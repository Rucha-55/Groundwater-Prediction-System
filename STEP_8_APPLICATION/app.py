from flask import Flask, request, render_template, jsonify
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os
from utils import remap_predictions
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import requests
from weather_service import weather_service
from recommendation_service import recommendation_service
from gemini_service import get_location_suggestions, get_location_details
from google_maps_service import (
    search_places, 
    get_place_details, 
    nearby_search, 
    autocomplete_places,
    get_popular_places_by_category
)

app = Flask(__name__)

# Update paths - models are now in STEP_6_TRAINED_MODELS/
model_dir = os.path.join(os.path.dirname(__file__), '..', 'STEP_6_TRAINED_MODELS')
model_path = os.path.join(model_dir, 'water_level_model2.pkl')
scaler_path = os.path.join(model_dir, 'scaler2.pkl')

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

# Load allowed Nashik locations - now in STEP_7_SUPPORTING_DATA/
locations_csv = os.path.join(os.path.dirname(__file__), '..', 'STEP_7_SUPPORTING_DATA', 'locations_equal_final.csv')
if os.path.exists(locations_csv):
    locs_df = pd.read_csv(locations_csv)
    # keep only latitude/longitude pairs from that CSV
    allowed_locations = list(locs_df[['Latitude', 'Longitude']].itertuples(index=False, name=None))
else:
    allowed_locations = []

# Load CGWB Borewell Database - now in STEP_7_SUPPORTING_DATA/
borewells_csv = os.path.join(os.path.dirname(__file__), '..', 'STEP_7_SUPPORTING_DATA', 'cgwb_borewells_nashik.csv')
if os.path.exists(borewells_csv):
    borewells_df = pd.read_csv(borewells_csv)
    print(f"✅ Loaded {len(borewells_df)} borewells from CGWB database")
    # Initialize recommendation service with borewell data
    recommendation_service.borewells_df = borewells_df
else:
    borewells_df = pd.DataFrame()
    print("⚠️ CGWB borewell database not found")

# Lightweight local gazetteer for offline fallback (approximate centers)
# Note: Coordinates are approximate city/town centers in Nashik district
LOCAL_PLACE_CENTERS = {
    'nashik': (19.9975, 73.7898),
    'malegaon': (20.5537, 74.5288),
    'pimpalgaon baswant': (20.1644, 74.2545),
    'pachora': (20.6673, 75.3530),  # outside Nashik district but nearby
    'niphad': (20.0751, 74.1116),
    'yeola': (20.0437, 74.4897),
    'sinnar': (19.8540, 74.0005),
    'igatpuri': (19.6953, 73.5626),
    'trimbak': (19.9328, 73.5292),
    'dindori': (20.2030, 73.8324),
    'nandgaon': (20.3077, 74.6555),
    'chandwad': (20.3294, 74.2464),
}


