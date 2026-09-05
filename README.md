# WeatherGPT: Conversational AI for Weather Forecasting, Alerts & Climate Information

**Developed for the Ministry of Earth Sciences (MoES) & India Meteorological Department (IMD)**  
**Theme**: Disaster Management | **Category**: Software

---

## 🏛️ System Architecture

```
                          WEATHERGPT
                               |
              ┌────────────────┴────────────────┐
              |                                 |
          FRONTEND                           BACKEND
       HTML / CSS / JS                    Python FastAPI
              |                                 |
              |               ┌─────────────────┼─────────────────┐
              |               |                 |                 |
              |            AI Engine       Weather API       Alerts API
              |          (LLM + Domain     (Open-Meteo /     (IMD 4-Color
              |           Meteorology)      Forecast/AQI)      Warnings)
              |               |                 |                 |
              └───────────────┴────────┬────────┴─────────────────┘
                                       |
                                     SQLite
                        (Chat Sessions, Messages, Alerts,
                               Location Bookmarks)
```

---

## ✨ Key Features

1. **Conversational AI Meteorological Assistant (AI API)**:
   - Natural language querying for weather conditions, precipitation chances, and severe storms.
   - Dual-engine architecture: Zero-config deterministic meteorological NLP engine + seamless Google Gemini LLM integration (`gemini-2.5-flash`).
   - Multilingual support: Full capability in **English** and **Hindi (हिन्दी)** with instant language toggling.
   - Sector-specific advisories:
     - 🌾 **Farmers**: Agrometeorology advice on sowing, irrigation scheduling, and pesticide application.
     - 🐟 **Fishermen**: Coastal squall warnings and sea condition advisories.
     - 🏙️ **Urban Citizens**: Local waterlogging risks, transit impacts, heat stress, and UV protection.

2. **Real-Time Meteorological & Forecast Intelligence (Weather API)**:
   - Live Temperature, Feels-like, Relative Humidity, Wind Speed/Direction/Gusts, Barometric Pressure, Cloud Cover.
   - 24-Hour Hourly Forecast trend with rain probabilities.
   - 7-Day Extended Outlook with maximum and minimum temperatures.
   - Air Quality Index (AQI: PM2.5, PM10) mapped to Central Pollution Control Board (CPCB) categories.
   - Built-in Geocoding search supporting Indian cities, districts, and coordinates.

3. **Disaster Management & Early Warning System (Alerts API)**:
   - Official IMD 4-tier warning color coding:
     - 🟢 **Green (No Warning)**: Normal, safe conditions.
     - 🟡 **Yellow (Watch)**: Be updated on changing weather.
     - 🟠 **Orange (Alert)**: Be prepared — severe weather disruptions expected.
     - 🔴 **Red (Warning)**: Take action — extreme weather danger / emergency protocols.
   - Live hazard classification: Cyclones & Squalls, Extremely Heavy Rainfall & Floods, Severe Heatwaves, Thunderstorms & Lightning.
   - Real-time emergency marquee ticker across all screens.

4. **Persistent SQLite Storage**:
   - Stores user chat history, multi-turn conversation context, bookmarked locations, and alert records.

5. **Modern Glassmorphic Web UI**:
   - Single-page application with responsive split layout.
   - Voice Dictation (Speech-to-Text via Web Speech API) and Text-to-Speech (TTS) audio playback.
   - Quick suggestion prompt pills and instant city selector pills.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Internet connection (for live meteorological data)

### 2. Setup Virtual Environment & Install Dependencies
```powershell
# In project root: x:\Prototype WeatherGPT
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
```

### 3. (Optional) Configure Gemini API Key
Create a `.env` file from `.env.example`:
```powershell
Copy-Item .env.example .env
```
Add your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: WeatherGPT includes a built-in domain meteorological engine, so it works completely even without an API key!)*

### 4. Run the Platform
```powershell
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Web Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
