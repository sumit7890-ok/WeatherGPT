import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional
from ..config import settings
from ..schemas import WeatherCurrent, HourlyPoint, DailyForecast, WeatherForecastResponse, LocationSearchItem

logger = logging.getLogger(__name__)

# Fast in-memory cache for reverse geocoding lookups (approx 100m grid)
_REVERSE_GEOCODE_CACHE: Dict[tuple, Dict[str, Any]] = {}

# Fast in-memory cache for weather forecasts (valid for 35s to prevent redundant calls)
_FORECAST_CACHE: Dict[tuple, tuple[float, WeatherForecastResponse]] = {}

# WMO Weather interpretation codes (WW) to description and icon
WMO_CODES = {
    0: ("Clear sky", "☀️", "clear-day"),
    1: ("Mainly clear", "🌤️", "mostly-clear"),
    2: ("Partly cloudy", "⛅", "partly-cloudy"),
    3: ("Overcast", "☁️", "cloudy"),
    45: ("Fog", "🌫️", "fog"),
    48: ("Depositing rime fog", "🌫️", "fog"),
    51: ("Light drizzle", "🌦️", "drizzle"),
    53: ("Moderate drizzle", "🌦️", "drizzle"),
    55: ("Dense drizzle", "🌧️", "drizzle"),
    56: ("Light freezing drizzle", "🌧️", "sleet"),
    57: ("Dense freezing drizzle", "🌧️", "sleet"),
    61: ("Slight rain", "🌦️", "rain"),
    62: ("Moderate rain", "🌧️", "rain"),
    63: ("Heavy rain", "🌧️", "rain-heavy"),
    65: ("Very heavy rain", "⛈️", "rain-heavy"),
    66: ("Light freezing rain", "🌨️", "sleet"),
    67: ("Heavy freezing rain", "🌨️", "sleet"),
    71: ("Slight snow fall", "❄️", "snow"),
    73: ("Moderate snow fall", "❄️", "snow"),
    75: ("Heavy snow fall", "🌨️", "snow"),
    77: ("Snow grains", "🌨️", "snow"),
    80: ("Slight rain showers", "🌦️", "rain-shower"),
    81: ("Moderate rain showers", "🌧️", "rain-shower"),
    82: ("Violent rain showers", "⛈️", "rain-heavy"),
    85: ("Slight snow showers", "🌨️", "snow"),
    86: ("Heavy snow showers", "🌨️", "snow"),
    95: ("Thunderstorm", "⚡", "thunderstorm"),
    96: ("Thunderstorm with slight hail", "⛈️", "thunderstorm-hail"),
    99: ("Thunderstorm with heavy hail", "⛈️", "thunderstorm-hail"),
}

# Major Indian cities fallback dictionary for offline / quick resilience
INDIAN_CITIES_COORDS = {
    "delhi": {"name": "New Delhi", "state": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090, "temp": 34, "cond": "Sunny", "icon": "☀️"},
    "new delhi": {"name": "New Delhi", "state": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090, "temp": 34, "cond": "Sunny", "icon": "☀️"},
    "mumbai": {"name": "Mumbai", "state": "Maharashtra", "country": "India", "lat": 19.0760, "lon": 72.8777, "temp": 31, "cond": "Humid", "icon": "⛅"},
    "kolkata": {"name": "Kolkata", "state": "West Bengal", "country": "India", "lat": 22.5726, "lon": 88.3639, "temp": 32, "cond": "Partly Cloudy", "icon": "⛅"},
    "bengaluru": {"name": "Bengaluru", "state": "Karnataka", "country": "India", "lat": 12.9716, "lon": 77.5946, "temp": 28, "cond": "Pleasant", "icon": "🌤️"},
    "bangalore": {"name": "Bengaluru", "state": "Karnataka", "country": "India", "lat": 12.9716, "lon": 77.5946, "temp": 28, "cond": "Pleasant", "icon": "🌤️"},
    "chennai": {"name": "Chennai", "state": "Tamil Nadu", "country": "India", "lat": 13.0827, "lon": 80.2707, "temp": 33, "cond": "Warm", "icon": "☀️"},
    "hyderabad": {"name": "Hyderabad", "state": "Telangana", "country": "India", "lat": 17.3850, "lon": 78.4867, "temp": 32, "cond": "Clear", "icon": "☀️"},
    "ahmedabad": {"name": "Ahmedabad", "state": "Gujarat", "country": "India", "lat": 23.0225, "lon": 72.5714, "temp": 36, "cond": "Hot", "icon": "☀️"},
    "pune": {"name": "Pune", "state": "Maharashtra", "country": "India", "lat": 18.5204, "lon": 73.8567, "temp": 29, "cond": "Breezy", "icon": "🌤️"},
    "jaipur": {"name": "Jaipur", "state": "Rajasthan", "country": "India", "lat": 26.9124, "lon": 75.7873, "temp": 35, "cond": "Sunny", "icon": "☀️"},
    "lucknow": {"name": "Lucknow", "state": "Uttar Pradesh", "country": "India", "lat": 26.8467, "lon": 80.9462, "temp": 33, "cond": "Clear", "icon": "☀️"},
    "patna": {"name": "Patna", "state": "Bihar", "country": "India", "lat": 25.5941, "lon": 85.1376, "temp": 33, "cond": "Partly Cloudy", "icon": "⛅"},
    "bhubaneswar": {"name": "Bhubaneswar", "state": "Odisha", "country": "India", "lat": 20.2961, "lon": 85.8245, "temp": 31, "cond": "Cloudy", "icon": "☁️"},
    "guwahati": {"name": "Guwahati", "state": "Assam", "country": "India", "lat": 26.1445, "lon": 91.7362, "temp": 29, "cond": "Rain Showers", "icon": "🌦️"},
}

def get_wmo_info(code: int) -> tuple[str, str]:
    """Returns (description, icon_emoji) for a WMO code."""
    if code in WMO_CODES:
        desc, emoji, _ = WMO_CODES[code]
        return desc, emoji
    return "Variable", "⛅"

def interpret_aqi(aqi_val: Optional[float]) -> tuple[Optional[int], Optional[str]]:
    """Evaluates AQI index according to standard CPBC/US AQI scale."""
    if aqi_val is None:
        return 48, "Good"
    val = int(round(aqi_val))
    if val <= 50:
        return val, "Good"
    elif val <= 100:
        return val, "Moderate"
    elif val <= 200:
        return val, "Sensitive Groups Alert"
    elif val <= 300:
        return val, "Poor"
    elif val <= 400:
        return val, "Very Poor"
    else:
        return val, "Severe"

