import re
import uuid
import json
import logging
import asyncio
import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .config import settings
from .database import engine, Base, get_db
from .models import ChatSession, ChatMessage, SavedLocation, AlertRecord
from .schemas import (
    ChatRequest,
    ChatResponse,
    WeatherCurrent,
    WeatherForecastResponse,
    AlertItem,
    LocationSearchItem,
    ChatMessageSchema,
    SessionSummary,
    TranslateRequest,
    TranslateResponse,
)
from .services.weather_service import weather_service, INDIAN_CITIES_COORDS
from .services.alerts_service import alerts_service
from .services.ai_service import ai_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weathergpt")

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WeatherGPT API - MoES / IMD Weather & Disaster Intelligence",
    version=settings.APP_VERSION,
    description="Conversational AI platform for real-time meteorological intelligence, forecasts, and disaster warnings."
)

# Enable CORS for all origins and local file access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

# Seed default locations on startup
@app.on_event("startup")
def startup_seed_locations():
    db = next(get_db())
    try:
        count = db.query(SavedLocation).count()
        if count == 0:
            defaults = [
                SavedLocation(name="New Delhi", state="Delhi", country="India", lat=28.6139, lon=77.2090, is_default=True),
                SavedLocation(name="Mumbai", state="Maharashtra", country="India", lat=19.0760, lon=72.8777, is_default=False),
                SavedLocation(name="Kolkata", state="West Bengal", country="India", lat=22.5726, lon=88.3639, is_default=False),
                SavedLocation(name="Chennai", state="Tamil Nadu", country="India", lat=13.0827, lon=80.2707, is_default=False),
                SavedLocation(name="Bengaluru", state="Karnataka", country="India", lat=12.9716, lon=77.5946, is_default=False),
            ]
            db.add_all(defaults)
            db.commit()
    except Exception as e:
        logger.error(f"Startup seed error: {e}")
    finally:
        db.close()


@app.get("/api/config")
async def get_client_config():
    """Provides public client configuration (e.g. Google Maps API key, Supabase public URL/key) securely."""
    return {
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "supabase_url": settings.SUPABASE_URL,
        "supabase_publishable_key": settings.SUPABASE_PUBLISHABLE_KEY,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }


# ----------------------------------------------------
# Geographic Resolution & Knowledge Base
# ----------------------------------------------------