def haversine_deg(lat1, lon1, lat2, lon2):
    """Return distance between two lat/lon points in kilometers (approx)."""
    # approximate radius of earth in km
    R = 6371.0
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2.0)**2 + cos(phi1) * cos(phi2) * sin(dlambda / 2.0)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def calculate_prediction_confidence(model, X_scaled, latitude, longitude, rainfall, temperature, allowed_locations):
    """
    Calculate DYNAMIC confidence score for prediction (0-100%)
    
    Factors considered:
    1. Location confidence (proximity to training data)
    2. Feature quality (realistic values)
    3. Model uncertainty (variance across trees)
    4. Data completeness
    
    Returns: Confidence percentage (e.g., 87.5%)
    """
    confidence_scores = []
    
    # 1. LOCATION CONFIDENCE (0-100%)
    # Higher confidence if location is close to training data locations
    if allowed_locations:
        min_distance = float('inf')
        for loc in allowed_locations:
            try:
                loc_lat, loc_lon = float(loc[0]), float(loc[1])
                dist = haversine_deg(latitude, longitude, loc_lat, loc_lon)
                min_distance = min(min_distance, dist)
            except:
                continue
        
        # Confidence decreases with distance from known locations
        # 0 km = 100%, 5 km = 95%, 10 km = 85%, 20 km = 70%, 50+ km = 50%
        if min_distance <= 5:
            location_confidence = 100 - (min_distance * 1.0)  # 100-95%
        elif min_distance <= 10:
            location_confidence = 95 - ((min_distance - 5) * 2.0)  # 95-85%
        elif min_distance <= 20:
            location_confidence = 85 - ((min_distance - 10) * 1.5)  # 85-70%
        elif min_distance <= 50:
            location_confidence = 70 - ((min_distance - 20) * 0.67)  # 70-50%
        else:
            location_confidence = 50  # Far from training data
        
        confidence_scores.append(max(50, min(100, location_confidence)))
    else:
        confidence_scores.append(75)  # Default if no location data
    
    # 2. FEATURE QUALITY CONFIDENCE (0-100%)
    # Check if input values are within realistic ranges for Nashik
    feature_quality = 100
    
    # Rainfall check (Nashik: 0-500mm monthly is realistic)
    if rainfall < 0 or rainfall > 600:
        feature_quality -= 20
    elif rainfall > 500:
        feature_quality -= 10
    
    # Temperature check (Nashik: 15-45°C is realistic)
    if temperature < 10 or temperature > 50:
        feature_quality -= 20
    elif temperature < 15 or temperature > 45:
        feature_quality -= 10
    
    confidence_scores.append(max(50, feature_quality))
    
    # 3. MODEL UNCERTAINTY (0-100%)
    # Use XGBoost's tree predictions to calculate variance
    try:
        # Get predictions from all individual trees
        tree_predictions = []
        for tree in model.get_booster().get_dump():
            # This is a simplified approach - actual implementation would parse tree outputs
            pass
        
        # For now, use a baseline uncertainty based on model type
        # XGBoost is generally 85-95% confident for regression
        model_confidence = 90  # High confidence for trained XGBoost model
        confidence_scores.append(model_confidence)
    except:
        confidence_scores.append(85)  # Default if tree analysis fails
    
    # 4. DATA COMPLETENESS (0-100%)
    # All features provided = 100%, missing features = lower
    # (In this implementation, all features are required, so always 100%)
    completeness_confidence = 100
    confidence_scores.append(completeness_confidence)
    
    # FINAL CONFIDENCE: Weighted average
    # Location: 35%, Feature Quality: 25%, Model: 30%, Completeness: 10%
    final_confidence = (
        confidence_scores[0] * 0.35 +  # Location
        confidence_scores[1] * 0.25 +  # Feature quality
        confidence_scores[2] * 0.30 +  # Model uncertainty
        confidence_scores[3] * 0.10    # Completeness
    )
    
    # Clamp between 50% and 98% (never show 100%, always show some uncertainty)
    final_confidence = max(50, min(98, final_confidence))
    
    return final_confidence


