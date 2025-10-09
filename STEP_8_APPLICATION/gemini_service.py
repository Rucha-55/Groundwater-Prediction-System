"""
Gemini AI Service for Intelligent Location Search
Provides dynamic, context-aware location suggestions for Nashik District
Enhanced with Google Maps integration for comprehensive place search
"""

import google.generativeai as genai
import json
import re

# Configure Gemini API (for AI-powered contextual search)
GEMINI_API_KEY = "AIzaSyBPRyNH10Jce_cvYyVDps2qI959COxBjl8"
genai.configure(api_key=GEMINI_API_KEY)

# Google Maps API Key (for real place data)
GOOGLE_MAPS_API_KEY = "AIzaSyBxsDSOmOE-ba4T7WdOW_k3P2TAbtiI-pg"

# Initialize Gemini model
model = genai.GenerativeModel('gemini-pro')

def get_location_suggestions(query, max_results=10):
    """
    Get intelligent location suggestions for Nashik District using Gemini AI
    Enhanced to detect place types: villages, cities, schools, banks, shops, temples, hospitals, etc.
    
    Args:
        query (str): User's search query
        max_results (int): Maximum number of suggestions to return
        
    Returns:
        list: List of location suggestions with details
    """
    
    if not query or len(query.strip()) < 2:
        # Return popular locations for empty query
        return get_popular_locations()
    
    try:
        prompt = f"""
You are a location search assistant for Nashik District, Maharashtra, India.
User is searching for: "{query}"

Provide {max_results} relevant location suggestions in Nashik District that match this query.

IMPORTANT: Understand the search intent and provide appropriate results:
- If searching for PLACES: cities, towns, talukas, villages, dams, industrial areas, tourist spots
- If searching for SCHOOLS: Schools, colleges, universities, education institutions
- If searching for BANKS: Banks, ATMs, financial institutions
- If searching for SHOPS: Malls, markets, stores, shopping centers
- If searching for HOSPITALS: Hospitals, clinics, health centers
- If searching for TEMPLES/RELIGIOUS: Temples, mosques, churches, religious places
- If searching for RESTAURANTS: Restaurants, cafes, food places
- If searching for HOTELS: Hotels, lodges, guest houses
- If searching for GOVERNMENT: Government offices, municipal corporations, post offices
- If searching for ANY ESTABLISHMENT: Match the query intent

For each suggestion, provide:
1. Name: Exact location name
2. Category: Type (City/Town/Village/Dam/Institute/Industrial Area/Tourist Spot/etc.)
3. Description: Brief description (1 line, include key features like population, importance, specialties)
4. Keywords: Related search terms
5. Popular: true/false (is it a well-known location?)
6. Coordinates: Approximate latitude and longitude

Format response EXACTLY as JSON array:
[
  {{
    "name": "Location Name",
    "category": "🏙️ City",
    "description": "Brief description with key features",
    "keywords": ["keyword1", "keyword2"],
    "popular": true,
    "lat": 20.0000,
    "lon": 73.7900
  }}
]

Rules:
- Only suggest locations within or very near Nashik District
- Prioritize exact matches first
- Include educational institutions if query mentions college/university/school
- Include dams if query mentions dam/water/reservoir
- Include industrial areas if query mentions MIDC/industrial
- Be accurate with coordinates (Nashik district: lat 19.5-21.0, lon 73.0-75.0)
- Keep descriptions concise and informative
- Return valid JSON only, no additional text

Search query: "{query}"
"""

        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to find JSON array in response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            suggestions = json.loads(json_str)
            
            # Validate and enhance suggestions
            validated_suggestions = []
            for idx, sug in enumerate(suggestions):
                if all(key in sug for key in ['name', 'category', 'description']):
                    # Add priority based on order
                    sug['priority'] = idx + 1
                    
                    # Ensure coordinates are present
                    if 'lat' not in sug or 'lon' not in sug:
                        sug['lat'] = 20.0  # Default Nashik center
                        sug['lon'] = 73.79
                    
                    # Ensure keywords exist
                    if 'keywords' not in sug:
                        sug['keywords'] = [sug['name'].lower()]
                    
                    # Ensure popular flag exists
                    if 'popular' not in sug:
                        sug['popular'] = False
                    
                    validated_suggestions.append(sug)
            
            return validated_suggestions[:max_results]
        else:
            print(f"Warning: Could not extract JSON from Gemini response: {response_text}")
            return get_fallback_suggestions(query)
            
    except Exception as e:
        print(f"Error getting Gemini suggestions: {str(e)}")
        return get_fallback_suggestions(query)