KNOWN_GLOBAL_LOCATIONS = {
    # Continents
    "africa": ("Nairobi, Kenya (Africa)", 1.2921, 36.8219),
    "asia": ("Singapore (Asia)", 1.3521, 103.8198),
    "europe": ("Paris, France (Europe)", 48.8566, 2.3522),
    "north america": ("Chicago, USA (North America)", 41.8781, -87.6298),
    "south america": ("São Paulo, Brazil (South America)", -23.5505, -46.6333),
    "australia": ("Sydney, Australia", -33.8688, 151.2093),
    "antarctica": ("Antarctica", -82.8628, 135.0000),

    # Countries
    "japan": ("Tokyo, Japan", 35.6762, 139.6503),
    "usa": ("Washington, D.C., United States", 38.8951, -77.0364),
    "united states": ("Washington, D.C., United States", 38.8951, -77.0364),
    "america": ("Washington, D.C., United States", 38.8951, -77.0364),
    "uk": ("London, United Kingdom", 51.5074, -0.1278),
    "united kingdom": ("London, United Kingdom", 51.5074, -0.1278),
    "britain": ("London, United Kingdom", 51.5074, -0.1278),
    "england": ("London, United Kingdom", 51.5074, -0.1278),
    "russia": ("Moscow, Russia", 55.7558, 37.6173),
    "china": ("Beijing, China", 39.9042, 116.4074),
    "canada": ("Ottawa, Canada", 45.4215, -75.6972),
    "france": ("Paris, France", 48.8566, 2.3522),
    "germany": ("Berlin, Germany", 52.5200, 13.4050),
    "italy": ("Rome, Italy", 41.9028, 12.4964),
    "spain": ("Madrid, Spain", 40.4168, -3.7038),
    "brazil": ("Brasília, Brazil", -15.7975, -47.8919),
    "india": ("New Delhi, India", 28.6139, 77.2090),
    "bangladesh": ("Dhaka, Bangladesh", 23.8103, 90.4125),
    "pakistan": ("Islamabad, Pakistan", 33.6844, 73.0479),
    "uae": ("Dubai, United Arab Emirates", 25.2048, 55.2708),
    "dubai": ("Dubai, United Arab Emirates", 25.2048, 55.2708),
    "singapore": ("Singapore", 1.3521, 103.8198),
    "thailand": ("Bangkok, Thailand", 13.7563, 100.5018),
    "indonesia": ("Jakarta, Indonesia", -6.2088, 106.8456),
    "malaysia": ("Kuala Lumpur, Malaysia", 3.1390, 101.6869),
    "philippines": ("Manila, Philippines", 14.5995, 120.9842),
    "vietnam": ("Hanoi, Vietnam", 21.0285, 105.8542),
    "south korea": ("Seoul, South Korea", 37.5665, 126.9780),
    "korea": ("Seoul, South Korea", 37.5665, 126.9780),
    "turkey": ("Ankara, Turkey", 39.9334, 32.8597),
    "saudi arabia": ("Riyadh, Saudi Arabia", 24.7136, 46.6753),
    "egypt": ("Cairo, Egypt", 30.0444, 31.2357),
    "south africa": ("Pretoria, South Africa", -25.7479, 28.2293),
    "mexico": ("Mexico City, Mexico", 19.4326, -99.1332),
    "new zealand": ("Wellington, New Zealand", -41.2865, 174.7762),
    "argentina": ("Buenos Aires, Argentina", -34.6037, -58.3816),
    "nepal": ("Kathmandu, Nepal", 27.7172, 85.3240),
    "sri lanka": ("Colombo, Sri Lanka", 6.9271, 79.8612),

    # States / Provinces
    "california": ("California, United States", 36.7783, -119.4179),
    "texas": ("Texas, United States", 31.9686, -99.9018),
    "florida": ("Florida, United States", 27.6648, -81.5158),
    "new york": ("New York, United States", 40.7128, -74.0060),
    "washington": ("Washington, United States", 47.7511, -120.7401),
    "illinois": ("Illinois, United States", 40.6331, -89.3985),
    "pennsylvania": ("Pennsylvania, United States", 41.2033, -77.1945),
    "ohio": ("Ohio, United States", 40.4173, -82.9071),
    "georgia": ("Georgia, United States", 32.1656, -82.9001),
    "north carolina": ("North Carolina, United States", 35.7596, -79.0193),
    "michigan": ("Michigan, United States", 44.3148, -85.6024),
    "west bengal": ("West Bengal, India", 22.9868, 87.8550),
    "maharashtra": ("Maharashtra, India", 19.7515, 75.7139),
    "karnataka": ("Karnataka, India", 15.3173, 75.7139),
    "tamil nadu": ("Tamil Nadu, India", 11.1271, 78.6569),
    "uttar pradesh": ("Uttar Pradesh, India", 26.8467, 80.9462),
    "gujarat": ("Gujarat, India", 22.2587, 71.1924),
    "rajasthan": ("Rajasthan, India", 27.0238, 74.2179),
    "punjab": ("Punjab, India", 31.1471, 75.3412),
    "kerala": ("Kerala, India", 10.8505, 76.2711),
    "delhi": ("New Delhi, India", 28.6139, 77.2090),
    "bihar": ("Bihar, India", 25.0961, 85.3131),
    "odisha": ("Odisha, India", 20.9517, 85.0985),
    "assam": ("Assam, India", 26.2006, 92.9376),
    "haryana": ("Haryana, India", 29.0588, 76.0856),
    "telangana": ("Telangana, India", 18.1124, 79.0193),
    "andhra pradesh": ("Andhra Pradesh, India", 15.9129, 79.7400),
    "madhya pradesh": ("Madhya Pradesh, India", 22.9734, 78.6569),
    "jharkhand": ("Jharkhand, India", 23.6102, 85.2799),
    "uttarakhand": ("Uttarakhand, India", 30.0668, 79.0193),
    "himachal pradesh": ("Himachal Pradesh, India", 31.1048, 77.1734),
    "goa": ("Goa, India", 15.2993, 74.1240),
    "jammu and kashmir": ("Srinagar, Jammu and Kashmir, India", 34.0837, 74.7973),
    "kashmir": ("Srinagar, Jammu and Kashmir, India", 34.0837, 74.7973),

    # Major Cities
    "tokyo": ("Tokyo, Japan", 35.6762, 139.6503),
    "london": ("London, United Kingdom", 51.5074, -0.1278),
    "paris": ("Paris, France", 48.8566, 2.3522),
    "kolkata": ("Kolkata, West Bengal, India", 22.5726, 88.3639),
    "mumbai": ("Mumbai, Maharashtra, India", 19.0760, 72.8777),
    "durgapur": ("Durgapur, West Bengal, India", 23.5204, 87.3119),
    "asansol": ("Asansol, West Bengal, India", 23.6889, 86.9661),
    "siliguri": ("Siliguri, West Bengal, India", 26.7271, 88.3953),
    "howrah": ("Howrah, West Bengal, India", 22.5958, 88.2636),
    "darjeeling": ("Darjeeling, West Bengal, India", 27.0410, 88.2663),
    "bengaluru": ("Bengaluru, Karnataka, India", 12.9716, 77.5946),
    "bangalore": ("Bengaluru, Karnataka, India", 12.9716, 77.5946),
    "hyderabad": ("Hyderabad, Telangana, India", 17.3850, 78.4867),
    "chennai": ("Chennai, Tamil Nadu, India", 13.0827, 80.2707),
    "pune": ("Pune, Maharashtra, India", 18.5204, 73.8567),
    "ahmedabad": ("Ahmedabad, Gujarat, India", 23.0225, 72.5714),
    "jaipur": ("Jaipur, Rajasthan, India", 26.9124, 75.7873),
    "lucknow": ("Lucknow, Uttar Pradesh, India", 26.8467, 80.9462),
    "patna": ("Patna, Bihar, India", 25.5941, 85.1376),
    "chandigarh": ("Chandigarh, India", 30.7333, 76.7794),
    "sydney": ("Sydney, Australia", -33.8688, 151.2093),
    "los angeles": ("Los Angeles, California, USA", 34.0522, -118.2437),
    "chicago": ("Chicago, Illinois, USA", 41.8781, -87.6298),
    "san francisco": ("San Francisco, California, USA", 37.7749, -122.4194),
    "seattle": ("Seattle, Washington, USA", 47.6062, -122.3321),
    "miami": ("Miami, Florida, USA", 25.7617, -80.1918),
    "toronto": ("Toronto, Canada", 43.6532, -79.3832),
    "vancouver": ("Vancouver, Canada", 49.2827, -123.1207),
    "berlin": ("Berlin, Germany", 52.5200, 13.4050),
    "rome": ("Rome, Italy", 41.9028, 12.4964),
    "madrid": ("Madrid, Spain", 40.4168, -3.7038),
    "moscow": ("Moscow, Russia", 55.7558, 37.6173),
    "beijing": ("Beijing, China", 39.9042, 116.4074),
    "shanghai": ("Shanghai, China", 31.2304, 121.4737),
    "seoul": ("Seoul, South Korea", 37.5665, 126.9780),
    "bangkok": ("Bangkok, Thailand", 13.7563, 100.5018),
    "cairo": ("Cairo, Egypt", 30.0444, 31.2357),
    # West Bengal Districts & Towns (User Request)
    "bardhaman": ("Bardhaman, West Bengal, India", 23.2496, 87.8682),
    "bardhamman": ("Bardhaman, West Bengal, India", 23.2496, 87.8682),
    "burdwan": ("Bardhaman, West Bengal, India", 23.2496, 87.8682),
    "purba bardhaman": ("Purba Bardhaman, West Bengal, India", 23.2496, 87.8682),
    "paschim bardhaman": ("Paschim Bardhaman, West Bengal, India", 23.6462, 87.1588),
    "kharagpur": ("Kharagpur, West Bengal, India", 22.3431, 87.3013),
    "kharagpore": ("Kharagpur, West Bengal, India", 22.3431, 87.3013),
    "midnapore": ("Midnapore, West Bengal, India", 22.4257, 87.3199),
    "medinipur": ("Midnapore, West Bengal, India", 22.4257, 87.3199),
    "purba medinipur": ("Purba Medinipur, West Bengal, India", 22.1466, 87.7719),
    "paschim medinipur": ("Paschim Medinipur, West Bengal, India", 22.4257, 87.3199),
    "bankura": ("Bankura, West Bengal, India", 23.2324, 87.0715),
    "purulia": ("Purulia, West Bengal, India", 23.3321, 86.3652),
    "murshidabad": ("Murshidabad, West Bengal, India", 24.1837, 88.2683),
    "berhampore": ("Berhampore, West Bengal, India", 24.0984, 88.2514),
    "baharampur": ("Berhampore, West Bengal, India", 24.0984, 88.2514),
    "nadia": ("Nadia, West Bengal, India", 23.4710, 88.5565),
    "krishnanagar": ("Krishnanagar, West Bengal, India", 23.4013, 88.4975),
    "hooghly": ("Hooghly, West Bengal, India", 22.8963, 88.3980),
    "chinsurah": ("Chinsurah, West Bengal, India", 22.8963, 88.3980),
    "howrah": ("Howrah, West Bengal, India", 22.5958, 88.2636),
    "north 24 parganas": ("North 24 Parganas, West Bengal, India", 22.7210, 88.4820),
    "barasat": ("Barasat, West Bengal, India", 22.7210, 88.4820),
    "south 24 parganas": ("South 24 Parganas, West Bengal, India", 22.1352, 88.5447),
    "alipore": ("Alipore, Kolkata, West Bengal, India", 22.5312, 88.3276),
    "jalpaiguri": ("Jalpaiguri, West Bengal, India", 26.5405, 88.7196),
    "alipurduar": ("Alipurduar, West Bengal, India", 26.4919, 89.5271),
    "cooch behar": ("Cooch Behar, West Bengal, India", 26.3236, 89.4510),
    "darjeeling": ("Darjeeling, West Bengal, India", 27.0410, 88.2663),
    "kalimpong": ("Kalimpong, West Bengal, India", 27.0667, 88.4667),
    "uttar dinajpur": ("Uttar Dinajpur, West Bengal, India", 25.6267, 88.1306),
    "raiganj": ("Raiganj, West Bengal, India", 25.6267, 88.1306),
    "dakshin dinajpur": ("Dakshin Dinajpur, West Bengal, India", 25.2215, 88.7667),
    "balurghat": ("Balurghat, West Bengal, India", 25.2215, 88.7667),
    "malda": ("Malda, West Bengal, India", 25.0045, 88.1457),
    "birbhum": ("Birbhum, West Bengal, India", 23.9056, 87.5246),
    "suri": ("Suri, West Bengal, India", 23.9056, 87.5246),
    "bolpur": ("Bolpur, West Bengal, India", 23.6693, 87.6843),
    "shantiniketan": ("Shantiniketan, West Bengal, India", 23.6797, 87.6888),
    "santiniketan": ("Shantiniketan, West Bengal, India", 23.6797, 87.6888),
    "haldia": ("Haldia, West Bengal, India", 22.0667, 88.0698),
    "digha": ("Digha, West Bengal, India", 21.6266, 87.5074),
    "panchla": ("Panchla, Howrah, West Bengal, India", 22.5398, 88.1444),
    "serampore": ("Serampore, West Bengal, India", 22.7504, 88.3434),
    "chandannagar": ("Chandannagar, West Bengal, India", 22.8671, 88.3674),
    "ranaghat": ("Ranaghat, West Bengal, India", 23.1802, 88.5804),
    "kalyani": ("Kalyani, West Bengal, India", 22.9750, 88.4344),
    "barrackpore": ("Barrackpore, West Bengal, India", 22.7634, 88.3756),
    "dum dum": ("Dum Dum, Kolkata, West Bengal, India", 22.6420, 88.4312),
    "salt lake": ("Salt Lake, Kolkata, West Bengal, India", 22.5804, 88.4178),
    "new town": ("New Town, Kolkata, West Bengal, India", 22.5867, 88.4847),

    "rio de janeiro": ("Rio de Janeiro, Brazil", -22.9068, -43.1729),
}