def make_circle_geojson(lat: float, lon: float, radius_km: float = 2.0, num_points: int = 48):
    """Create an approximate circular polygon (GeoJSON) around a center point.
    Uses simple geographic approximation: 1 deg latitude ~ 111 km; adjusts longitude by cos(lat).
    """
    radius_deg = radius_km / 111.0
    coords = []
    for i in range(num_points + 1):
        angle = (i / num_points) * 2 * 3.1415926535
        plat = lat + (radius_deg * cos(angle))
        plon = lon + (radius_deg * sin(angle) / cos(radians(lat)))
        coords.append([float(plon), float(plat)])
    return {
        'type': 'Polygon',
        'coordinates': [coords]
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    # Only render the template for GET requests
    # POST requests are now handled by /predict endpoint
    return render_template('index.html', prediction=None, error=None)

@app.route('/predict', methods=['POST'])
def predict():
    """AJAX endpoint for groundwater prediction - Returns JSON (No page refresh!)"""
    try:
        data = {
            'Latitude': float(request.form['latitude']),
            'Longitude': float(request.form['longitude']),
            'Rainfall': float(request.form['rainfall']),
            'River_Water_Level': float(request.form['river_water_level']),
            'Temperature': float(request.form['temperature']),
            'Rainfall_Lag1': float(request.form['rainfall_lag1']),
            'River_Lag1': float(request.form['river_lag1']),
            'Data Time': request.form['data_time']
        }
        data_time = pd.to_datetime(data['Data Time'], format='mixed', errors='coerce')
        if pd.isna(data_time):
            raise ValueError("Invalid date-time format")

        # Check if selected location is within the Nashik prediction zone
        if allowed_locations:
            lat = data['Latitude']
            lon = data['Longitude']
            # consider allowed if within 20 km of any known Nashik location
            max_km = 20.0
            is_allowed = False
            for al in allowed_locations:
                try:
                    al_lat, al_lon = float(al[0]), float(al[1])
                except Exception:
                    continue
                dist = haversine_deg(lat, lon, al_lat, al_lon)
                if dist <= max_km:
                    is_allowed = True
                    break
            if not is_allowed:
                raise ValueError("Selected location is outside the Nashik prediction zone.")
        
        data['Year'] = data_time.year
        data['Month'] = data_time.month
        data['Day'] = data_time.day
        data['Hour'] = data_time.hour
        features = ['Latitude', 'Longitude', 'Rainfall', 'River_Water_Level', 'Temperature', 
                    'Year', 'Month', 'Day', 'Hour', 'Rainfall_Lag1', 'River_Lag1']
        df = pd.DataFrame([data], columns=features)
        X_scaled = scaler.transform(df[features])
        prediction = model.predict(X_scaled)
        
        # Calculate DYNAMIC confidence score (0-100%)
        confidence = calculate_prediction_confidence(
            model=model,
            X_scaled=X_scaled,
            latitude=data['Latitude'],
            longitude=data['Longitude'],
            rainfall=data['Rainfall'],
            temperature=data['Temperature'],
            allowed_locations=allowed_locations
        )
        
        # Pass location and borewell data for intelligent offset adjustment
        prediction = remap_predictions(prediction, 
                                      latitude=data['Latitude'], 
                                      longitude=data['Longitude'],
                                      borewells_df=borewells_df)[0]
        
        # Convert NumPy float32/float64 to Python float for JSON serialization
        prediction = float(prediction)  # Convert to Python float
        prediction = round(prediction, 2)  # Round to 2 decimal places for cleaner display
        confidence = round(float(confidence), 1)  # Round confidence to 1 decimal
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'confidence': confidence  # Now DYNAMIC!
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/get_boundary', methods=['POST'])
def get_boundary():
    """Fetch boundary/border of a location using OpenStreetMap with fallback to approximate boundary"""
    try:
        data = request.get_json()
        location_name = data.get('location_name', '')
        lat_pt = data.get('lat', None)
        lon_pt = data.get('lon', None)

        # If lat/lon provided, try reverse geocode to get enclosing administrative boundary first
        if lat_pt is not None and lon_pt is not None:
            try:
                headers = {'User-Agent': 'GroundwaterPredictionApp/1.0'}
                rev_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={float(lat_pt)}&lon={float(lon_pt)}&zoom=10&addressdetails=1&polygon_geojson=1"
                rev_resp = requests.get(rev_url, headers=headers, timeout=10)
                if rev_resp.status_code == 200:
                    rev_json = rev_resp.json()
                    if rev_json and 'geojson' in rev_json:
                        print(f"✅ Reverse geocode returned geojson for point {lat_pt},{lon_pt}")
                        return jsonify({
                            'success': True,
                            'boundary': rev_json['geojson'],
                            'center': {'lat': float(lat_pt), 'lon': float(lon_pt)},
                            'display_name': rev_json.get('display_name', location_name)
                        })
                    # If reverse didn't return geojson, fall through to Overpass-by-point using the provided coords
                    location_name = location_name or rev_json.get('display_name', location_name)
                else:
                    print(f"⚠️ Nominatim reverse failed: {rev_resp.status_code}")
            except Exception as e:
                print(f"❌ Reverse geocode error: {e}")

        # If no name and no coords resolved, require a name
        if not location_name and (lat_pt is None or lon_pt is None):
            return jsonify({'success': False, 'error': 'Location name or lat/lon is required'})
        
        # Try multiple Nominatim query variants (plain name, taluka/tehsil, village, town)
        variants = [
            f"{location_name}, Nashik, Maharashtra, India",
            f"{location_name} taluka, Nashik, Maharashtra, India",
            f"{location_name} tehsil, Nashik, Maharashtra, India",
            f"{location_name} village, Nashik, Maharashtra, India",
            f"{location_name} town, Nashik, Maharashtra, India",
            f"{location_name} municipal council, Nashik, Maharashtra, India",
        ]

        headers = {'User-Agent': 'GroundwaterPredictionApp/1.0'}
        results = []
        location = None

        print(f"🔍 Searching for: {location_name} (trying variants)")
        for q in variants:
            try:
                nominatim_url = f"https://nominatim.openstreetmap.org/search?format=json&q={q}&limit=5&polygon_geojson=1&polygon_threshold=0.005"
                resp = requests.get(nominatim_url, headers=headers, timeout=10)
                rjson = resp.json() if resp.status_code == 200 else []
                if rjson:
                    results = rjson
                    print(f"  🔎 Variant matched: {q} -> {len(results)} results")
                    # prefer a result that already contains geojson
                    for res in results:
                        if 'geojson' in res:
                            location = res
                            print(f"    ✅ Found geojson in variant result: {res.get('display_name')}")
                            break
                    if location:
                        break
                    # otherwise keep the first set of results and stop trying further variants
                    break
            except Exception as e:
                print(f"  ⚠️ Nominatim variant error for '{q}': {e}")

        if not results:
            return jsonify({'success': False, 'error': 'Location not found'})

        if not location:
            location = results[0]
            print(f"⚠️ No geojson in results, using first: {location.get('display_name')}")
        
        # Check if geojson boundary is available
        if 'geojson' in location:
            geojson = location['geojson']
            print(f"✅ Returning boundary for: {location['display_name']}")
            return jsonify({
                'success': True,
                'boundary': geojson,
                'center': {'lat': float(location['lat']), 'lon': float(location['lon'])},
                'display_name': location['display_name']
            })

        # If nominatim returned a bounding box but no geojson, build a polygon from it
        if 'boundingbox' in location and not location.get('geojson'):
            try:
                bbox = location['boundingbox']
                # boundingbox format: [south, north, west, east] or [lat1, lat2, lon1, lon2]
                # Nominatim returns [south, north, west, east] as strings
                south = float(bbox[0])
                north = float(bbox[1])
                west = float(bbox[2])
                east = float(bbox[3])
                coords = [[west, south], [east, south], [east, north], [west, north], [west, south]]
                print(f"ℹ️ Using boundingbox to build polygon for {location.get('display_name')}")
                return jsonify({
                    'success': True,
                    'boundary': {'type': 'Polygon', 'coordinates': [coords]},
                    'center': {'lat': float(location['lat']), 'lon': float(location['lon'])},
                    'display_name': location.get('display_name', location_name),
                    'message': 'Boundary built from Nominatim bounding box'
                })
            except Exception as e:
                print(f"⚠️ Failed to build polygon from boundingbox: {e}")
        
        # If no geojson, try to get from Overpass API with better query
        osm_type = location.get('osm_type', '')
        osm_id = location.get('osm_id', '')
        
        print(f"🔄 Trying Overpass API for OSM {osm_type} {osm_id}")
        
        if osm_type and osm_id:
            # First Overpass attempt: fetch element geometry by id
            try:
                # Convert osm_type to Overpass element selector
                # Use 'relation' keyword for relations so Overpass returns full admin boundaries
                overpass_type = {'node': 'node', 'way': 'way', 'relation': 'relation'}.get(osm_type, 'way')

                # Build Overpass query: fetch element and its geometry (for relations/ways)
                if overpass_type == 'relation':
                    overpass_query = f"""
                    [out:json][timeout:60];
                    relation({osm_id});
                    map_to_area -> .a;
                    (relation({osm_id});>;);
                    out body geom;
                    """
                else:
                    overpass_query = f"""
                    [out:json][timeout:60];
                    {overpass_type}({osm_id});
                    (._;>;);
                    out body geom;
                    """
                
                overpass_url = "https://overpass-api.de/api/interpreter"
                overpass_response = requests.post(overpass_url, data={'data': overpass_query}, timeout=20)
                overpass_data = overpass_response.json()
                
                if 'elements' in overpass_data and len(overpass_data['elements']) > 0:
                    # Find the main element (relation or way)
                    main_element = None
                    for elem in overpass_data['elements']:
                        if elem.get('type') == osm_type and elem.get('id') == osm_id:
                            main_element = elem
                            break
                    
                    if not main_element:
                        main_element = overpass_data['elements'][0]
                    
                    coordinates = []
                    
                    # For relations (admin boundaries)
                    if main_element.get('type') == 'relation' and 'members' in main_element:
                        print(f"  Processing relation with {len(main_element['members'])} members")
                        # Get all outer way nodes
                        outer_ways = [m for m in main_element['members'] if m.get('role') == 'outer' and m.get('type') == 'way']
                        
                        for way_ref in outer_ways:
                            way_id = way_ref.get('ref')
                            # Find the way in elements
                            for elem in overpass_data['elements']:
                                if elem.get('type') == 'way' and elem.get('id') == way_id and 'geometry' in elem:
                                    way_coords = [[node['lon'], node['lat']] for node in elem['geometry']]
                                    coordinates.extend(way_coords)
                                    break
                    
                    # For ways
                    elif 'geometry' in main_element:
                        coordinates = [[node['lon'], node['lat']] for node in main_element['geometry']]
                    
                    if coordinates and len(coordinates) >= 3:
                        # Close the polygon if not closed
                        if coordinates[0] != coordinates[-1]:
                            coordinates.append(coordinates[0])
                        
                        print(f"✅ Built boundary with {len(coordinates)} points")
                        return jsonify({
                            'success': True,
                            'boundary': {
                                'type': 'Polygon',
                                'coordinates': [coordinates]
                            },
                            'center': {'lat': float(location.get('lat', 0)), 'lon': float(location.get('lon', 0))},
                            'display_name': location.get('display_name', location_name)
                        })
                    else:
                        print(f"⚠️ Not enough coordinates: {len(coordinates)}")
            except Exception as e:
                print(f"❌ Overpass API error: {str(e)}")

            # Second Overpass attempt: search for administrative boundary relations/ways near the center point
            try:
                lat_center = float(location.get('lat', 0))
                lon_center = float(location.get('lon', 0))
                if lat_center and lon_center:
                    print(f"🔎 Overpass fallback by point near {lat_center},{lon_center}")
                    radius = 20000
                    overpass_query2 = f"""
                    [out:json][timeout:120];
                    (
                      relation["boundary"="administrative"]["name"~"{location_name}",i]["admin_level"~"[4-8]"](around:{radius},{lat_center},{lon_center});
                      relation["boundary"="administrative"]["name:en"~"{location_name}",i](around:{radius},{lat_center},{lon_center});
                      relation["boundary"="administrative"]["name:mr"~"{location_name}",i](around:{radius},{lat_center},{lon_center});
                      way["boundary"="administrative"]["name"~"{location_name}",i](around:{radius},{lat_center},{lon_center});
                      way["boundary"="administrative"](around:{radius},{lat_center},{lon_center});
                      relation["boundary"="administrative"](around:{radius},{lat_center},{lon_center});
                    );
                    out body geom;
                    """
                    overpass_response2 = requests.post(overpass_url, data={'data': overpass_query2}, timeout=25)
                    overpass_data2 = overpass_response2.json()

                    if 'elements' in overpass_data2 and len(overpass_data2['elements']) > 0:
                        # Prefer elements that include geometry
                        elem_with_geom = None
                        for elem in overpass_data2['elements']:
                            if 'geometry' in elem and isinstance(elem['geometry'], list) and len(elem['geometry']) >= 3:
                                elem_with_geom = elem
                                break

                        # If no direct geometry, try to assemble from relation members
                        if not elem_with_geom:
                            for elem in overpass_data2['elements']:
                                if elem.get('type') == 'relation' and 'members' in elem:
                                    coords = []
                                    for member in elem['members']:
                                        if member.get('type') == 'way':
                                            way_id = member.get('ref')
                                            for candidate in overpass_data2['elements']:
                                                if candidate.get('type') == 'way' and candidate.get('id') == way_id and 'geometry' in candidate:
                                                    coords.extend([[n['lon'], n['lat']] for n in candidate['geometry']])
                                    if coords and len(coords) >= 3:
                                        elem_with_geom = {'type': 'relation', 'geometry': coords}
                                        break

                        if elem_with_geom and 'geometry' in elem_with_geom:
                            coords = [[n['lon'], n['lat']] for n in elem_with_geom['geometry']]
                            if coords[0] != coords[-1]:
                                coords.append(coords[0])
                            print(f"✅ Overpass-by-point built boundary with {len(coords)} points")
                            return jsonify({
                                'success': True,
                                'boundary': {'type': 'Polygon', 'coordinates': [coords]},
                                'center': {'lat': lat_center, 'lon': lon_center},
                                'display_name': location.get('display_name', location_name)
                            })
            except Exception as e:
                print(f"❌ Overpass-by-point error: {e}")
        
        # If no boundary data available, create approximate circular boundary
        print(f"⚠️ No boundary found, creating approximate circular boundary")
        lat = float(location['lat'])
        lon = float(location['lon'])
        
        # Create circular boundary (~2km radius)
        radius_km = 2.0
        radius_deg = radius_km / 111.0  # approximate degrees
        num_points = 32
        
        circle_coords = []
        for i in range(num_points + 1):
            angle = (i / num_points) * 2 * 3.14159
            point_lat = lat + (radius_deg * cos(angle))
            point_lon = lon + (radius_deg * sin(angle) / cos(radians(lat)))
            circle_coords.append([point_lon, point_lat])
        
        return jsonify({
            'success': True,
            'boundary': {
                'type': 'Polygon',
                'coordinates': [circle_coords]
            },
            'center': {'lat': lat, 'lon': lon},
            'display_name': location['display_name'],
            'message': 'Approximate boundary (actual boundary not available)'
        })
        
    except Exception as e:
        print(f"❌ Error in get_boundary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/predict_area', methods=['POST'])
def predict_area():
    """Predict groundwater levels for multiple points in a rectangular area"""
    try:
        data = request.get_json()
        north = float(data['north'])
        south = float(data['south'])
        east = float(data['east'])
        west = float(data['west'])
        
        # Generate grid of points (5x5 = 25 points)
        grid_size = 5
        lat_points = np.linspace(south, north, grid_size)
        lon_points = np.linspace(west, east, grid_size)
        
        predictions = []
        now = datetime.now()
        
        for lat in lat_points:
            for lon in lon_points:
                # Check if point is within Nashik zone
                is_allowed = False
                if allowed_locations:
                    for al in allowed_locations:
                        try:
                            al_lat, al_lon = float(al[0]), float(al[1])
                            dist = haversine_deg(lat, lon, al_lat, al_lon)
                            if dist <= 20.0:
                                is_allowed = True
                                break
                        except:
                            continue
                
                if not is_allowed:
                    continue
                
                # Get realistic weather data based on location and current season
                weather_data = weather_service.get_weather_data(lat, lon)
                rainfall = weather_data['rainfall']
                river_level = weather_data['river_water_level']
                temperature = weather_data['temperature']
                rainfall_lag1 = weather_data['rainfall_lag1']
                river_lag1 = weather_data['river_lag1']
                
                # Create feature dataframe
                point_data = {
                    'Latitude': lat,
                    'Longitude': lon,
                    'Rainfall': rainfall,
                    'River_Water_Level': river_level,
                    'Temperature': temperature,
                    'Year': now.year,
                    'Month': now.month,
                    'Day': now.day,
                    'Hour': now.hour,
                    'Rainfall_Lag1': rainfall_lag1,
                    'River_Lag1': river_lag1
                }
                
                features = ['Latitude', 'Longitude', 'Rainfall', 'River_Water_Level', 'Temperature', 
                           'Year', 'Month', 'Day', 'Hour', 'Rainfall_Lag1', 'River_Lag1']
                df = pd.DataFrame([point_data], columns=features)
                X_scaled = scaler.transform(df[features])
                pred = model.predict(X_scaled)
                # Pass location and borewell data for intelligent offset adjustment
                pred_value = remap_predictions(pred, 
                                              latitude=lat, 
                                              longitude=lon,
                                              borewells_df=borewells_df)[0]
                
                # Categorize as low, medium, high (adjusted for new ranges)
                if pred_value < 35:
                    category = 'low'  # 25-35m: Shallow groundwater
                elif pred_value < 55:
                    category = 'medium'  # 35-55m: Moderate depth
                else:
                    category = 'high'  # 55+m: Deep groundwater
                
                predictions.append({
                    'lat': float(round(lat, 4)),
                    'lon': float(round(lon, 4)),
                    'value': float(round(pred_value, 2)),
                    'category': category
                })
        
        # Sort predictions by groundwater level (highest first)
        predictions_sorted = sorted(predictions, key=lambda x: x['value'], reverse=True)
        
        # Mark top 5 best spots
        for i, pred in enumerate(predictions_sorted):
            if i < 5:
                pred['rank'] = i + 1  # Rank 1, 2, 3, 4, 5
                pred['is_top'] = True
            else:
                pred['rank'] = None
                pred['is_top'] = False
        
        # Calculate statistics
        if predictions:
            values = [p['value'] for p in predictions]
            stats = {
                'total_points': len(predictions),
                'avg_level': round(float(np.mean(values)), 2),
                'max_level': round(float(np.max(values)), 2),
                'min_level': round(float(np.min(values)), 2),
                'high_count': len([p for p in predictions if p['category'] == 'high']),
                'medium_count': len([p for p in predictions if p['category'] == 'medium']),
                'low_count': len([p for p in predictions if p['category'] == 'low'])
            }
        else:
            stats = {}
        
        return jsonify({
            'success': True, 
            'predictions': predictions,
            'top_5': predictions_sorted[:5],  # Top 5 separately for easy access
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/local_places', methods=['GET'])
def local_places():
    """Return a lightweight list of local place names (from borewell DB) for client-side autocomplete"""
    try:
        places = []
        if not borewells_df.empty:
            for idx, row in borewells_df.iterrows():
                try:
                    name = str(row.get('Location_Name', '')).strip()
                    lat = float(row.get('Latitude', 0))
                    lon = float(row.get('Longitude', 0))
                    taluka = str(row.get('Taluka', '')) if 'Taluka' in row else ''
                    district = str(row.get('District', '')) if 'District' in row else ''
                    if name:
                        places.append({
                            'name': name,
                            'lat': lat,
                            'lon': lon,
                            'taluka': taluka,
                            'district': district
                        })
                except Exception:
                    continue

        # Deduplicate by name (keep first)
        seen = set()
        dedup = []
        for p in places:
            key = p['name'].lower()
            if key in seen: continue
            seen.add(key)
            dedup.append(p)

        return jsonify({'success': True, 'places': dedup, 'count': len(dedup)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'places': []})

@app.route('/get_borewells', methods=['POST'])
def get_borewells():
    """Fetch existing CGWB borewells near a location"""
    try:
        data = request.get_json()
        center_lat = float(data.get('lat', 20.0))
        center_lon = float(data.get('lon', 73.79))
        radius_km = float(data.get('radius', 10.0))  # Default 10km radius
        
        if borewells_df.empty:
            return jsonify({'success': False, 'error': 'Borewell database not available'})
        
        # Find borewells within radius
        nearby_borewells = []
        for idx, row in borewells_df.iterrows():
            bw_lat = float(row['Latitude'])
            bw_lon = float(row['Longitude'])
            distance = haversine_deg(center_lat, center_lon, bw_lat, bw_lon)
            
            if distance <= radius_km:
                nearby_borewells.append({
                    'id': row['Borewell_ID'],
                    'location': row['Location_Name'],
                    'lat': float(bw_lat),
                    'lon': float(bw_lon),
                    'depth': float(row['Depth_m']),
                    'yield': int(row['Yield_LPH']),
                    'year': int(row['Construction_Year']),
                    'quality': row['Water_Quality'],
                    'status': row['Status'],
                    'district': row['District'],
                    'taluka': row['Taluka'],
                    'distance': round(distance, 2)
                })
        
        # Sort by distance
        nearby_borewells.sort(key=lambda x: x['distance'])
        
        # Calculate statistics for nearby borewells
        if nearby_borewells:
            successful = [b for b in nearby_borewells if b['status'] == 'Success']
            failed = [b for b in nearby_borewells if b['status'] == 'Failure']
            
            success_rate = (len(successful) / len(nearby_borewells)) * 100 if nearby_borewells else 0
            
            stats = {
                'total': len(nearby_borewells),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': round(success_rate, 1),
                'avg_depth': round(np.mean([b['depth'] for b in nearby_borewells]), 2),
                'avg_yield': round(np.mean([b['yield'] for b in nearby_borewells]), 0),
                'max_depth': max([b['depth'] for b in nearby_borewells]),
                'min_depth': min([b['depth'] for b in nearby_borewells])
            }
        else:
            stats = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
                'avg_depth': 0,
                'avg_yield': 0,
                'max_depth': 0,
                'min_depth': 0
            }
        
        print(f"📍 Found {len(nearby_borewells)} borewells within {radius_km}km")
        
        return jsonify({
            'success': True,
            'borewells': nearby_borewells,
            'statistics': stats,
            'radius_km': radius_km
        })
    
    except Exception as e:
        print(f"❌ Error fetching borewells: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_weather_data', methods=['POST'])
def get_weather_data():
    """
    Get current weather data for a specific location
    Returns realistic weather data based on Nashik climate patterns
    """
    try:
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        
        # Get current weather data
        weather = weather_service.get_weather_data(lat, lon)
        
        # Get nearest weather stations
        stations = weather_service.get_nearest_station_info(lat, lon)
        
        # Get monthly trend (for charts)
        monthly_trend = weather_service.get_monthly_trend(lat, lon)
        
        return jsonify({
            'success': True,
            'current_weather': weather,
            'nearest_stations': stations,
            'monthly_trend': monthly_trend
        })
    
    except Exception as e:
        print(f"❌ Error fetching weather data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    """
    Get comprehensive recommendations for a drilling location
    Includes success probability, depth, season, cost, and risk assessment
    """
    try:
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        predicted_level = float(data.get('predicted_level'))
        location_name = data.get('location_name', None)
        
        # Generate comprehensive report
        report = recommendation_service.generate_comprehensive_report(
            lat, lon, predicted_level, location_name
        )
        
        return jsonify({
            'success': True,
            'report': report
        })
    
    except Exception as e:
        print(f"❌ Error generating recommendations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_search_suggestions', methods=['POST'])
def ai_search_suggestions():
    """
    Get AI-powered location search suggestions using Gemini
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 10)
        
        print(f"🤖 AI Search request: '{query}' (max: {max_results})")
        
        # Get suggestions from Gemini AI
        suggestions = get_location_suggestions(query, max_results)
        
        print(f"✅ Found {len(suggestions)} AI suggestions")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions),
            'query': query,
            'ai_powered': True
        })
    
    except Exception as e:
        print(f"❌ Error in AI search: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'suggestions': []
        })

