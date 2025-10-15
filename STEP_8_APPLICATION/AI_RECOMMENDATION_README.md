# AI Recommendation System - Borewell Site Selection

## Overview
The AI recommendation system helps identify the best candidate locations for new borewell drilling within a user-selected map region. It uses a trained logistic regression model built on existing CGWB borewell data from Nashik district.

## Key Features
- **AI-Powered Site Scoring**: Each candidate point receives a probability score (0-100%) indicating likelihood of drilling success
- **Explainable AI**: Per-feature contributions show which factors (depth, yield, quality, age) influence the recommendation
- **Historical Data Integration**: Uses actual borewell performance data (Success/Failure, Depth, Yield, Water Quality)
- **Smart Placement**: Avoids overcrowding by considering proximity to existing borewells

## How It Works

### 1. Model Training
- The system trains a lightweight logistic regression on `cgwb_borewells_nashik.csv` (30 borewells)
- Features used:
  - **Depth (m)**: Average depth of nearby successful borewells
  - **Yield (LPH)**: Average yield (liters per hour) in the area
  - **Water Quality**: Encoded quality score (Excellent=3, Good=2, Moderate=1, Poor=0)
  - **Age (years)**: Average age of nearby borewells
- Target: Success (1) or Failure (0)

### 2. Scoring Candidates
For each grid point in the selected region:
1. Find nearby borewells within 5 km radius
2. Compute aggregated features (avg depth, yield, success rate, count)
3. Pass features through trained model → get probability
4. Return per-feature contributions (coefficient × scaled feature value)

### 3. Results Display
- Top 5 candidates shown as purple markers on map
- Popup includes:
  - Success probability (%)
  - Nearby data summary (depth, yield, success rate, count)
  - AI feature contributions with +/- values

## Usage

### Web Interface
1. **Draw a rectangle** on the map to select your region of interest
2. Click **"🤖 AI Recommend Best Sites"** button
3. View AI-scored candidate locations (purple markers)
4. Click markers to see detailed explanations

### API Endpoint
```http
POST /ai_recommend
Content-Type: application/json

{
  "bbox": [min_lat, min_lon, max_lat, max_lon],
  "n": 5,
  "spacing_km": 0.8
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "lat": 19.9680,
      "lon": 73.8169,
      "prob_success": 0.9842,
      "meta": {
        "avg_depth": 42.1,
        "avg_yield": 2400.0,
        "success_rate": 1.0,
        "count": 3
      },
      "contributions": {
        "depth_m": 0.523,
        "yield_lph": 0.412,
        "quality": 0.231,
        "age_years": -0.045
      }
    },
    ...
  ]
}
```

### Python Test Script
```powershell
# Run from project root
C:/Users/rucha/Downloads/Project/.venv/Scripts/python.exe STEP_9_TESTING\test_select_borewell_sites.py
```

## Files Added/Modified

### New Modules
- `STEP_8_APPLICATION/ai_recommender.py` - Core AI logic (train, load, score)
- `STEP_8_APPLICATION/select_borewell_sites.py` - Grid generation and distance utilities
- `STEP_9_TESTING/test_select_borewell_sites.py` - Demo/test script

### Modified Files
- `STEP_8_APPLICATION/app.py` - Added `/ai_recommend` endpoint
- `STEP_8_APPLICATION/templates/index.html` - Added UI button and JavaScript handler

### Trained Model
- `STEP_6_TRAINED_MODELS/ai_recommender.pkl` (auto-generated on first run)

## Dependencies
Install required packages in your venv:
```powershell
C:/Users/rucha/Downloads/Project/.venv/Scripts/python.exe -m pip install pandas scikit-learn joblib numpy
```

## Configuration

### Tuning Parameters
Edit `ai_recommender.py` or pass in API request:
- `spacing_km`: Grid point spacing (default 0.8 km)
- `neighbor_radius_km`: Radius for neighbor search (default 5 km)
- `n`: Number of top candidates to return (default 5)

### Retraining the Model
Delete `STEP_6_TRAINED_MODELS/ai_recommender.pkl` and run:
```python
from STEP_8_APPLICATION import ai_recommender
df = ai_recommender.load_borewells()
model_bundle = ai_recommender.train_and_save_model(df)
```

## Understanding Feature Contributions

Contributions show how each feature affects the AI score:
- **Positive (+)** = Feature increases success probability
- **Negative (-)** = Feature decreases success probability

Example:
- `depth_m: +0.523` → Deeper nearby borewells increase confidence
- `age_years: -0.045` → Older borewells slightly reduce confidence (may indicate depletion)

## Limitations & Future Improvements

### Current Limitations
- Small training dataset (30 samples) limits model accuracy
- Simple logistic regression (interpretable but less powerful)
- No geological/soil data integration
- Grid-based sampling may miss optimal spots between grid points

### Planned Improvements
- Integrate more borewell data from CGWB database
- Add geological layer data (rock type, aquifer depth, soil composition)
- Use ensemble models (Random Forest, XGBoost) for better accuracy
- Implement SHAP values for better explainability
- Add temporal analysis (seasonal water level changes)
- Distance-weighted feature aggregation instead of simple averages

## Support & Troubleshooting

### Common Issues

**Q: "No module named 'sklearn'"**
A: Install scikit-learn in your venv:
```powershell
C:/Users/rucha/Downloads/Project/.venv/Scripts/python.exe -m pip install scikit-learn
```

**Q: "Not enough training samples"**
A: Ensure `cgwb_borewells_nashik.csv` has at least 5 rows with valid data.

**Q: AI button doesn't appear**
A: Draw a rectangle on the map first (rectangle tool in top-right corner).

**Q: All candidates have same score**
A: Dataset may have low variance. Try a larger region or add more diverse borewell data.

## Example Use Cases

1. **Municipal Planning**: Select drought-prone villages and find optimal borewell locations
2. **Agricultural Projects**: Identify high-yield spots for irrigation borewells
3. **Industrial Sites**: Find reliable groundwater sources for factories/processing plants
4. **Research**: Analyze spatial patterns in groundwater availability

## License & Credits
This AI recommendation system was developed as part of the Nashik Groundwater Prediction project.
Dataset: CGWB (Central Ground Water Board), Nashik District

---
**Generated:** 2025-10-14
**Version:** 1.0