GLOBAL_COUNTRY_CAPITALS = KNOWN_GLOBAL_LOCATIONS

def parse_target_date(text: str, forecast_dates: List[str]) -> Optional[str]:
    """
    Matches natural language date or day query to one of the 7-day forecast ISO dates.
    """
    lower = text.lower()
    today = datetime.date.today()
    if forecast_dates:
        try:
            today = datetime.date.fromisoformat(forecast_dates[0])
        except Exception:
            pass

    if "tomorrow" in lower:
        target = today + datetime.timedelta(days=1)
        target_str = target.isoformat()
        if target_str in forecast_dates:
            return target_str

    if "day after tomorrow" in lower:
        target = today + datetime.timedelta(days=2)
        target_str = target.isoformat()
        if target_str in forecast_dates:
            return target_str

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, w in enumerate(weekdays):
        if re.search(rf"\b{w}\b", lower):
            for f_str in forecast_dates:
                try:
                    dt = datetime.date.fromisoformat(f_str)
                    if dt.weekday() == i:
                        return f_str
                except Exception:
                    pass

    m_iso = re.search(r'\b(202\d-\d{1,2}-\d{1,2})\b', text)
    if m_iso and m_iso.group(1) in forecast_dates:
        return m_iso.group(1)

    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    m_day_month = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]+)\b', lower)
    if m_day_month:
        day_num = int(m_day_month.group(1))
        month_str = m_day_month.group(2)
        if month_str in months:
            month_num = months[month_str]
            for f_str in forecast_dates:
                try:
                    dt = datetime.date.fromisoformat(f_str)
                    if dt.day == day_num and dt.month == month_num:
                        return f_str
                except Exception:
                    pass

    m_month_day = re.search(r'\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b', lower)
    if m_month_day:
        month_str = m_month_day.group(1)
        day_num = int(m_month_day.group(2))
        if month_str in months:
            month_num = months[month_str]
            for f_str in forecast_dates:
                try:
                    dt = datetime.date.fromisoformat(f_str)
                    if dt.day == day_num and dt.month == month_num:
                        return f_str
                except Exception:
                    pass

    m_day_only = re.search(r'\b(?:on|of|the)\s+(\d{1,2})(?:st|nd|rd|th)\b', lower)
    if m_day_only:
        day_num = int(m_day_only.group(1))
        for f_str in forecast_dates:
            try:
                dt = datetime.date.fromisoformat(f_str)
                if dt.day == day_num:
                    return f_str
            except Exception:
                pass

    return None