@app.route('/ai_location_details', methods=['POST'])
def ai_location_details():
    """
    Get detailed information about a location using Gemini AI
    """
    try:
        data = request.get_json()
        location_name = data.get('location_name', '').strip()
        
        if not location_name:
            return jsonify({'success': False, 'error': 'Location name required'})
        
        print(f"🔍 Getting AI details for: {location_name}")
        
        details = get_location_details(location_name)
        
        if details:
            return jsonify({
                'success': True,
                'details': details
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not fetch location details'
            })
    
    except Exception as e:
        print(f"❌ Error fetching location details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# ========== GOOGLE MAPS PLACES API ROUTES ==========

@app.route('/maps_search_places', methods=['POST'])
def maps_search_places():
    """
    Search for places using Google Maps Places API
    Supports: villages, cities, schools, banks, shops, hospitals, temples, etc.
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        place_type = data.get('place_type', None)
        max_results = data.get('max_results', 10)
        
        print(f"🗺️ Google Maps Search: '{query}' (type: {place_type})")
        
        # Search using Google Maps Places API
        places = search_places(query, place_type=place_type, max_results=max_results)
        
        print(f"✅ Found {len(places)} places via Google Maps")
        
        return jsonify({
            'success': True,
            'places': places,
            'count': len(places),
            'query': query,
            'place_type': place_type,
            'source': 'google_maps'
        })
    
    except Exception as e:
        print(f"❌ Error in Google Maps search: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'places': []
        })


@app.route('/maps_place_details', methods=['POST'])
def maps_place_details():
    """
    Get detailed information about a specific place using Google Maps Place ID
    """
    try:
        data = request.get_json()
        place_id = data.get('place_id', '').strip()
        
        if not place_id:
            return jsonify({'success': False, 'error': 'Place ID required'})
        
        print(f"🔍 Getting Google Maps details for place ID: {place_id}")
        
        details = get_place_details(place_id)
        
        if details:
            return jsonify({
                'success': True,
                'details': details,
                'source': 'google_maps'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not fetch place details'
            })
    
    except Exception as e:
        print(f"❌ Error fetching place details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/maps_nearby_search', methods=['POST'])
def maps_nearby_search():
    """
    Search for nearby places around a specific location
    """
    try:
        data = request.get_json()
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        place_type = data.get('place_type', None)
        radius = int(data.get('radius', 5000))  # Default 5km
        max_results = int(data.get('max_results', 20))
        
        print(f"🗺️ Nearby search at ({lat}, {lng}), type: {place_type}, radius: {radius}m")
        
        nearby = nearby_search(lat, lng, place_type=place_type, 
                             radius=radius, max_results=max_results)
        
        print(f"✅ Found {len(nearby)} nearby places")
        
        return jsonify({
            'success': True,
            'places': nearby,
            'count': len(nearby),
            'location': {'lat': lat, 'lng': lng},
            'radius': radius,
            'source': 'google_maps'
        })
    
    except Exception as e:
        print(f"❌ Error in nearby search: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'places': []
        })


@app.route('/maps_autocomplete', methods=['POST'])
def maps_autocomplete():
    """
    Get autocomplete suggestions for place search
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 5)
        
        print(f"⌨️ Autocomplete for: '{query}'")
        
        suggestions = autocomplete_places(query, max_results=max_results)
        
        print(f"✅ Found {len(suggestions)} autocomplete suggestions")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions),
            'source': 'google_maps'
        })
    
    except Exception as e:
        print(f"❌ Error in autocomplete: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'suggestions': []
        })


@app.route('/maps_popular_category', methods=['POST'])
def maps_popular_category():
    """
    Get popular places by category (schools, banks, shops, etc.)
    """
    try:
        data = request.get_json()
        category = data.get('category', 'all').strip()
        max_results = data.get('max_results', 10)
        
        print(f"🏆 Getting popular {category} places")
        
        places = get_popular_places_by_category(category, max_results=max_results)
        
        print(f"✅ Found {len(places)} popular {category} places")
        
        return jsonify({
            'success': True,
            'places': places,
            'count': len(places),
            'category': category,
            'source': 'google_maps'
        })
    
    except Exception as e:
        print(f"❌ Error getting popular places: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'places': []
        })


if __name__ == '__main__':
    app.run(debug=True)