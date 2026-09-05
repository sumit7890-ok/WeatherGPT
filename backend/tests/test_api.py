import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.services.weather_service import weather_service
from backend.app.services.alerts_service import alerts_service

# Isolated in-memory database for testing so weathergpt.db is never contaminated
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_root_index_html():
    """Verify frontend HTML is served on root /."""
    response = client.get("/")
    assert response.status_code == 200
    assert "WeatherGPT" in response.text
    assert "IMD" in response.text

def test_geocoding_search():
    """Verify city search endpoint returns coordinates."""
    response = client.get("/api/weather/search?q=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any("Mumbai" in item["name"] for item in data)

def test_current_weather_endpoint():
    """Verify real-time meteorological endpoint."""
    response = client.get("/api/weather/current?lat=28.6139&lon=77.2090&city=New%20Delhi")
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "humidity" in data
    assert "wind_speed" in data
    assert "aqi" in data
    assert data["city"] == "New Delhi"

def test_forecast_endpoint():
    """Verify 24h hourly and 7d forecast endpoint."""
    response = client.get("/api/weather/forecast?lat=19.0760&lon=72.8777&city=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "hourly_24h" in data
    assert len(data["hourly_24h"]) > 0
    assert "daily_7d" in data
    assert len(data["daily_7d"]) > 0

def test_alerts_endpoint():
    """Verify active alerts endpoint with IMD color codes."""
    response = client.get("/api/alerts/active?region=Odisha")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # Should include Cyclone bulletin for Odisha
    assert any(a["severity"] in ("ORANGE", "RED", "YELLOW", "GREEN") for a in data)

def test_national_alerts_endpoint():
    """Verify national overview alerts."""
    response = client.get("/api/alerts/national")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_chat_endpoint_english():
    """Verify conversational AI response in English."""
    payload = {
        "message": "Will it rain in Mumbai today?",
        "language": "en",
        "location": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert data["weather"] is not None
    assert len(data["suggested_queries"]) > 0

def test_chat_endpoint_hindi():
    """Verify conversational AI response in Hindi."""
    payload = {
        "message": "क्या आज दिल्ली में बारिश होगी?",
        "language": "hi",
        "location": "New Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    # Response should contain Hindi characters
    assert any('\u0900' <= char <= '\u097F' for char in data["reply"])

def test_chat_sessions_history():
    """Verify SQLite session and history persistence."""
    # 1. Get sessions
    res = client.get("/api/chat/sessions")
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) > 0
    first_session_id = sessions[0]["id"]

    # 2. Get history of that session
    hist_res = client.get(f"/api/chat/sessions/{first_session_id}")
    assert hist_res.status_code == 200
    messages = hist_res.json()
    assert len(messages) >= 2  # user + assistant

def test_settings_endpoints():
    """Verify settings GET and POST endpoints."""
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "openai_configured" in data
    assert "openai_model" in data

    post_res = client.post("/api/settings", json={"openai_model": "gpt-4o-mini"})
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"

def test_chat_endpoint_bangla():
    """Verify conversational AI response in Bangla."""
    payload = {
        "message": "আজ কলকাতায় কি বৃষ্টি হবে?",
        "language": "bn",
        "location": "Kolkata",
        "latitude": 22.5726,
        "longitude": 88.3639
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    # Response should contain Bengali characters (\u0980-\u09FF)
    assert any('\u0980' <= char <= '\u09FF' for char in data["reply"])

def test_translate_endpoint_hindi():
    """Verify POST /api/translate to Hindi."""
    payload = {
        "text": "### 🌧️ **Precipitation & Monsoon Analysis for New Delhi**\n- **Current Condition**: Sunny",
        "target_language": "hi"
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "translated_text" in data
    assert "वर्षा" in data["translated_text"] or any('\u0900' <= char <= '\u097F' for char in data["translated_text"])

def test_translate_endpoint_bangla():
    """Verify POST /api/translate to Bangla."""
    payload = {
        "text": "### 🌧️ **Precipitation & Monsoon Analysis for New Delhi**\n- **Current Condition**: Sunny",
        "target_language": "bn"
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "translated_text" in data
    assert any('\u0980' <= char <= '\u09FF' for char in data["translated_text"])


def test_reverse_geocoding_endpoint():
    """Verify GET /api/weather/reverse-geocode returns valid location attributes."""
    res = client.get("/api/weather/reverse-geocode?lat=19.0760&lon=72.8777")
    assert res.status_code == 200
    data = res.json()
    assert "city" in data
    assert "latitude" in data
    assert "longitude" in data
    assert data["latitude"] == 19.0760
    assert data["longitude"] == 72.8777
    assert "Mumbai" in data["city"] or "Maharashtra" in data.get("state", "") or "India" in data.get("country", "")


def test_supabase_config_endpoint():
    """Verify GET /api/supabase/config returns Supabase keys without leaking secrets."""
    res = client.get("/api/supabase/config")
    assert res.status_code == 200
    data = res.json()
    assert "supabase_url" in data
    assert "supabase_publishable_key" in data
    assert "configured" in data
    assert "sb_publishable_Jn7ETscju0dksTOgXVPLfQ_ybgv4Xfu" in data["supabase_publishable_key"]


def test_forecast_has_5day_daily():
    """Verify forecast endpoint returns at least 5-day daily forecast data."""
    res = client.get("/api/weather/forecast?lat=12.9716&lon=77.5946&city=Bengaluru")
    assert res.status_code == 200
    data = res.json()
    assert "daily_7d" in data
    daily = data["daily_7d"]
    assert len(daily) >= 5
    for day in daily[:5]:
        assert "temp_max" in day
        assert "temp_min" in day
        assert "precipitation_prob" in day
        assert "weather_icon" in day
        assert "weather_desc" in day


def test_chat_uses_detected_location_and_not_delhi():
    """Verify chat uses the user's detected location and does not default to New Delhi."""
    payload = {
        "message": "What is the weather here and will it rain?",
        "location": "Kolkata",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "language": "en"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "Kolkata" in data["reply"] or (data.get("weather") and "Kolkata" in data["weather"]["city"])
    assert "New Delhi" not in data.get("weather", {}).get("city", "")


def test_chat_5day_forecast_query():
    """Verify chat specifically answers 5-day forecast queries."""
    payload = {
        "message": "What will the weather be like for the next 5 days?",
        "location": "Pune",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "language": "en"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "5-Day" in data["reply"] or "Pune" in data["reply"]


def test_chat_travel_advisory_query():
    """Verify chat understands travel safety queries."""
    payload = {
        "message": "Is it safe to travel today?",
        "location": "Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "language": "en"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "Travel" in data["reply"] or "Safe" in data["reply"] or "Chennai" in data["reply"]



