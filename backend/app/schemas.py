from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime

class WeatherCurrent(BaseModel):
    city: str
    latitude: float
    longitude: float
    timezone: str
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    wind_direction: int
    wind_gust: Optional[float] = None
    pressure: float
    precipitation: float
    cloud_cover: int
    weather_code: int
    weather_desc: str
    weather_icon: str
    uv_index: Optional[float] = None
    aqi: Optional[int] = None
    aqi_desc: Optional[str] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    timestamp: str

class HourlyPoint(BaseModel):
    time: str
    temperature: float
    precipitation_prob: int
    precipitation: float
    weather_code: int
    weather_desc: str
    wind_speed: float
    weather_icon: Optional[str] = None

class DailyForecast(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    precipitation_sum: float
    precipitation_prob: int
    weather_code: int
    weather_desc: str
    weather_icon: str
    uv_index_max: Optional[float] = None

class WeatherForecastResponse(BaseModel):
    current: WeatherCurrent
    hourly_24h: List[HourlyPoint]
    daily_7d: List[DailyForecast]

class AlertItem(BaseModel):
    alert_id: str
    region: str
    state: Optional[str] = None
    hazard_type: str
    severity: str  # GREEN, YELLOW, ORANGE, RED
    severity_level: int  # 1 to 4
    severity_color: str
    severity_title: str
    headline: str
    description: str
    advisory: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None

class LocationSearchItem(BaseModel):
    id: Optional[int] = 0
    name: str
    formattedAddress: Optional[str] = None
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    country: str = "India"
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    locality: Optional[str] = None
    sublocality: Optional[str] = None
    neighborhood: Optional[str] = None
    postalCode: Optional[str] = None
    placeId: Optional[str] = None
    admin1: Optional[str] = None  # State / Province alias
    admin2: Optional[str] = None  # District alias

class ChatMessageSchema(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    weather_data: Optional[Dict[str, Any]] = None
    alert_data: Optional[Any] = None
    matching_locations: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[Any] = None
    time_display: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    language: Optional[str] = "en"  # "en", "hi", or "bn"
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: str
    weather: Optional[WeatherCurrent] = None
    forecast_preview: Optional[List[DailyForecast]] = None
    alerts: Optional[List[AlertItem]] = None
    suggested_queries: List[str] = []
    matching_locations: Optional[List[Dict[str, Any]]] = None

class TranslateRequest(BaseModel):
    text: str
    target_language: str  # "en", "hi", or "bn"
    session_id: Optional[str] = None

class TranslateResponse(BaseModel):
    translated_text: str
    target_language: str
    session_id: Optional[str] = None

class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    time_display: Optional[str] = None
    message_count: int
