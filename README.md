# 🌊 Groundwater Prediction System - Nashik District

## 📋 Project Overview

AI-powered groundwater level prediction system for Nashik District using machine learning, real-time data, and interactive visualization.

## 🎯 Features

- 🗺️ **Interactive Map**: Click to select location, GPS support
- 🤖 **AI Predictions**: XGBoost ML model with **dynamic confidence** (50-98%)
- 🎨 **Area Predictions**: Heatmap showing groundwater levels
- 🏗️ **Borewell Database**: 30 CGWB borewells with success/failure data
- 🔍 **Smart Search**: AI-powered location search
- 🌙 **Dark Mode**: Complete dark theme support

## 📁 Project Structure (Step-by-Step)

```
Project/
├── STEP_1_RAW_DATA/              📊 Original Excel files from IMD, CGWB
├── STEP_2_DATA_PREPROCESSING/    🔧 Scripts to convert Excel → CSV
├── STEP_3_PROCESSED_DATA/        📋 Cleaned CSV files
├── STEP_4_DATA_INTEGRATION/      🔗 Combined master dataset
├── STEP_5_MODEL_TRAINING/        🤖 ML model training scripts
├── STEP_6_TRAINED_MODELS/        💾 Saved .pkl models
├── STEP_7_SUPPORTING_DATA/       📁 Borewells, locations
├── STEP_8_APPLICATION/           🌐 Flask web app
└── STEP_9_TESTING/               🧪 Test scripts
```

## 🔄 Complete Workflow

```
Raw Data (STEP 1)
    ↓
Convert to CSV (STEP 2)
    ↓
Cleaned Data (STEP 3)
    ↓
Combine Datasets (STEP 4)
    ↓
Train Models (STEP 5)
    ↓
Save Models (STEP 6)
    ↓
Flask App (STEP 8) ← Supporting Data (STEP 7)
    ↓
Testing (STEP 9)
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install flask pandas numpy xgboost scikit-learn requests google-generativeai
```

### 2. Run Application
```bash
cd STEP_8_APPLICATION
python app.py
```

### 3. Open Browser
```
http://127.0.0.1:5000/
```

## 📖 Documentation

Each STEP folder has its own README.md explaining:
- What it contains
- How to use it
- Input/Output flow

**Start with**: `STEP_1_RAW_DATA/README.md`

## 🛠️ Technology Stack

- **Backend**: Python 3.12, Flask, XGBoost, Pandas, NumPy
- **Frontend**: HTML5, Tailwind CSS, Leaflet.js, JavaScript
- **APIs**: Google Maps, Google Gemini AI, OpenStreetMap
- **Data Sources**: IMD, CGWB, State Government

## 🎯 Model Performance

- **Algorithm**: XGBoost Regressor
- **Training Data**: 10,000+ samples
- **Confidence**: Dynamic (50-98%) based on:
  - Location proximity to training data (35%)
  - Feature quality (25%)
  - Model uncertainty (30%)
  - Data completeness (10%)

## 📊 Dataset Details

- **Total Records**: 10,000+
- **Locations**: 500+ in Nashik District
- **Time Range**: 2016-2025
- **Parameters**: Latitude, Longitude, Rainfall, Temperature, River Level
- **Borewells**: 30 CGWB records

## 🧪 Testing

```bash
cd STEP_9_TESTING
python test_ai_search.py
python test_borewell_api.py
python verify_dataset.py
```

## 📱 User Interface

- Full-screen interactive map
- Real-time predictions (no page refresh)
- Color-coded confidence indicators
- Area predictions with heatmap
- Dark mode support

## 🎉 New Features

### Dynamic Confidence Score
Confidence is now **DYNAMIC** (not static 95%):
- 🟢 90-98% = Excellent
- 🟡 80-89% = Very Good
- 🟠 70-79% = Good
- 🟤 60-69% = Fair
- 🔴 50-59% = Low

### No Page Refresh
- AJAX-based predictions
- Map and inputs stay visible
- Smooth user experience

---

**Version**: 2.0  
**Last Updated**: October 9, 2025  
**Status**: Production Ready ✅