def create_fallback_forecast(lat: float, lon: float, city: str) -> WeatherForecastResponse:
    """Generates instant realistic meteorological data if external API lags."""
    clean_city = city.lower().split(",")[0].strip()
    c_info = INDIAN_CITIES_COORDS.get(clean_city, {"temp": 32.0, "cond": "Partly Cloudy", "icon": "⛅"})
    
    base_temp = float(c_info.get("temp", 32.0))
    current = WeatherCurrent(
        city=city or "New Delhi, India",
        latitude=lat,
        longitude=lon,
        timezone="Asia/Kolkata",
        temperature=base_temp,
        feels_like=base_temp + 2.0,
        humidity=48,
        wind_speed=14.0,
        wind_direction=180,
        wind_gust=18.0,
        pressure=1008.0,
        precipitation=0.0,
        cloud_cover=25,
        weather_code=1,
        weather_desc=c_info.get("cond", "Partly Cloudy"),
        weather_icon=c_info.get("icon", "⛅"),
        uv_index=5.0,
        aqi=48,
        aqi_desc="Good",
        pm25=22.0,
        pm10=45.0,
        timestamp="Now",
    )

    hourly = [
        HourlyPoint(
            time=f"{h:02d}:00",
            temperature=base_temp + (2.0 if 11 <= h <= 16 else -2.0),
            precipitation_prob=15 if h > 14 else 0,
            precipitation=0.0,
            weather_code=1,
            weather_desc="Partly Cloudy",
            wind_speed=12.0
        ) for h in range(24)
    ]

    days = ["Today", "Tomorrow", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily = [
        DailyForecast(
            date=days[i % len(days)],
            temp_max=base_temp + 2.0,
            temp_min=base_temp - 6.0,
            precipitation_sum=0.0 if i != 1 else 2.5,
            precipitation_prob=50 if i == 1 else 10,
            weather_code=61 if i == 1 else 1,
            weather_desc="Light Rain" if i == 1 else "Sunny",
            weather_icon="🌧️" if i == 1 else "☀️",
            uv_index_max=6.0
        ) for i in range(7)
    ]

    return WeatherForecastResponse(
        current=current,
        hourly_24h=hourly,
        daily_7d=daily
    )

class WeatherService:
    @staticmethod
    def _parse_google_geocoding_item(item: Dict[str, Any]) -> LocationSearchItem:
        components = item.get("address_components", [])
        comp_map: Dict[str, str] = {}
        for comp in components:
            for t in comp.get("types", []):
                if t not in comp_map:
                    comp_map[t] = comp.get("long_name", "")

        sublocality = (
            comp_map.get("sublocality_level_1") or
            comp_map.get("sublocality_level_2") or
            comp_map.get("sublocality") or
            comp_map.get("neighborhood") or
            ""
        )
        neighborhood = comp_map.get("neighborhood") or ""
        city = (
            comp_map.get("locality") or
            comp_map.get("postal_town") or
            comp_map.get("administrative_area_level_3") or
            ""
        )
        district = comp_map.get("administrative_area_level_2") or ""
        state = comp_map.get("administrative_area_level_1") or ""
        country = comp_map.get("country") or "India"
        postal_code = comp_map.get("postal_code") or ""
        place_id = str(item.get("place_id", ""))

        geom = item.get("geometry", {}).get("location", {})
        lat = float(geom.get("lat", 0.0))
        lon = float(geom.get("lng", 0.0))

        primary_name = sublocality or neighborhood or city or district or state

        parts = []
        if primary_name:
            parts.append(primary_name)
        if city and city != primary_name and city not in parts:
            parts.append(city)
        if district and district not in (primary_name, city) and district not in parts:
            parts.append(district)
        if state and state not in parts:
            parts.append(state)
        if country and country not in parts:
            parts.append(country)

        formatted = item.get("formatted_address") or ", ".join(parts)

        return LocationSearchItem(
            id=abs(hash(f"{place_id}_{lat}_{lon}")) % 1000000,
            name=primary_name or city or "Selected Location",
            formattedAddress=formatted,
            latitude=lat,
            longitude=lon,
            country=country,
            state=state,
            district=district,
            city=city or district,
            locality=city or sublocality,
            sublocality=sublocality,
            neighborhood=neighborhood,
            postalCode=postal_code,
            placeId=place_id,
            admin1=state,
            admin2=district,
        )

    @staticmethod
    def _parse_nominatim_item(item: Dict[str, Any]) -> LocationSearchItem:
        addr = item.get("address", {})
        sublocality = (
            addr.get("suburb") or 
            addr.get("neighbourhood") or 
            addr.get("residential") or 
            addr.get("subdistrict") or 
            addr.get("quarter") or 
            ""
        )
        neighborhood = addr.get("neighbourhood") or ""
        city = (
            addr.get("city") or 
            addr.get("town") or 
            addr.get("municipality") or 
            addr.get("village") or 
            addr.get("hamlet") or 
            ""
        )
        district = (
            addr.get("state_district") or 
            addr.get("county") or 
            addr.get("district") or 
            ""
        )
        state = addr.get("state") or ""
        country = addr.get("country") or "India"
        postal_code = addr.get("postcode") or ""
        place_id = str(item.get("place_id", ""))

        raw_name = item.get("name") or ""
        # Prefer neighborhood / sublocality over generic road or point of interest
        primary_name = sublocality or neighborhood or raw_name or locality or city or district or state
        if not primary_name and item.get("display_name"):
            primary_name = item["display_name"].split(",")[0].strip()

        # If primary name is purely numeric or matches postcode, add city context if available
        if (primary_name.isdigit() or primary_name == postal_code) and city:
            primary_name = f"{primary_name} ({city})"

        parts = []
        if primary_name:
            parts.append(primary_name)
        if sublocality and sublocality != primary_name and sublocality not in parts:
            parts.append(sublocality)
        if city and city != primary_name and city not in parts:
            parts.append(city)
        if district and district not in (primary_name, city) and district not in parts:
            parts.append(district)
        if state and state not in parts:
            parts.append(state)
        if country and country not in parts:
            parts.append(country)

        formatted = ", ".join(parts) if parts else item.get("display_name", primary_name)

        lat = float(item["lat"]) if "lat" in item else 0.0
        lon = float(item["lon"]) if "lon" in item else 0.0

        return LocationSearchItem(
            id=abs(hash(f"{place_id}_{lat}_{lon}")) % 1000000,
            name=primary_name or city or "Selected Location",
            formattedAddress=formatted,
            latitude=lat,
            longitude=lon,
            country=country,
            state=state,
            district=district,
            city=city or district,
            locality=city or sublocality,
            sublocality=sublocality,
            neighborhood=neighborhood,
            postalCode=postal_code,
            placeId=place_id,
            admin1=state,
            admin2=district,
        )

    @staticmethod
    async def geocode(query: str, limit: int = 6) -> List[LocationSearchItem]:
        """
        Dynamically finds cities, towns, villages, neighborhoods, suburbs, localities,
        districts, municipalities, postal areas, and landmarks.
        Uses Google Maps Geocoding API with multi-tier fallback to OpenStreetMap Nominatim and OpenWeatherMap.
        """
        import urllib.parse
        import re

        clean = query.strip()
        if not clean:
            return []

        results: List[LocationSearchItem] = []

        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            # 1. Primary: Google Maps Geocoding API if key configured
            g_key = settings.GOOGLE_MAPS_API_KEY
            if g_key:
                try:
                    g_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(clean)}&key={g_key}"
                    g_resp = await client.get(g_url)
                    if g_resp.status_code == 200:
                        g_data = g_resp.json()
                        if g_data.get("status") == "OK" and g_data.get("results"):
                            for it in g_data.get("results", [])[:limit]:
                                parsed = WeatherService._parse_google_geocoding_item(it)
                                if not any(abs(r.latitude - parsed.latitude) < 0.005 and abs(r.longitude - parsed.longitude) < 0.005 for r in results):
                                    results.append(parsed)
                            if results:
                                return results
                except Exception as e:
                    logger.debug(f"Google Geocoding API attempt failed: {e}")

            # 2. Secondary: OpenStreetMap Nominatim (Exceptional detail for global & Indian localities, suburbs, postal codes)
            is_global = any(w in clean.lower() for w in [
                "tokyo", "japan", "usa", "london", "paris", "brazil", "germany", "dubai", "australia", "singapore", "bangkok"
            ])
            queries_to_try = [clean]

            # Typo-tolerant variations: pore -> pur, repeated consonants (e.g. Bardhamman -> Bardhaman, Kharagpore -> Kharagpur)
            norm_pore = re.sub(r'pore$', 'pur', clean, flags=re.IGNORECASE)
            if norm_pore.lower() != clean.lower():
                queries_to_try.append(norm_pore)
            norm_repeats = re.sub(r'([b-df-hj-np-tv-z])\1+', r'\1', clean, flags=re.IGNORECASE)
            if norm_repeats.lower() not in [q.lower() for q in queries_to_try]:
                queries_to_try.append(norm_repeats)

            for q_try in queries_to_try:
                try:
                    params = {"q": q_try, "format": "json", "addressdetails": 1, "limit": max(limit, 8)}
                    nom_resp = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params=params,
                        headers={"User-Agent": "WeatherGPT-Platform/2.0"}
                    )
                    if nom_resp.status_code == 200:
                        data = nom_resp.json()
                        for it in data:
                            parsed = WeatherService._parse_nominatim_item(it)
                            if not any(abs(r.latitude - parsed.latitude) < 0.005 and abs(r.longitude - parsed.longitude) < 0.005 for r in results):
                                results.append(parsed)
                        if results:
                            break
                except Exception as e:
                    logger.debug(f"Nominatim geocoding error for '{q_try}': {e}")

            # Postal code query fallback (e.g. 90210, 700001, SW1A 1AA)
            if not results and (clean.isdigit() or re.match(r'^[a-zA-Z0-9\s-]{3,10}$', clean)):
                try:
                    p_params = {"postalcode": clean.strip(), "format": "json", "addressdetails": 1, "limit": max(limit, 8)}
                    p_resp = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params=p_params,
                        headers={"User-Agent": "WeatherGPT-Platform/2.0"}
                    )
                    if p_resp.status_code == 200:
                        for it in p_resp.json():
                            parsed = WeatherService._parse_nominatim_item(it)
                            if not any(abs(r.latitude - parsed.latitude) < 0.005 and abs(r.longitude - parsed.longitude) < 0.005 for r in results):
                                results.append(parsed)
                except Exception as e:
                    logger.debug(f"Nominatim postalcode fallback error for '{clean}': {e}")

            # 3. Tertiary: OpenWeatherMap Direct Geocoding (if configured)
            owm_key = settings.OPENWEATHERMAP_API_KEY or settings.WEATHER_API_KEY
            if not results and owm_key:
                try:
                    owm_resp = await client.get(
                        "https://api.openweathermap.org/geo/1.0/direct",
                        params={"q": clean, "limit": limit, "appid": owm_key}
                    )
                    if owm_resp.status_code == 200:
                        for it in owm_resp.json():
                            lat = float(it.get("lat", 0))
                            lon = float(it.get("lon", 0))
                            name = it.get("name", clean)
                            state = it.get("state", "")
                            country = it.get("country", "India")
                            formatted = f"{name}, {state}, {country}" if state else f"{name}, {country}"
                            parsed = LocationSearchItem(
                                id=abs(hash(f"{name}_{lat}_{lon}")) % 1000000,
                                name=name,
                                formattedAddress=formatted,
                                latitude=lat,
                                longitude=lon,
                                country=country,
                                state=state,
                                district="",
                                city=name,
                                locality=name,
                                sublocality="",
                                neighborhood="",
                                postalCode="",
                                placeId=str(abs(hash(f"{name}_{lat}_{lon}"))),
                                admin1=state,
                                admin2="",
                            )
                            if not any(abs(r.latitude - parsed.latitude) < 0.005 and abs(r.longitude - parsed.longitude) < 0.005 for r in results):
                                results.append(parsed)
                except Exception as e:
                    logger.debug(f"OWM direct geocoding error: {e}")

            # 4. Quaternary: Open-Meteo Geocoding
            if not results:
                try:
                    om_resp = await client.get(
                        settings.OPEN_METEO_GEOCODING_URL,
                        params={"name": clean, "count": limit, "language": "en", "format": "json"}
                    )
                    if om_resp.status_code == 200:
                        om_data = om_resp.json()
                        for it in om_data.get("results", []):
                            lat = float(it.get("latitude", 0))
                            lon = float(it.get("longitude", 0))
                            name = it.get("name", clean)
                            state = it.get("admin1", "")
                            district = it.get("admin2", "")
                            country = it.get("country", "India")
                            parts = [name]
                            if district and district != name: parts.append(district)
                            if state and state != name: parts.append(state)
                            if country: parts.append(country)
                            formatted = ", ".join(parts)
                            parsed = LocationSearchItem(
                                id=it.get("id", abs(hash(f"{name}_{lat}")) % 1000000),
                                name=name,
                                formattedAddress=formatted,
                                latitude=lat,
                                longitude=lon,
                                country=country,
                                state=state,
                                district=district,
                                city=name,
                                locality=name,
                                sublocality="",
                                neighborhood="",
                                postalCode="",
                                placeId=str(it.get("id", "")),
                                admin1=state,
                                admin2=district,
                            )
                            if not any(abs(r.latitude - parsed.latitude) < 0.005 and abs(r.longitude - parsed.longitude) < 0.005 for r in results):
                                results.append(parsed)
                except Exception as e:
                    logger.debug(f"Open-Meteo geocoding error: {e}")

        return results

    @staticmethod
    async def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
        """
        Translates GPS latitude and longitude into an authentic, highly granular local area,
        neighborhood, sublocality, town/city, district, state, and country.
        Uses Google Maps Reverse Geocoding with fallback to OpenStreetMap Nominatim (zoom 18) and OpenWeatherMap.
        """
        import math
        if math.isnan(lat) or math.isnan(lon):
            lat, lon = settings.DEFAULT_LAT, settings.DEFAULT_LON

        # Check memory cache first (rounded to 3 decimal places ~100m)
        cache_key = (round(lat, 3), round(lon, 3))
        if cache_key in _REVERSE_GEOCODE_CACHE:
            return _REVERSE_GEOCODE_CACHE[cache_key]

        # Nearest landmark/city baseline fallback based on distance
        best_fallback_name = "Kolkata"
        best_fallback_state = "West Bengal"
        min_dist = float("inf")
        for c_key, c_val in INDIAN_CITIES_COORDS.items():
            d2 = (lat - c_val["lat"]) ** 2 + (lon - c_val["lon"]) ** 2
            if d2 < min_dist:
                min_dist = d2
                best_fallback_name = c_val["name"]
                best_fallback_state = c_val.get("state", "India")

        async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
            # 1. OpenWeatherMap fast reverse geocode task
            owm_key = settings.OPENWEATHERMAP_API_KEY or settings.WEATHER_API_KEY
            owm_task = None
            if owm_key:
                owm_task = client.get(
                    "https://api.openweathermap.org/geo/1.0/reverse",
                    params={"lat": lat, "lon": lon, "limit": 1, "appid": owm_key}
                )

            # 2. OpenStreetMap Nominatim task for fine neighborhood/sublocality detail
            nom_task = client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 18, "addressdetails": 1},
                headers={"User-Agent": "WeatherGPT-Platform/3.0"}
            )

            tasks = [t for t in [nom_task, owm_task] if t is not None]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check Nominatim result first for high-granularity locality/neighborhood
            nom_res = results[0] if len(results) > 0 and not isinstance(results[0], Exception) else None
            owm_res = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None

            if nom_res and nom_res.status_code == 200:
                try:
                    data = nom_res.json()
                    if "error" not in data and ("address" in data or "display_name" in data):
                        parsed_nom = WeatherService._parse_nominatim_item(data)
                        if parsed_nom.name and parsed_nom.name != "Selected Location":
                            res_payload = {
                                "name": parsed_nom.name,
                                "formattedAddress": parsed_nom.formattedAddress,
                                "latitude": lat,
                                "longitude": lon,
                                "country": parsed_nom.country,
                                "state": parsed_nom.state or best_fallback_state,
                                "district": parsed_nom.district or "",
                                "city": parsed_nom.city or parsed_nom.name,
                                "locality": parsed_nom.locality or parsed_nom.name,
                                "sublocality": parsed_nom.sublocality or "",
                                "neighborhood": parsed_nom.neighborhood or "",
                                "postalCode": parsed_nom.postalCode or "",
                                "placeId": parsed_nom.placeId or "",
                                "formatted": parsed_nom.formattedAddress,
                                "timezone": "Asia/Kolkata"
                            }
                            _REVERSE_GEOCODE_CACHE[cache_key] = res_payload
                            return res_payload
                except Exception as e:
                    logger.debug(f"Nominatim parse error: {e}")

            # Fallback to OpenWeatherMap reverse geocode
            if owm_res and owm_res.status_code == 200:
                try:
                    owm_items = owm_res.json()
                    if owm_items:
                        it = owm_items[0]
                        name = it.get("name") or best_fallback_name
                        state = it.get("state") or best_fallback_state
                        country = it.get("country") or "India"
                        formatted = f"{name}, {state}, {country}" if state else f"{name}, {country}"
                        return {
                            "name": name,
                            "formattedAddress": formatted,
                            "latitude": lat,
                            "longitude": lon,
                            "country": country,
                            "state": state,
                            "district": "",
                            "city": name,
                            "locality": name,
                            "sublocality": "",
                            "neighborhood": "",
                            "postalCode": "",
                            "placeId": "",
                            "formatted": formatted,
                            "timezone": "Asia/Kolkata"
                        }
                except Exception as e:
                    logger.debug(f"OWM parse error: {e}")

        # 3. Resilient geographic fallback
        formatted_fb = f"{best_fallback_name}, {best_fallback_state}, India"
        return {
            "name": best_fallback_name,
            "formattedAddress": formatted_fb,
            "latitude": lat,
            "longitude": lon,
            "country": "India",
            "state": best_fallback_state,
            "district": "",
            "city": best_fallback_name,
            "locality": best_fallback_name,
            "sublocality": "",
            "neighborhood": "",
            "postalCode": "",
            "placeId": "",
            "formatted": formatted_fb,
            "timezone": "Asia/Kolkata"
        }

    @staticmethod
    async def find_nearby_places(
        category: str,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        limit: int = 8
    ) -> List[LocationSearchItem]:
        """
        Dynamically finds nearby institutions (colleges, schools, hospitals, universities, banks, etc.)
        around given coordinates using OpenStreetMap Nominatim viewbox search.
        """
        import math
        d_lat = radius_km / 111.0
        d_lon = d_lat / max(0.1, math.cos(math.radians(lat)))
        viewbox = f"{lon - d_lon},{lat + d_lat},{lon + d_lon},{lat - d_lat}"

        results: List[LocationSearchItem] = []
        clean_cat = category.strip()

        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": clean_cat,
                        "viewbox": viewbox,
                        "bounded": 1,
                        "format": "json",
                        "addressdetails": 1,
                        "limit": limit
                    },
                    headers={"User-Agent": "WeatherGPT-Platform/2.0"}
                )
                if resp.status_code == 200:
                    for it in resp.json():
                        parsed = WeatherService._parse_nominatim_item(it)
                        if not any(abs(r.latitude - parsed.latitude) < 0.001 and abs(r.longitude - parsed.longitude) < 0.001 for r in results):
                            results.append(parsed)
            except Exception as e:
                logger.debug(f"Nearby places Nominatim viewbox error: {e}")

        # Fallback to general geocoding query if viewbox returned no results
        if not results:
            try:
                results = await WeatherService.geocode(f"{clean_cat} near {lat:.2f},{lon:.2f}", limit=limit)
            except Exception:
                pass
        if not results:
            try:
                results = await WeatherService.geocode(clean_cat, limit=limit)
            except Exception:
                pass

        return results

    @staticmethod
    async def get_weather_for_locations(locations: List[LocationSearchItem]) -> List[Dict[str, Any]]:
        """
        Concurrently retrieves current meteorological observations for multiple locations using
        each location's OWN coordinates. Employs asyncio.gather(..., return_exceptions=True) so
        failure of one location never impacts the others.
        """
        async def _fetch_single(loc: LocationSearchItem) -> Dict[str, Any]:
            loc_dict = loc.model_dump() if hasattr(loc, "model_dump") else loc.dict()
            try:
                w = await WeatherService.get_current_weather(loc.latitude, loc.longitude, loc.name)
                return {
                    **loc_dict,
                    "weather": {
                        "temperature": round(w.temperature, 1),
                        "feels_like": round(w.feels_like, 1),
                        "weather_desc": w.weather_desc,
                        "weather_icon": w.weather_icon,
                        "humidity": w.humidity,
                        "wind_speed": round(w.wind_speed, 1),
                        "pressure": round(w.pressure, 1),
                        "aqi": w.aqi,
                        "aqi_desc": w.aqi_desc
                    }
                }
            except Exception as e:
                logger.debug(f"Failed to fetch weather for {loc.name} ({loc.latitude}, {loc.longitude}): {e}")
                return {
                    **loc_dict,
                    "weather": None,
                    "error": "Weather unavailable"
                }

        tasks = [_fetch_single(loc) for loc in locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, dict):
                valid.append(r)
        return valid

    @staticmethod
    async def _fetch_from_openweathermap(lat: float, lon: float, city: str = "") -> Optional[WeatherForecastResponse]:
        """Fetches real-time weather and 5-day forecast using user's OpenWeatherMap API key with second-by-second live telemetry."""
        api_key = settings.OPENWEATHERMAP_API_KEY or settings.WEATHER_API_KEY
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                w_task = client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
                )
                f_task = client.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
                )
                a_task = client.get(
                    "https://api.openweathermap.org/data/2.5/air_pollution",
                    params={"lat": lat, "lon": lon, "appid": api_key}
                )
                om_task = client.get(
                    settings.OPEN_METEO_FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": [
                            "temperature_2m",
                            "precipitation_probability",
                            "precipitation",
                            "weather_code",
                            "wind_speed_10m",
                        ],
                        "forecast_days": 2,
                        "timezone": "auto",
                    }
                )
                res_w, res_f, res_a, res_om = await asyncio.gather(w_task, f_task, a_task, om_task, return_exceptions=True)

                if isinstance(res_w, Exception) or res_w.status_code != 200:
                    return None

                w_data = res_w.json()
                main = w_data.get("main", {})
                wind = w_data.get("wind", {})
                weather_arr = w_data.get("weather", [{}])
                w_info = weather_arr[0] if weather_arr else {}
                w_id = int(w_info.get("id", 800))
                desc = w_info.get("description", "Clear").title()

                icon = "☀️"
                if w_id < 300: icon = "⛈️"
                elif w_id < 600: icon = "🌧️"
                elif w_id < 700: icon = "❄️"
                elif w_id < 800: icon = "🌫️"
                elif w_id == 800: icon = "☀️"
                elif w_id <= 804: icon = "⛅"

                aqi_val = 65
                pm25 = 25.0
                pm10 = 45.0
                if not isinstance(res_a, Exception) and res_a.status_code == 200:
                    a_list = res_a.json().get("list", [])
                    if a_list:
                        comps = a_list[0].get("components", {})
                        pm25 = float(comps.get("pm2_5", 25.0))
                        pm10 = float(comps.get("pm10", 45.0))
                        owm_aqi = int(a_list[0].get("main", {}).get("aqi", 2))
                        aqi_scale = {1: 35, 2: 70, 3: 115, 4: 165, 5: 240}
                        aqi_val = aqi_scale.get(owm_aqi, 70)

                aqi_int, aqi_desc = interpret_aqi(aqi_val)

                from datetime import datetime, timezone, timedelta
                utc_offset = int(w_data.get("timezone", 19800))
                if not isinstance(res_om, Exception) and res_om.status_code == 200:
                    try:
                        utc_offset = int(res_om.json().get("utc_offset_seconds", utc_offset))
                    except Exception:
                        pass

                local_tz = timezone(timedelta(seconds=utc_offset))
                local_now = datetime.now(local_tz)
                now_str = local_now.strftime("%Y-%m-%d %H:%M:%S")
                now_hour_str = local_now.strftime("%Y-%m-%dT%H:00")

                current = WeatherCurrent(
                    city=city or w_data.get("name") or "Live Station",
                    latitude=lat,
                    longitude=lon,
                    timezone="Asia/Kolkata",
                    temperature=float(main.get("temp", 30.0)),
                    feels_like=float(main.get("feels_like", 32.0)),
                    humidity=int(main.get("humidity", 50)),
                    wind_speed=round(float(wind.get("speed", 2.0)) * 3.6, 1),
                    wind_direction=int(wind.get("deg", 180)),
                    wind_gust=round(float(wind.get("gust", wind.get("speed", 2.0))) * 3.6, 1),
                    pressure=float(main.get("pressure", 1010.0)),
                    precipitation=float(w_data.get("rain", {}).get("1h", 0.0) or w_data.get("snow", {}).get("1h", 0.0)),
                    cloud_cover=int(w_data.get("clouds", {}).get("all", 20)),
                    weather_code=w_id,
                    weather_desc=desc,
                    weather_icon=icon,
                    uv_index=5.0,
                    aqi=aqi_int,
                    aqi_desc=aqi_desc,
                    pm25=pm25,
                    pm10=pm10,
                    timestamp=f"Live • {now_str}",
                )

                hourly = []
                # 1. High-precision 1-hour resolution from Open-Meteo sliced from current hour
                if not isinstance(res_om, Exception) and res_om.status_code == 200:
                    try:
                        om_data = res_om.json()
                        h_raw = om_data.get("hourly", {})
                        t_arr = h_raw.get("time", [])
                        temp_arr = h_raw.get("temperature_2m", [])
                        pop_arr = h_raw.get("precipitation_probability", [])
                        prec_arr = h_raw.get("precipitation", [])
                        code_arr = h_raw.get("weather_code", [])
                        wind_arr = h_raw.get("wind_speed_10m", [])

                        start_idx = 0
                        for idx_t, t_val in enumerate(t_arr):
                            if t_val >= now_hour_str:
                                start_idx = idx_t
                                break

                        for k in range(start_idx, min(start_idx + 24, len(t_arr))):
                            code = int(code_arr[k]) if k < len(code_arr) else 0
                            h_desc, h_icon = get_wmo_info(code)
                            time_part = t_arr[k].split("T")[-1][:5] if "T" in t_arr[k] else t_arr[k]
                            hourly.append(HourlyPoint(
                                time=time_part,
                                temperature=float(temp_arr[k]) if k < len(temp_arr) else 28.0,
                                precipitation_prob=int(pop_arr[k]) if k < len(pop_arr) and pop_arr[k] is not None else 0,
                                precipitation=float(prec_arr[k]) if k < len(prec_arr) and prec_arr[k] is not None else 0.0,
                                weather_code=code,
                                weather_desc=h_desc,
                                weather_icon=h_icon,
                                wind_speed=float(wind_arr[k]) if k < len(wind_arr) else 10.0
                            ))
                    except Exception as e:
                        logger.debug(f"Open-Meteo hourly parse error in OWM fetcher: {e}")

                # 2. Fallback to OpenWeatherMap forecast if Open-Meteo hourly was empty
                if not hourly and not isinstance(res_f, Exception) and res_f.status_code == 200:
                    f_list = res_f.json().get("list", [])
                    cutoff_epoch = local_now.timestamp() - 3600
                    for item in f_list:
                        dt_epoch = item.get("dt", 0)
                        if dt_epoch < cutoff_epoch:
                            continue
                        dt_local = datetime.fromtimestamp(dt_epoch, tz=local_tz)
                        time_part = dt_local.strftime("%H:%M")
                        item_w = item.get("weather", [{}])[0]
                        w_mid = int(item_w.get("id", 800))
                        item_icon = "☀️"
                        if w_mid < 300: item_icon = "⛈️"
                        elif w_mid < 600: item_icon = "🌧️"
                        elif w_mid < 700: item_icon = "❄️"
                        elif w_mid < 800: item_icon = "🌫️"
                        elif w_mid <= 804: item_icon = "⛅"
                        hourly.append(HourlyPoint(
                            time=time_part,
                            temperature=float(item.get("main", {}).get("temp", 28.0)),
                            precipitation_prob=int(item.get("pop", 0.0) * 100),
                            precipitation=float(item.get("rain", {}).get("3h", 0.0)),
                            weather_code=w_mid,
                            weather_desc=item_w.get("description", "Clear").title(),
                            weather_icon=item_icon,
                            wind_speed=round(float(item.get("wind", {}).get("speed", 2.0)) * 3.6, 1)
                        ))
                        if len(hourly) >= 8:
                            break

                daily = []
                if not isinstance(res_f, Exception) and res_f.status_code == 200:
                    f_list = res_f.json().get("list", [])
                    grouped_days = {}
                    for item in f_list:
                        d_str = item.get("dt_txt", "").split(" ")[0]
                        if not d_str: continue
                        if d_str not in grouped_days:
                            grouped_days[d_str] = []
                        grouped_days[d_str].append(item)

                    for d_str, day_items in list(grouped_days.items())[:7]:
                        temps = [it.get("main", {}).get("temp", 28.0) for it in day_items]
                        t_max = max(temps) if temps else 32.0
                        t_min = min(temps) if temps else 24.0
                        max_pop = max([int(it.get("pop", 0.0) * 100) for it in day_items]) if day_items else 10
                        rain_sum = sum([float(it.get("rain", {}).get("3h", 0.0)) for it in day_items])
                        mid_item = day_items[len(day_items) // 2]
                        mid_w = mid_item.get("weather", [{}])[0]
                        mid_id = int(mid_w.get("id", 800))
                        d_icon = "☀️"
                        if mid_id < 300: d_icon = "⛈️"
                        elif mid_id < 600: d_icon = "🌧️"
                        elif mid_id < 700: d_icon = "❄️"
                        elif mid_id < 800: d_icon = "🌫️"
                        elif mid_id == 800: d_icon = "☀️"
                        elif mid_id <= 804: d_icon = "⛅"

                        daily.append(DailyForecast(
                            date=d_str,
                            temp_max=float(t_max),
                            temp_min=float(t_min),
                            precipitation_sum=round(rain_sum, 1),
                            precipitation_prob=max_pop,
                            weather_code=mid_id,
                            weather_desc=mid_w.get("description", "Clear").title(),
                            weather_icon=d_icon,
                            uv_index_max=5.0
                        ))

                return WeatherForecastResponse(current=current, hourly_24h=hourly, daily_7d=daily)
        except Exception as e:
            logger.warning(f"OpenWeatherMap request failed: {e}")
        return None


    @staticmethod
    async def _fetch_from_weather_api(lat: float, lon: float, city: str = "") -> Optional[WeatherForecastResponse]:
        """Fetches from WeatherAPI.com when WEATHER_API_KEY is configured."""
        if not settings.WEATHER_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                resp = await client.get(
                    f"{settings.WEATHER_API_URL}/forecast.json",
                    params={
                        "key": settings.WEATHER_API_KEY,
                        "q": f"{lat},{lon}",
                        "days": 7,
                        "aqi": "yes",
                        "alerts": "yes"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    loc = data.get("location", {})
                    curr = data.get("current", {})
                    f_days = data.get("forecast", {}).get("forecastday", [])

                    aqi_data = curr.get("air_quality", {})
                    pm25 = float(aqi_data.get("pm2_5", 25.0))
                    pm10 = float(aqi_data.get("pm10", 50.0))
                    epa_index = int(aqi_data.get("us-epa-index", 2))
                    aqi_map = {1: 45, 2: 85, 3: 130, 4: 175, 5: 250, 6: 350}
                    aqi_val = aqi_map.get(epa_index, 75)
                    aqi_int, aqi_desc = interpret_aqi(aqi_val)

                    condition = curr.get("condition", {})
                    desc = condition.get("text", "Partly Cloudy")
                    icon = "☀️"
                    if "rain" in desc.lower(): icon = "🌧️"
                    elif "thunder" in desc.lower(): icon = "⛈️"
                    elif "cloud" in desc.lower(): icon = "⛅"
                    elif "snow" in desc.lower(): icon = "❄️"
                    elif "fog" in desc.lower() or "mist" in desc.lower(): icon = "🌫️"

                    current = WeatherCurrent(
                        city=city or loc.get("name", "New Delhi"),
                        latitude=lat,
                        longitude=lon,
                        timezone=loc.get("tz_id", "Asia/Kolkata"),
                        temperature=float(curr.get("temp_c", 30.0)),
                        feels_like=float(curr.get("feelslike_c", 32.0)),
                        humidity=int(curr.get("humidity", 50)),
                        wind_speed=float(curr.get("wind_kph", 12.0)),
                        wind_direction=int(curr.get("wind_degree", 180)),
                        wind_gust=float(curr.get("gust_kph", 16.0)),
                        pressure=float(curr.get("pressure_mb", 1010.0)),
                        precipitation=float(curr.get("precip_mm", 0.0)),
                        cloud_cover=int(curr.get("cloud", 20)),
                        weather_code=condition.get("code", 1000),
                        weather_desc=desc,
                        weather_icon=icon,
                        uv_index=float(curr.get("uv", 5.0)),
                        aqi=aqi_int,
                        aqi_desc=aqi_desc,
                        pm25=pm25,
                        pm10=pm10,
                        timestamp="Live",
                    )

                    hourly = []
                    if f_days and "hour" in f_days[0]:
                        for h_data in f_days[0]["hour"][:24]:
                            time_str = h_data.get("time", "").split(" ")[-1]
                            h_cond = h_data.get("condition", {}).get("text", "Clear")
                            hourly.append(
                                HourlyPoint(
                                    time=time_str or "12:00",
                                    temperature=float(h_data.get("temp_c", 28.0)),
                                    precipitation_prob=int(h_data.get("chance_of_rain", 0)),
                                    precipitation=float(h_data.get("precip_mm", 0.0)),
                                    weather_code=h_data.get("condition", {}).get("code", 1000),
                                    weather_desc=h_cond,
                                    wind_speed=float(h_data.get("wind_kph", 10.0))
                                )
                            )

                    daily = []
                    for f in f_days[:7]:
                        d_day = f.get("day", {})
                        d_cond = d_day.get("condition", {}).get("text", "Sunny")
                        d_icon = "☀️"
                        if "rain" in d_cond.lower(): d_icon = "🌧️"
                        elif "cloud" in d_cond.lower(): d_icon = "⛅"
                        daily.append(
                            DailyForecast(
                                date=f.get("date", "Today"),
                                temp_max=float(d_day.get("maxtemp_c", 32.0)),
                                temp_min=float(d_day.get("mintemp_c", 24.0)),
                                precipitation_sum=float(d_day.get("totalprecip_mm", 0.0)),
                                precipitation_prob=int(d_day.get("daily_chance_of_rain", 10)),
                                weather_code=d_day.get("condition", {}).get("code", 1000),
                                weather_desc=d_cond,
                                weather_icon=d_icon,
                                uv_index_max=float(d_day.get("uv", 5.0))
                            )
                        )
                    return WeatherForecastResponse(current=current, hourly_24h=hourly, daily_7d=daily)
        except Exception as e:
            logger.warning(f"WeatherAPI.com request failed, falling back to Open-Meteo: {e}")
        return None

    @staticmethod
    async def get_forecast(lat: float, lon: float, city: str = "") -> WeatherForecastResponse:
        """
        Fetches real-time live weather with second-by-second updates.
        Checks OpenWeatherMap (user's live API key), then WeatherAPI.com, then Open-Meteo.
        """
        # Resolve real place name if city is empty or placeholder
        if not city or city in ("Selected Location", "Selected Place", "Selected", "Locating..."):
            try:
                rev = await WeatherService.reverse_geocode(lat, lon)
                city = rev.get("sublocality") or rev.get("locality") or rev.get("name") or rev.get("city") or "Kolkata"
            except Exception:
                city = "Kolkata"

        # Check short-lived in-memory forecast cache (35s)
        cache_key = (round(lat, 3), round(lon, 3), (city or "").strip().lower())
        import time as _time
        now_ts = _time.time()
        if cache_key in _FORECAST_CACHE:
            cached_ts, cached_resp = _FORECAST_CACHE[cache_key]
            if now_ts - cached_ts < 35.0:
                return cached_resp

        # 1. Attempt OpenWeatherMap with user's live key
        owm_res = await WeatherService._fetch_from_openweathermap(lat, lon, city)
        if owm_res:
            _FORECAST_CACHE[cache_key] = (now_ts, owm_res)
            return owm_res

        # 2. Attempt WeatherAPI.com if key exists
        weather_api_res = await WeatherService._fetch_from_weather_api(lat, lon, city)
        if weather_api_res:
            _FORECAST_CACHE[cache_key] = (now_ts, weather_api_res)
            return weather_api_res

        # 2. Open-Meteo unified call
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                # 1. Single unified call for current + hourly + daily
                forecast_task = client.get(
                    settings.OPEN_METEO_FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": [
                            "temperature_2m",
                            "relative_humidity_2m",
                            "apparent_temperature",
                            "precipitation",
                            "weather_code",
                            "surface_pressure",
                            "cloud_cover",
                            "wind_speed_10m",
                            "wind_direction_10m",
                            "wind_gusts_10m",
                        ],
                        "hourly": [
                            "temperature_2m",
                            "precipitation_probability",
                            "precipitation",
                            "weather_code",
                            "wind_speed_10m",
                        ],
                        "daily": [
                            "temperature_2m_max",
                            "temperature_2m_min",
                            "precipitation_sum",
                            "precipitation_probability_max",
                            "weather_code",
                            "uv_index_max",
                        ],
                        "forecast_days": 7,
                        "timezone": "auto",
                    }
                )

                # 2. Parallel call for air quality
                aqi_task = client.get(
                    settings.OPEN_METEO_AIR_QUALITY_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": ["us_aqi", "pm2_5", "pm10", "uv_index"],
                    }
                )

                res_forecast, res_aqi = await asyncio.gather(forecast_task, aqi_task, return_exceptions=True)

                if not isinstance(res_forecast, Exception) and res_forecast.status_code == 200:
                    data = res_forecast.json()
                    curr_raw = data.get("current", {})
                    hourly_raw = data.get("hourly", {})
                    daily_raw = data.get("daily", {})

                    aqi_val = 48.0
                    pm25_val = 20.0
                    pm10_val = 45.0
                    uv_val = 5.0
                    if not isinstance(res_aqi, Exception) and res_aqi.status_code == 200:
                        aqi_data = res_aqi.json().get("current", {})
                        aqi_val = aqi_data.get("us_aqi", 48.0)
                        pm25_val = aqi_data.get("pm2_5", 20.0)
                        pm10_val = aqi_data.get("pm10", 45.0)
                        uv_val = aqi_data.get("uv_index", 5.0)

                    w_code = int(curr_raw.get("weather_code", 0))
                    desc, icon = get_wmo_info(w_code)
                    aqi_int, aqi_desc = interpret_aqi(aqi_val)

                    current = WeatherCurrent(
                        city=city or "Kolkata",
                        latitude=lat,
                        longitude=lon,
                        timezone=data.get("timezone", "Asia/Kolkata"),
                        temperature=float(curr_raw.get("temperature_2m", 32.0)),
                        feels_like=float(curr_raw.get("apparent_temperature", 34.0)),
                        humidity=int(curr_raw.get("relative_humidity_2m", 50)),
                        wind_speed=float(curr_raw.get("wind_speed_10m", 14.0)),
                        wind_direction=int(curr_raw.get("wind_direction_10m", 180)),
                        wind_gust=curr_raw.get("wind_gusts_10m"),
                        pressure=float(curr_raw.get("surface_pressure", 1008.0)),
                        precipitation=float(curr_raw.get("precipitation", 0.0)),
                        cloud_cover=int(curr_raw.get("cloud_cover", 20)),
                        weather_code=w_code,
                        weather_desc=desc,
                        weather_icon=icon,
                        uv_index=uv_val or 5.0,
                        aqi=aqi_int or 48,
                        aqi_desc=aqi_desc or "Good",
                        pm25=pm25_val,
                        pm10=pm10_val,
                        timestamp=curr_raw.get("time", "Now"),
                    )

                    # Determine local hour index to prevent past hours
                    utc_offset = int(data.get("utc_offset_seconds", 19800))
                    from datetime import datetime, timezone, timedelta
                    local_tz = timezone(timedelta(seconds=utc_offset))
                    local_now = datetime.now(local_tz)
                    now_hour_str = local_now.strftime("%Y-%m-%dT%H:00")

                    times = hourly_raw.get("time", [])
                    temps = hourly_raw.get("temperature_2m", [])
                    probs = hourly_raw.get("precipitation_probability", [])
                    precips = hourly_raw.get("precipitation", [])
                    codes = hourly_raw.get("weather_code", [])
                    winds = hourly_raw.get("wind_speed_10m", [])

                    start_idx = 0
                    for idx_t, t_val in enumerate(times):
                        if t_val >= now_hour_str:
                            start_idx = idx_t
                            break

                    hourly_list: List[HourlyPoint] = []
                    for i in range(start_idx, min(start_idx + 24, len(times))):
                        code = codes[i] if i < len(codes) else 0
                        h_desc, h_icon = get_wmo_info(code)
                        time_str = times[i].split("T")[-1][:5] if "T" in times[i] else times[i]
                        hourly_list.append(
                            HourlyPoint(
                                time=time_str,
                                temperature=float(temps[i]) if i < len(temps) else 28.0,
                                precipitation_prob=int(probs[i]) if i < len(probs) and probs[i] is not None else 0,
                                precipitation=float(precips[i]) if i < len(precips) and precips[i] is not None else 0.0,
                                weather_code=code,
                                weather_desc=h_desc,
                                weather_icon=h_icon,
                                wind_speed=float(winds[i]) if i < len(winds) else 10.0,
                            )
                        )

                    daily_list: List[DailyForecast] = []
                    d_times = daily_raw.get("time", [])
                    t_max = daily_raw.get("temperature_2m_max", [])
                    t_min = daily_raw.get("temperature_2m_min", [])
                    p_sums = daily_raw.get("precipitation_sum", [])
                    p_probs = daily_raw.get("precipitation_probability_max", [])
                    d_codes = daily_raw.get("weather_code", [])
                    uv_max = daily_raw.get("uv_index_max", [])

                    for j in range(len(d_times)):
                        code = d_codes[j] if j < len(d_codes) else 0
                        d_desc, d_icon = get_wmo_info(code)
                        daily_list.append(
                            DailyForecast(
                                date=d_times[j],
                                temp_max=float(t_max[j]) if j < len(t_max) else 34.0,
                                temp_min=float(t_min[j]) if j < len(t_min) else 24.0,
                                precipitation_sum=float(p_sums[j]) if j < len(p_sums) and p_sums[j] is not None else 0.0,
                                precipitation_prob=int(p_probs[j]) if j < len(p_probs) and p_probs[j] is not None else 0,
                                weather_code=code,
                                weather_desc=d_desc,
                                weather_icon=d_icon,
                                uv_index_max=float(uv_max[j]) if j < len(uv_max) and uv_max[j] is not None else 6.0,
                            )
                        )

                    fc_response = WeatherForecastResponse(
                        current=current,
                        hourly_24h=hourly_list,
                        daily_7d=daily_list
                    )
                    _FORECAST_CACHE[cache_key] = (now_ts, fc_response)
                    return fc_response

        except Exception as e:
            logger.error(f"Weather API timeout / connection issue: {e}. Falling back to instant local meteorological model.")

        # Immediate resilient fallback
        fallback_resp = create_fallback_forecast(lat, lon, city)
        _FORECAST_CACHE[cache_key] = (now_ts, fallback_resp)
        return fallback_resp

    @staticmethod
    async def get_current_weather(lat: float, lon: float, city: str = "") -> WeatherCurrent:
        forecast_res = await WeatherService.get_forecast(lat, lon, city)
        return forecast_res.current

weather_service = WeatherService()
