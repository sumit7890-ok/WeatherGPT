import os
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file from project root or backend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = "WeatherGPT - MoES/IMD Intelligent Meteorological Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # SQLite Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'weathergpt.db'}")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

    # AI Engine Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    
    # Meteorological APIs
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_URL: str = "https://api.weatherapi.com/v1"
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", os.getenv("OPENWEATHER_API_KEY", ""))
    OPENWEATHERMAP_URL: str = "https://api.openweathermap.org/data/2.5"
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    
    # Default Coordinates (Kolkata, West Bengal, India per user request)
    DEFAULT_CITY: str = "Kolkata, West Bengal, India"
    DEFAULT_LAT: float = 22.5726
    DEFAULT_LON: float = 88.3639
    
    # IMD Warning Color Codes
    ALERT_COLORS: dict = {
        "GREEN": {"name": "No Warning (Normal)", "hex": "#10B981", "level": 1},
        "YELLOW": {"name": "Watch (Be Updated)", "hex": "#F59E0B", "level": 2},
        "ORANGE": {"name": "Alert (Be Prepared)", "hex": "#F97316", "level": 3},
        "RED": {"name": "Warning (Take Action)", "hex": "#EF4444", "level": 4}
    }

settings = Settings()