def _detect_comparison_query(text: str) -> Optional[tuple[str, str]]:
    """Detects if user asks for a comparison between two places."""
    lower = text.lower()
    patterns = [
        r'(?:compare|comparison|difference)(?:\s+(?:the\s+)?weather)?\s+(?:between\s+)?([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+?)\s+(?:and|with|to|vs|versus)\s+([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+)',
        r'([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+?)\s+(?:vs|versus)\s+([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+)',
        r'(?:which is|is)\s+(?:colder|hotter|warmer|rainier|drier|better)\s+(?:between\s+)?([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+?)\s+(?:or|and)\s+([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+)',
        r'(?:तुलना|তুলনা)\s+([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+?)\s+(?:और|এবং|व|এবং)\s+([a-zA-Z\u0900-\u097F\u0980-\u09FF\s]+)'
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            c1 = m.group(1).replace("weather", "").replace("in", "").replace("of", "").replace("between", "").strip(" ?.,!")
            c2 = m.group(2).replace("weather", "").replace("in", "").replace("of", "").strip(" ?.,!")
            if c1 and c2 and len(c1) >= 2 and len(c2) >= 2:
                return c1, c2
    return None

def _detect_nearby_institutions_query(text: str) -> Optional[tuple[str, Optional[str]]]:
    """
    Detects if user asks for nearby institutions (e.g. colleges, hospitals, schools, banks, etc.)
    near a location or 'me'.
    Returns (category, target_location_or_none).
    """
    lower = text.lower().strip(" ?.,!;:()\"'")

    cats = {
        "college": ["colleges", "college", "universities", "university", "campus", "campuses", "মহাবিদ্যালয়", "কলেজ", "विश्वविद्यालय", "कॉलेज"],
        "hospital": ["hospitals", "hospital", "clinics", "clinic", "healthcare", "medical center", "medical centers", "হাসপাতাল", "अस्पताल"],
        "school": ["schools", "school", "high school", "high schools", "academy", "academies", "বিদ্যালয়", "স্কুল", "स्कूल"],
        "bank": ["banks", "bank", "atms", "atm", "ব্যাংক", "बैंक"],
        "police": ["police stations", "police station", "police", "থানা", "পুলিশ", "पुलिस"],
        "pharmacy": ["pharmacies", "pharmacy", "chemists", "chemist", "drugstores", "drugstore", "ওষুধের দোকান", "दवा की दुकान"],
        "park": ["parks", "park", "gardens", "garden", "উদ্যান", "পার্ক", "बगीचा", "पार्क"],
        "restaurant": ["restaurants", "restaurant", "cafes", "cafe", "diners", "diner", "রেস্তোরাঁ", "রেস্টুরেন্ট", "होटल", "रेस्तरां"]
    }

    matched_cat = None
    for cat_key, synonyms in cats.items():
        for syn in synonyms:
            if re.search(rf"\b{re.escape(syn)}\b", lower):
                matched_cat = cat_key
                break
        if matched_cat:
            break

    if not matched_cat:
        return None

    # Check for target location: "... (colleges) near/around/in/at (target) ..."
    m = re.search(r'(?:near|around|close\s+to|in|at)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s,-]+?)(?:\s+(?:with\s+their\s+weather|with\s+weather|weather|please)|[?.!,]|$)', lower)
    if m:
        target = m.group(1).strip()
        target = re.sub(r'^(?:the\s+city\s+of|the\s+town\s+of|the|my\s+area|area)\s+', '', target).strip()
        if target in ("me", "here", "my location", "current location", "us", "আমার অবস্থান", "मेरी लोकेशन", "यहाँ", "यहां"):
            return matched_cat, "me"
        if len(target) >= 2:
            return matched_cat, target

    if any(phrase in lower for phrase in ["near me", "nearby", "around here", "close by", "near us", "কাছে", "কাছাকাছি", "आसपास"]):
        return matched_cat, "me"

    if any(verb in lower for verb in ["show", "find", "list", "get", "tell me", "display", "all", "দেখাও", "खोजो"]):
        return matched_cat, "me"

    return None

def _detect_matching_locations_query(text: str) -> Optional[str]:
    """
    Detects queries asking for all matching locations for a query string.
    E.g. 'Show all matching locations for Springfield', 'All places named Springfield',
    'Show matching places for 700001'.
    Returns location query string.
    """
    lower = text.lower().strip(" ?.,!;:()\"'")
    m = re.search(r'(?:show|list|find|display|search)\s+(?:all\s+)?(?:matching\s+)?(?:locations?|places?|results?|cities|towns)\s+(?:for|in|of|named)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s,-]+?)(?:\s+(?:with\s+their\s+weather|with\s+weather|weather|please)|[?.!,]|$)', lower)
    if m:
        return m.group(1).strip()

    m2 = re.search(r'(?:all\s+places\s+named|all\s+locations\s+named|all\s+matching\s+places\s+for|matching\s+locations\s+for)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s,-]+?)(?:\s+(?:with\s+their\s+weather|with\s+weather|weather|please)|[?.!,]|$)', lower)
    if m2:
        return m2.group(1).strip()

    return None

NON_LOCATION_WORDS = {
    # Question words
    "what", "who", "where", "when", "why", "how", "which", "whose", "whom",
    # Verbs & auxiliaries
    "is", "are", "am", "was", "were", "be", "been", "being",
    "do", "does", "did", "done", "have", "has", "had", "having",
    "can", "could", "shall", "should", "will", "would", "may", "might", "must",
    "go", "going", "gone", "went", "get", "got", "take", "taking", "took", "need", "needs",
    "feel", "feels", "felt", "look", "looks", "see", "tell", "show", "give", "help", "know",
    "wear", "wearing", "carry", "carrying", "affect", "travel", "traveling",
    # Pronouns & determiners
    "i", "me", "my", "myself", "we", "us", "our", "ours", "you", "your", "yours",
    "he", "him", "his", "she", "her", "hers", "it", "its", "they", "them", "their", "theirs",
    "this", "that", "these", "those", "the", "a", "an", "all", "any", "some", "every",
    # Prepositions & conjunctions
    "in", "on", "at", "to", "for", "of", "with", "about", "by", "from", "between", "into", "through",
    "and", "or", "but", "so", "if", "then", "because", "as", "than", "like",
    # Weather terms
    "weather", "forecast", "climate", "temperature", "temp", "rain", "raining", "rainy", "rains",
    "snow", "snowing", "snowy", "sunny", "sun", "sunshine", "cloud", "clouds", "cloudy", "overcast",
    "wind", "windy", "breeze", "breezy", "storm", "storms", "stormy", "thunderstorm",
    "humidity", "humid", "pressure", "aqi", "air", "pollution", "uv", "index", "heat", "hot",
    "cold", "colder", "warmer", "warm", "cool", "umbrella", "jacket", "coat", "clothes", "clothing",
    "outdoor", "outdoors", "outside", "sports", "trip",
    # Time words
    "today", "tomorrow", "tonight", "yesterday", "now", "current", "currently", "morning",
    "afternoon", "evening", "night", "day", "days", "week", "weeks", "month", "months", "year", "years",
    "weekend", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    # Conversational, Greetings & general
    "hello", "hi", "hii", "hiii", "hiiii", "hey", "heyy", "heyyy", "helo", "helllo", "helloo",
    "hola", "namaste", "namaskar", "pranam", "pranaam", "greetings", "greeting", "howdy", "hiya", "sup", "yo",
    "kemon", "acho", "achis", "achen", "kaise", "kya", "haal", "chal", "khobor", "bhalo",
    "weathergpt", "gpt", "chatbot", "bot", "ai", "assistant",
    "bro", "buddy", "friend", "sir", "mam", "madam", "dude", "mate",
    "thanks", "thank", "thankyou", "please", "yes", "no", "ok", "okay",
    "good", "bad", "better", "best", "difference", "compare", "comparison", "right", "here", "there",
    "fine", "great", "cool", "awesome", "bye", "cya", "see", "ya"
}

def _is_valid_location_candidate(text: str) -> bool:
    clean = text.lower().strip(" ?.,!;:()\"'~`@#$%^&*-_+=/\\|")
    if not clean or len(clean) < 2:
        return False
    if ai_service.is_greeting(clean):
        return False
    words = clean.split()
    meaningful_words = []
    for w in words:
        if w in NON_LOCATION_WORDS:
            continue
        w_c = re.sub(r'([a-z])\1+', r'\1', w)
        w_d = re.sub(r'([a-z])\1+', r'\1\1', w)
        if w_c in NON_LOCATION_WORDS or (w_c + "o") in NON_LOCATION_WORDS or w_d in NON_LOCATION_WORDS:
            continue
        meaningful_words.append(w)

    if not meaningful_words:
        return False
    if words[0] in {"what", "who", "where", "when", "why", "how", "which", "will", "would", "should", "could", "can", "is", "are", "do", "does", "did"}:
        return False
    return True

def _extract_candidate_from_text(text: str) -> Optional[str]:
    lower = text.lower().strip(" ?.,!;:()\"'~`")
    if not lower or ai_service.is_greeting(lower):
        return None

    p_prep = [
        r'(?:can you\s+|could you\s+|please\s+|help me\s+|i want to\s+)?(?:locate|show|find|point|view|open|pin|display|where is|navigate to|go to|take me to)\s+(?:me\s+)?(?:the\s+)?(?:location\s+of\s+|weather\s+of\s+|weather\s+in\s+|weather\s+at\s+|map\s+of\s+)?([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]+?)(?:\s+(?:on\s+map|on\s+the\s+map|in\s+map|map|weather|forecast|today|now|\?|\.|$)|$)',
        r'^([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]{2,30}?)\s+(?:map|location|coordinates|coords)$',
        r'(?:map|satellite|view)\s+(?:of\s+)?([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]+?)(?:\s+(?:today|now|\?|\.|$)|$)',
        r'(?:weather|forecast|temperature|temp|climate|rain|humidity|condition)\s+(?:of|in|at|for)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]+?)(?:\s+(?:today|tomorrow|now|on|at|\?|\.|$)|$)',
        r'(?:how is|show me|tell me)\s+(?:the\s+)?(?:weather\s+)?(?:in|of|at|for)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]+?)(?:\s+(?:today|tomorrow|now|\?|\.|$)|$)',
        r'\b(?:in|at|for|of)\s+([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]{2,30}?)(?:\s+(?:weather|forecast|today|tomorrow|now|\?|\.|$)|$)',
        r'^([a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s\-]{2,30}?)\s+(?:weather|forecast|temperature|temp|condition|climate)$'
    ]
    for p in p_prep:
        m = re.search(p, lower)
        if m:
            cand = m.group(1).strip()
            cand = re.sub(r'^(the|a|an|my|this|current)\s+', '', cand).strip()
            if _is_valid_location_candidate(cand):
                return cand

    words = lower.split()
    if 1 <= len(words) <= 3:
        if _is_valid_location_candidate(lower):
            return lower

    return None

async def _resolve_city(city_query: str) -> Optional[tuple[str, float, float]]:
    clean = city_query.lower().strip(" ?.,!;:()\"'~`@#$%^&*-_+=/\\|")
    if not clean or len(clean) < 2 or not _is_valid_location_candidate(clean) or ai_service.is_greeting(clean):
        return None

    # 1. Exact match in KNOWN_GLOBAL_LOCATIONS or INDIAN_CITIES_COORDS
    if clean in KNOWN_GLOBAL_LOCATIONS:
        return KNOWN_GLOBAL_LOCATIONS[clean]
    if clean in INDIAN_CITIES_COORDS:
        d = INDIAN_CITIES_COORDS[clean]
        return d["name"], d["lat"], d["lon"]

    # 2. Normalize repeated consonants (e.g. bardhamman -> bardhaman)
    norm = re.sub(r'([b-df-hj-np-tv-z])\1+', r'\1', clean)
    if norm in KNOWN_GLOBAL_LOCATIONS:
        return KNOWN_GLOBAL_LOCATIONS[norm]
    if norm in INDIAN_CITIES_COORDS:
        d = INDIAN_CITIES_COORDS[norm]
        return d["name"], d["lat"], d["lon"]

    # Protect against short acronyms/airport codes (e.g. 'hii' -> Lake Havasu City, 'lax', 'hel')
    if len(clean) <= 3:
        return None

    # 3. Fuzzy match against dictionary keys
    import difflib
    all_keys = list(KNOWN_GLOBAL_LOCATIONS.keys()) + list(INDIAN_CITIES_COORDS.keys())
    close = difflib.get_close_matches(clean, all_keys, n=1, cutoff=0.75)
    if close:
        match_key = close[0]
        if match_key in KNOWN_GLOBAL_LOCATIONS:
            return KNOWN_GLOBAL_LOCATIONS[match_key]
        if match_key in INDIAN_CITIES_COORDS:
            d = INDIAN_CITIES_COORDS[match_key]
            return d["name"], d["lat"], d["lon"]

    # 4. Dynamic Multi-Tier Geocoding Engine
    try:
        locs = await weather_service.geocode(clean, limit=1)
        if locs:
            l = locs[0]
            label = l.formattedAddress or (f"{l.name}, {l.country}" if l.country else l.name)
            return label, l.latitude, l.longitude
    except Exception:
        pass

    return None

async def _extract_location_from_query(text: str) -> Optional[tuple[str, float, float]]:
    """Intelligent geographic extractor for any city, country, state, or locality."""
    clean = text.lower().strip(" ?.,!;:()\"'~`")
    if not clean or ai_service.is_greeting(clean):
        return None

    # 1. Preposition and intent patterns first (captures specific multi-word localities like 'salt lake sector 5')
    cand = _extract_candidate_from_text(text)
    if cand:
        res = await _resolve_city(cand)
        if res:
            return res

    # 2. Check known locations (longest first)
    for loc_key, data in sorted(KNOWN_GLOBAL_LOCATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if len(loc_key) >= 3 and re.search(rf"\b{re.escape(loc_key)}\b", clean):
            return data

    for city_key, data in sorted(INDIAN_CITIES_COORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if len(city_key) >= 3 and re.search(rf"\b{re.escape(city_key)}\b", clean):
            return data["name"], data["lat"], data["lon"]

    return None


# ----------------------------------------------------
# 1. Weather & Geocoding Endpoints
# ----------------------------------------------------

@app.get("/api/weather/search")
async def search_location(
    q: str = Query(..., min_length=2),
    include_weather: bool = Query(False, description="Whether to attach individual live weather to each match"),
    limit: int = Query(8, description="Maximum matching places to return")
):
    """Search for locations, localities, suburbs, postal codes, and institutions dynamically."""
    results = await weather_service.geocode(q, limit=limit)
    if include_weather and results:
        return await weather_service.get_weather_for_locations(results)
    return results


@app.get("/api/weather/nearby-institutions")
async def get_nearby_institutions(
    category: str = Query(..., description="Institution category e.g. college, school, hospital, bank, police"),
    lat: Optional[float] = Query(None, description="Center latitude"),
    lon: Optional[float] = Query(None, description="Center longitude"),
    location: Optional[str] = Query(None, description="Center location name or postal code"),
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    include_weather: bool = Query(True, description="Attach weather for each institution using its own coordinates"),
    limit: int = Query(8, description="Maximum places to return")
):
    """Dynamically finds nearby institutions and retrieves weather for each using its own coordinates."""
    import math
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        if location:
            res = await _resolve_city(location)
            if res:
                _, lat, lon = res
            else:
                locs = await weather_service.geocode(location, limit=1)
                if locs:
                    lat, lon = locs[0].latitude, locs[0].longitude
        if lat is None or lon is None:
            lat, lon = settings.DEFAULT_LAT, settings.DEFAULT_LON

    places = await weather_service.find_nearby_places(category, lat, lon, radius_km, limit)
    if include_weather and places:
        return await weather_service.get_weather_for_locations(places)
    return places


@app.get("/api/weather/reverse-geocode")
async def reverse_geocode_location(
    lat: float = Query(..., description="GPS Latitude"),
    lon: float = Query(..., description="GPS Longitude")
):
    """Translates GPS latitude and longitude into authentic locality, city, state, country."""
    import math
    if math.isnan(lat) or math.isnan(lon):
        lat, lon = settings.DEFAULT_LAT, settings.DEFAULT_LON
    return await weather_service.reverse_geocode(lat, lon)


@app.get("/api/weather/current", response_model=WeatherCurrent)
async def get_current_weather(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    city: Optional[str] = Query(None)
):
    """Retrieve real-time meteorological parameters and AQI with automatic coordinates resolution."""
    import math
    clean_city = (city or "").strip()
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        if clean_city:
            res = await _resolve_city(clean_city)
            if res:
                resolved_name, lat, lon = res
                city = resolved_name
        if lat is None or lon is None:
            lat, lon = settings.DEFAULT_LAT, settings.DEFAULT_LON
            city = clean_city or settings.DEFAULT_CITY
    elif clean_city and clean_city.lower() not in ("kolkata", "calcutta"):
        # If coordinates match default Kolkata but city is explicitly different
        if abs(lat - settings.DEFAULT_LAT) < 0.001 and abs(lon - settings.DEFAULT_LON) < 0.001:
            res = await _resolve_city(clean_city)
            if res:
                resolved_name, lat, lon = res
                city = resolved_name
    return await weather_service.get_current_weather(lat, lon, city or settings.DEFAULT_CITY)


@app.get("/api/weather/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    city: Optional[str] = Query(None)
):
    """Retrieve 24-hour hourly and 7-day weather forecast with automatic coordinates resolution."""
    import math
    clean_city = (city or "").strip()
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        if clean_city:
            res = await _resolve_city(clean_city)
            if res:
                resolved_name, lat, lon = res
                city = resolved_name
        if lat is None or lon is None:
            lat, lon = settings.DEFAULT_LAT, settings.DEFAULT_LON
            city = clean_city or settings.DEFAULT_CITY
    elif clean_city and clean_city.lower() not in ("kolkata", "calcutta"):
        # If coordinates match default Kolkata but city is explicitly different
        if abs(lat - settings.DEFAULT_LAT) < 0.001 and abs(lon - settings.DEFAULT_LON) < 0.001:
            res = await _resolve_city(clean_city)
            if res:
                resolved_name, lat, lon = res
                city = resolved_name
    return await weather_service.get_forecast(lat, lon, city or settings.DEFAULT_CITY)


# ----------------------------------------------------
# 2. Early Warning & Disaster Alerts Endpoints
# ----------------------------------------------------

@app.get("/api/alerts/active", response_model=List[AlertItem])
async def get_active_alerts(
    region: str = Query("New Delhi"),
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    """Retrieve active IMD disaster alerts and color codes for a region."""
    import math
    if lat is not None and math.isnan(lat):
        lat = None
    if lon is not None and math.isnan(lon):
        lon = None
    weather_curr = None
    if lat is not None and lon is not None:
        try:
            weather_curr = await weather_service.get_current_weather(lat, lon, region)
        except Exception:
            pass
    return alerts_service.get_alerts_for_location(region, weather_curr)


@app.get("/api/alerts/national", response_model=List[AlertItem])
async def get_national_alerts():
    """Retrieve nationwide severe meteorological bulletins."""
    return alerts_service.get_national_alerts_overview()



# ----------------------------------------------------
# 3. Conversational AI & Chat Endpoints
# ----------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Main Conversational AI endpoint:
    Integrates NLP, real-time meteorological data, IMD warnings, and multi-location comparisons.
    Uses real LLM reasoning over structured meteorological context.
    """
    # 1. Manage or create Session
    session_id = req.session_id or str(uuid.uuid4())
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        clean_title = (req.message[:35] + "...") if len(req.message) > 35 else req.message
        session = ChatSession(id=session_id, title=clean_title)
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. Check for greetings, nearby institutions, or matching locations queries
    is_greeting_msg = ai_service.is_greeting(req.message)
    nearby_req = None if is_greeting_msg else _detect_nearby_institutions_query(req.message)
    matching_req = None if is_greeting_msg else _detect_matching_locations_query(req.message)
    comp = None if is_greeting_msg else _detect_comparison_query(req.message)

    comparison_data = None
    matching_locations = None
    extra_context = None
    current_weather = None
    hourly_forecast = None
    daily_forecast = None
    active_alerts = None

    if nearby_req:
        cat, target = nearby_req
        ref_lat = req.latitude
        ref_lon = req.longitude
        ref_name = req.location or "Current Location"

        if target and target != "me":
            res = await _resolve_city(target)
            if res:
                ref_name, ref_lat, ref_lon = res
            else:
                locs = await weather_service.geocode(target, limit=1)
                if locs:
                    ref_lat, ref_lon = locs[0].latitude, locs[0].longitude
                    ref_name = locs[0].formattedAddress or locs[0].name

        if ref_lat is None or ref_lon is None:
            ref_lat = settings.DEFAULT_LAT
            ref_lon = settings.DEFAULT_LON
            ref_name = settings.DEFAULT_CITY

        # Base forecast for reference center
        try:
            fc = await weather_service.get_forecast(ref_lat, ref_lon, ref_name)
            current_weather = fc.current
            hourly_forecast = fc.hourly_24h
            daily_forecast = fc.daily_7d
            active_alerts = alerts_service.get_alerts_for_location(ref_name, current_weather)
        except Exception as e:
            logger.warning(f"Error getting base forecast for nearby query: {e}")

        # Find nearby places and fetch their individual live weather
        try:
            places = await weather_service.find_nearby_places(cat, ref_lat, ref_lon, radius_km=15.0, limit=8)
            if places:
                matching_locations = await weather_service.get_weather_for_locations(places)
                lines = [f"NEARBY {cat.upper()} INSTITUTIONS FOUND NEAR {ref_name} WITH LIVE METEOROLOGICAL TELEMETRY:"]
                for p in matching_locations:
                    w = p.get("weather") or {}
                    w_desc = w.get("weather_desc", "Clear")
                    w_temp = w.get("temperature", "--")
                    w_fl = w.get("feels_like", "--")
                    w_hum = w.get("humidity", "--")
                    w_wind = w.get("wind_speed", "--")
                    p_name = p.get("name", "Institution")
                    p_loc = p.get("formattedAddress") or f"{p.get('city') or ''}, {p.get('state') or ''}".strip(", ")
                    p_coords = f"Lat: {p.get('latitude', 0):.4f}, Lon: {p.get('longitude', 0):.4f}"
                    lines.append(f"- {p_name} ({p_loc}, {p_coords}): {w_temp}°C ({w_desc}, Feels like: {w_fl}°C, Humidity: {w_hum}%, Wind: {w_wind} km/h)")
                extra_context = "\n".join(lines)
        except Exception as e:
            logger.warning(f"Error getting nearby places weather: {e}")

    elif matching_req:
        query_str = matching_req
        try:
            places = await weather_service.geocode(query_str, limit=8)
            if places:
                matching_locations = await weather_service.get_weather_for_locations(places)
                first_loc = matching_locations[0]
                first_lat = first_loc["latitude"]
                first_lon = first_loc["longitude"]
                first_name = first_loc.get("formattedAddress") or first_loc.get("name")

                fc = await weather_service.get_forecast(first_lat, first_lon, first_name)
                current_weather = fc.current
                hourly_forecast = fc.hourly_24h
                daily_forecast = fc.daily_7d
                active_alerts = alerts_service.get_alerts_for_location(first_name, current_weather)

                lines = [f"MATCHING LOCATIONS FOR '{query_str}' (ALL RESULTS WITH LIVE METEOROLOGICAL TELEMETRY):"]
                for p in matching_locations:
                    w = p.get("weather") or {}
                    w_desc = w.get("weather_desc", "Clear")
                    w_temp = w.get("temperature", "--")
                    w_fl = w.get("feels_like", "--")
                    w_hum = w.get("humidity", "--")
                    w_wind = w.get("wind_speed", "--")
                    p_name = p.get("name", "Location")
                    p_loc = p.get("formattedAddress") or f"{p.get('city') or ''}, {p.get('state') or ''}".strip(", ")
                    p_coords = f"Lat: {p.get('latitude', 0):.4f}, Lon: {p.get('longitude', 0):.4f}"
                    lines.append(f"- {p_name} ({p_loc}, {p_coords}): {w_temp}°C ({w_desc}, Feels like: {w_fl}°C, Humidity: {w_hum}%, Wind: {w_wind} km/h)")
                extra_context = "\n".join(lines)
        except Exception as e:
            logger.warning(f"Error geocoding matching locations: {e}")

    elif comp:
        c1_str, c2_str = comp
        r1, r2 = await asyncio.gather(_resolve_city(c1_str), _resolve_city(c2_str))
        if r1 and r2:
            try:
                fc1, fc2 = await asyncio.gather(
                    weather_service.get_forecast(r1[1], r1[2], r1[0]),
                    weather_service.get_forecast(r2[1], r2[2], r2[0])
                )
                city_name, lat, lon = r1[0], r1[1], r1[2]
                current_weather = fc1.current
                hourly_forecast = fc1.hourly_24h
                daily_forecast = fc1.daily_7d
                active_alerts = alerts_service.get_alerts_for_location(city_name, current_weather)
                comparison_data = {
                    "city": r2[0],
                    "weather": fc2.current,
                    "daily_7d": fc2.daily_7d
                }
            except Exception as e:
                logger.warning(f"Comparison data retrieval error: {e}")

    # 3. If neither matching/nearby nor comparison, determine target location
    if not comparison_data and not matching_locations:
        lat = req.latitude
        lon = req.longitude
        city_name = req.location

        if is_greeting_msg:
            # Greetings ALWAYS retain active or default location (e.g. Kolkata)
            if lat is None or lon is None:
                lat = settings.DEFAULT_LAT
                lon = settings.DEFAULT_LON
            if not city_name or city_name.lower().strip() in ("current location", "my location", "here", "weather here", "near me"):
                city_name = settings.DEFAULT_CITY
            extracted = None
        else:
            # If city is explicitly mentioned in message, prioritize that city
            extracted = await _extract_location_from_query(req.message)
            if extracted:
                city_name, lat, lon = extracted
            elif lat is not None and lon is not None:
                # If city name is missing, placeholder, or coordinate string, reverse-geocode to authentic city
                if not city_name or city_name.lower().strip() in ("current location", "my location", "here", "weather here", "near me") or "coords (" in city_name.lower() or "location (" in city_name.lower():
                    try:
                        rg = await weather_service.reverse_geocode(lat, lon)
                        city_name = rg.get("city") or rg.get("locality") or rg.get("state") or rg.get("country") or "Selected Region"
                    except Exception:
                        city_name = "Selected Region"

            # Check if session has a recent location context if no explicit location was provided and it's a follow-up
            if not extracted and not is_greeting_msg and (lat is None or lon is None or (abs(lat - settings.DEFAULT_LAT) < 0.001 and abs(lon - settings.DEFAULT_LON) < 0.001 and (not city_name or city_name.lower().strip() in ("kolkata", "kolkata, west bengal, india")))):
                last_with_weather = (
                    db.query(ChatMessage)
                    .filter(ChatMessage.session_id == session_id, ChatMessage.weather_snapshot.isnot(None))
                    .order_by(ChatMessage.created_at.desc())
                    .first()
                )
                if last_with_weather and last_with_weather.weather_snapshot:
                    try:
                        snap = json.loads(last_with_weather.weather_snapshot)
                        # Only reuse if valid coordinates and NOT an anomalous or foreign location if user asked a simple follow-up
                        if snap.get("latitude") and snap.get("longitude"):
                            lat = float(snap["latitude"])
                            lon = float(snap["longitude"])
                            city_name = snap.get("city", city_name)
                    except Exception:
                        pass

        # Fallback to default only if coordinates are completely absent
        if lat is None or lon is None:
            lat = settings.DEFAULT_LAT
            lon = settings.DEFAULT_LON
            city_name = city_name or settings.DEFAULT_CITY
        elif not city_name or "location (" in city_name.lower() or "coords (" in city_name.lower():
            city_name = "Selected Region"

        # Fetch real-time weather & forecast
        try:
            forecast_res = await weather_service.get_forecast(lat, lon, city_name)
            current_weather = forecast_res.current
            hourly_forecast = forecast_res.hourly_24h
            daily_forecast = forecast_res.daily_7d
        except Exception as e:
            logger.error(f"Error getting weather for chat: {e}")
            current_weather = None
            hourly_forecast = None
            daily_forecast = None

        # Fetch active disaster alerts
        try:
            active_alerts = alerts_service.get_alerts_for_location(city_name, current_weather)
        except Exception as e:
            logger.error(f"Error getting alerts for chat: {e}")
            active_alerts = None

    # 4. Fetch past session history for conversational context
    past_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history_dicts = [{"role": m.role, "content": m.content} for m in past_messages]

    # 5. Check if query asks for a specific date in the 7-day forecast to provide UI preview
    target_day_matched = None
    if daily_forecast and len(daily_forecast) > 0:
        forecast_dates = [d.date for d in daily_forecast if d.date]
        target_date_str = parse_target_date(req.message, forecast_dates)
        if target_date_str:
            target_day_matched = next((d for d in daily_forecast if d.date == target_date_str), None)

    # 6. Call AI Service - 100% LLM dynamic reasoning over real meteorological telemetry!
    reply_text, suggested_queries = await ai_service.chat(
        message=req.message,
        weather=current_weather,
        hourly=hourly_forecast,
        forecast=daily_forecast,
        alerts=active_alerts,
        comparison_data=comparison_data,
        chat_history=history_dicts,
        language=req.language or "en",
        extra_context=extra_context
    )

    # 7. Persist messages to SQLite
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=req.message
    )

    weather_snap_str = None
    if current_weather:
        snap_dict = current_weather.model_dump()
        if matching_locations:
            snap_dict["matching_locations"] = matching_locations
        weather_snap_str = json.dumps(snap_dict)
    elif matching_locations:
        weather_snap_str = json.dumps({"matching_locations": matching_locations})

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=reply_text,
        weather_snapshot=weather_snap_str,
        alert_snapshot=json.dumps([a.model_dump() for a in active_alerts]) if active_alerts else None
    )
    session.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        session_id=session_id,
        reply=reply_text,
        language=req.language or "en",
        weather=current_weather,
        forecast_preview=[target_day_matched] if target_day_matched else (daily_forecast[:4] if daily_forecast else None),
        alerts=active_alerts,
        suggested_queries=suggested_queries,
        matching_locations=matching_locations
    )


@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text_endpoint(req: TranslateRequest, db: Session = Depends(get_db)):
    """
    Translates meteorological consultation text into English ('en'), Hindi ('hi'), or Bangla ('bn')
    in under 2-3 seconds using AI / fast meteorological domain translation.
    """
    translated = await ai_service.translate_text(req.text, req.target_language)
    
    # If session_id provided, optionally update the last assistant message in SQLite
    if req.session_id:
        try:
            last_msg = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == req.session_id, ChatMessage.role == "assistant")
                .order_by(ChatMessage.created_at.desc())
                .first()
            )
            if last_msg:
                last_msg.content = translated
                db.commit()
        except Exception as e:
            logger.warning(f"Could not persist translated message: {e}")

    return TranslateResponse(
        translated_text=translated,
        target_language=req.target_language,
        session_id=req.session_id
    )


IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

@app.get("/api/time")
def get_current_time():
    """Returns current real-time timestamp in IST and UTC."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc.astimezone(IST)
    return {
        "epoch": int(now_utc.timestamp()),
        "utc_iso": now_utc.isoformat(),
        "ist_iso": now_ist.isoformat(),
        "ist_time": now_ist.strftime("%I:%M %p"),
        "date_display": now_ist.strftime("%d %b %Y"),
        "timezone": "Asia/Kolkata (IST +05:30)"
    }


@app.get("/api/chat/sessions", response_model=List[SessionSummary])
@app.get("/api/conversations", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_db)):
    """Lists saved conversation sessions with accurate IST timestamps."""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    results = []
    for s in sessions:
        msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).count()
        dt = s.updated_at or s.created_at
        if dt is None:
            dt = datetime.datetime.now(datetime.timezone.utc)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        ist_dt = dt.astimezone(IST)

        results.append(
            SessionSummary(
                id=s.id,
                title=s.title,
                created_at=ist_dt.isoformat(),
                updated_at=ist_dt.isoformat(),
                time_display=ist_dt.strftime("%I:%M %p"),
                message_count=msg_count
            )
        )
    return results


@app.get("/api/chat/sessions/{session_id}", response_model=List[ChatMessageSchema])
@app.get("/api/conversations/{session_id}", response_model=List[ChatMessageSchema])
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Loads all messages for a specific session with accurate IST timestamps."""
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    res = []
    for m in msgs:
        w_data = json.loads(m.weather_snapshot) if m.weather_snapshot else None
        a_data = json.loads(m.alert_snapshot) if m.alert_snapshot else None
        matching_locs = None
        if w_data and isinstance(w_data, dict) and "matching_locations" in w_data:
            matching_locs = w_data.pop("matching_locations")

        dt = m.created_at
        if dt is None:
            dt = datetime.datetime.now(datetime.timezone.utc)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        ist_dt = dt.astimezone(IST)

        res.append(
            ChatMessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                weather_data=w_data,
                alert_data=a_data,
                matching_locations=matching_locs,
                created_at=ist_dt.isoformat(),
                time_display=ist_dt.strftime("%I:%M %p")
            )
        )
    return res


@app.delete("/api/conversations")
@app.delete("/api/chat/sessions")
def clear_all_conversations(db: Session = Depends(get_db)):
    """Deletes all chat sessions and messages for Clear All functionality."""
    db.query(ChatMessage).delete()
    db.query(ChatSession).delete()
    db.commit()
    return {"status": "success", "message": "All chat history cleared"}


@app.delete("/api/chat/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Deletes a chat session and associated messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "success", "message": "Session deleted"}


@app.get("/api/locations/saved")
def get_saved_locations(db: Session = Depends(get_db)):
    """Returns bookmarked meteorological locations."""
    return db.query(SavedLocation).all()


@app.get("/api/supabase/config")
def get_supabase_config():
    """Returns safe Supabase project URL and public publishable key for client-side integration."""
    return {
        "supabase_url": settings.SUPABASE_URL,
        "supabase_publishable_key": settings.SUPABASE_PUBLISHABLE_KEY,
        "configured": bool(settings.SUPABASE_URL and settings.SUPABASE_PUBLISHABLE_KEY)
    }


@app.get("/api/settings")
def get_settings():
    """Returns status of external AI and Weather API configurations."""
    return {
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
        "weather_api_configured": bool(settings.WEATHER_API_KEY),
        "default_city": settings.DEFAULT_CITY,
        "default_lat": settings.DEFAULT_LAT,
        "default_lon": settings.DEFAULT_LON,
    }


@app.post("/api/settings")
async def update_settings(payload: dict):
    """Updates runtime configuration keys."""
    if "openai_api_key" in payload and payload["openai_api_key"] is not None:
        val = str(payload["openai_api_key"]).strip()
        settings.OPENAI_API_KEY = val
    if "openai_model" in payload and payload["openai_model"] is not None:
        settings.OPENAI_MODEL = str(payload["openai_model"]).strip()
    if "gemini_api_key" in payload and payload["gemini_api_key"] is not None:
        settings.GEMINI_API_KEY = str(payload["gemini_api_key"]).strip()
    if "gemini_model" in payload and payload["gemini_model"] is not None:
        settings.GEMINI_MODEL = str(payload["gemini_model"]).strip()
    if "weather_api_key" in payload and payload["weather_api_key"] is not None:
        settings.WEATHER_API_KEY = str(payload["weather_api_key"]).strip()
    return {
        "status": "success",
        "message": "Settings updated successfully",
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
        "weather_api_configured": bool(settings.WEATHER_API_KEY),
    }


# ----------------------------------------------------
# 4. Static Frontend Mount & Root Index
# ----------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/index.html")
    async def serve_index_html():
        return FileResponse(FRONTEND_DIR / "index.html")