def get_popular_locations():
    """
    Return popular/trending locations when no query is provided
    """
    return [
        {
            "name": "Nashik",
            "category": "🏙️ City",
            "description": "Wine capital of India • Major pilgrimage center • Population 15 lakh+",
            "keywords": ["nashik", "nasik", "city", "wine", "godavari"],
            "popular": True,
            "trending": True,
            "priority": 1,
            "lat": 20.0,
            "lon": 73.79
        },
        {
            "name": "Trimbakeshwar",
            "category": "🕉️ Religious",
            "description": "Jyotirlinga temple • Origin of Godavari River • Popular pilgrimage",
            "keywords": ["trimbak", "temple", "jyotirlinga", "religious"],
            "popular": True,
            "trending": True,
            "priority": 2,
            "lat": 19.9333,
            "lon": 73.5333
        },
        {
            "name": "Malegaon",
            "category": "🏙️ City",
            "description": "2nd largest city • Textile industry hub • Population 5 lakh+",
            "keywords": ["malegaon", "textile", "city"],
            "popular": True,
            "priority": 3,
            "lat": 20.5500,
            "lon": 74.5333
        },
        {
            "name": "Sinnar",
            "category": "🏘️ Town",
            "description": "Industrial hub • MIDC area • Rapidly growing town",
            "keywords": ["sinnar", "industrial", "midc"],
            "popular": True,
            "priority": 4,
            "lat": 19.8472,
            "lon": 73.9975
        },
        {
            "name": "Igatpuri",
            "category": "⛰️ Hill Station",
            "description": "Western Ghats • High rainfall • Trekking destination",
            "keywords": ["igatpuri", "ghat", "hill station", "trekking"],
            "popular": True,
            "trending": True,
            "priority": 5,
            "lat": 19.6958,
            "lon": 73.5631
        },
        {
            "name": "Gangapur Dam",
            "category": "💧 Dam",
            "description": "Major water reservoir • Supplies water to Nashik city",
            "keywords": ["gangapur", "dam", "water", "reservoir"],
            "popular": True,
            "priority": 6,
            "lat": 20.0167,
            "lon": 74.0167
        },
        {
            "name": "Lasalgaon",
            "category": "🧅 Market",
            "description": "Asia's largest onion market • Major agricultural hub",
            "keywords": ["lasalgaon", "onion", "market", "agriculture"],
            "popular": True,
            "trending": True,
            "priority": 7,
            "lat": 20.1333,
            "lon": 74.2333
        },
        {
            "name": "Panchavati",
            "category": "🕉️ Religious",
            "description": "Godavari riverside • Ramayan connection • Sacred bathing ghats",
            "keywords": ["panchavati", "godavari", "religious", "ghat"],
            "popular": True,
            "priority": 8,
            "lat": 19.9975,
            "lon": 73.7898
        }
    ]


def get_fallback_suggestions(query):
    """
    Fallback suggestions when Gemini API fails
    Simple keyword matching from popular locations
    """
    popular = get_popular_locations()
    
    if not query:
        return popular
    
    query_lower = query.lower()
    
    # Filter based on name or keywords
    matches = [
        loc for loc in popular
        if query_lower in loc['name'].lower() or
        any(query_lower in kw for kw in loc['keywords'])
    ]
    
    return matches if matches else popular[:5]


def get_location_details(location_name):
    """
    Get detailed information about a specific location using Gemini AI
    """
    try:
        prompt = f"""
Provide detailed information about "{location_name}" in Nashik District, Maharashtra, India.

Include:
1. Full name and alternative names
2. Type of location (city/town/village/dam/etc.)
3. Brief description (2-3 sentences)
4. Key features or importance
5. Approximate population (if applicable)
6. Major industries or activities
7. Tourist attractions nearby
8. Approximate coordinates (latitude, longitude)

Format as JSON:
{{
  "name": "Full Location Name",
  "type": "Type",
  "description": "Detailed description",
  "features": ["feature1", "feature2"],
  "population": "approximate number or N/A",
  "coordinates": {{"lat": 00.0000, "lon": 00.0000}}
}}
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return None
        
    except Exception as e:
        print(f"Error getting location details: {str(e)}")
        return None


# Test function
if __name__ == "__main__":
    print("Testing Gemini Location Search Service...")
    print("\n1. Testing with query 'college':")
    results = get_location_suggestions("college", max_results=5)
    for r in results:
        print(f"  - {r['name']} ({r['category']}): {r['description']}")
    
    print("\n2. Testing with query 'dam':")
    results = get_location_suggestions("dam", max_results=5)
    for r in results:
        print(f"  - {r['name']} ({r['category']}): {r['description']}")
    
    print("\n3. Testing popular locations (empty query):")
    results = get_location_suggestions("", max_results=5)
    for r in results:
        print(f"  - {r['name']} ({r['category']}): {r['description']}")
