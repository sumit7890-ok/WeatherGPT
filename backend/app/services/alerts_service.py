import datetime
from typing import List, Optional
from ..config import settings
from ..schemas import AlertItem, WeatherCurrent

# Simulated National Active Bulletins representing typical IMD seasonal warnings
IMD_BULLETINS_DATABASE = [
    {
        "alert_id": "IMD-CYC-2026-01",
        "region": "Odisha & North Andhra Coast",
        "state": "Odisha",
        "hazard_type": "Cyclonic Storm & Squally Winds",
        "severity": "ORANGE",
        "headline": "Deep Depression intensifying into Cyclonic Storm over West-Central Bay of Bengal",
        "description": "Squally wind speed reaching 55-65 kmph gusting to 75 kmph likely along and off Odisha and north Andhra Pradesh coasts. Sea condition will be rough to very rough.",
        "advisory": "Fishermen are advised not to venture into deep sea areas. Coastal residents should secure loose structures. Farmers should harvest mature paddy and store in safe sheds.",
        "valid_until": "2026-09-08T23:59:00"
    },
    {
        "alert_id": "IMD-RAIN-2026-04",
        "region": "Konkan & Goa, Mumbai Metropolitan Region",
        "state": "Maharashtra",
        "hazard_type": "Extremely Heavy Rainfall & Urban Waterlogging",
        "severity": "ORANGE",
        "headline": "Active Monsoon trough causing isolated extremely heavy downpours",
        "description": "Heavy to very heavy rainfall exceeding 115.6 mm to 204.4 mm expected in Mumbai, Thane, and Raigad districts over the next 48 hours. Risk of localized flooding and transit delays.",
        "advisory": "Avoid low-lying underpasses and waterlogged routes. Keep emergency kits ready. Local train schedules may be regulated. Disaster teams are on standby.",
        "valid_until": "2026-09-06T18:00:00"
    },
    {
        "alert_id": "IMD-THUNDER-2026-09",
        "region": "Assam & Meghalaya",
        "state": "Assam",
        "hazard_type": "Severe Thunderstorm & Lightning",
        "severity": "YELLOW",
        "headline": "Thunderstorm accompanied by lightning and gusty winds (30-40 kmph)",
        "description": "Scattered thunderstorms likely across Brahmaputra valley. Sudden lightning strikes pose hazard in open agricultural fields.",
        "advisory": "Take shelter inside sturdy buildings during lightning. Do not take shelter under tall trees or metal poles. Unplug electrical appliances.",
        "valid_until": "2026-09-05T20:00:00"
    },
    {
        "alert_id": "IMD-HEAT-2026-02",
        "region": "West Rajasthan & Vidarbha",
        "state": "Rajasthan",
        "hazard_type": "Severe Heatwave Conditions",
        "severity": "YELLOW",
        "headline": "Heatwave conditions in isolated pockets with max temp above 42°C",
        "description": "High temperature and warm night conditions likely. Elevated risk of heat illness for infants, elderly, and chronic disease patients.",
        "advisory": "Drink plenty of water (ORSL, buttermilk, lemon water). Avoid peak sun exposure between 12:00 PM and 3:30 PM. Wear light, loose cotton clothes.",
        "valid_until": "2026-09-07T18:00:00"
    }
]

class AlertsService:
    @staticmethod
    def get_color_meta(severity: str) -> dict:
        sev = severity.upper()
        return settings.ALERT_COLORS.get(sev, settings.ALERT_COLORS["GREEN"])

    @staticmethod
    def evaluate_live_weather_hazard(weather: WeatherCurrent, region_name: str) -> Optional[AlertItem]:
        """Dynamically identifies hazards from live weather metrics and maps to IMD levels."""
        hazard_type = None
        severity = "GREEN"
        headline = ""
        description = ""
        advisory = ""

        # Wind & Cyclone thresholds
        if weather.wind_speed >= 75.0 or (weather.wind_gust and weather.wind_gust >= 90.0):
            hazard_type = "Severe Gale & Cyclonic Winds"
            severity = "RED"
            headline = f"Red Warning: Dangerous winds ({weather.wind_speed:.1f} km/h) in {region_name}"
            description = "Extremely high wind speeds posing severe danger to life, uprooting trees and damaging electrical infrastructure."
            advisory = "Remain indoors away from windows. Fishermen suspend all operations. Follow disaster management directives immediately."
        elif weather.wind_speed >= 50.0 or (weather.wind_gust and weather.wind_gust >= 65.0):
            hazard_type = "Squally Wind / Strong Gales"
            severity = "ORANGE"
            headline = f"Orange Alert: Squally winds ({weather.wind_speed:.1f} km/h) in {region_name}"
            description = "Strong winds capable of breaking tree branches and disrupting public transit."
            advisory = "Secure loose roofs and hoardings. Avoid venturing into open sea or high altitude exposed locations."
        
        # Rainfall & Flooding thresholds
        elif weather.precipitation >= 65.0 or weather.weather_code in (65, 82):
            hazard_type = "Extremely Heavy Rainfall & Flood Risk"
            severity = "RED"
            headline = f"Red Warning: Torrential rainfall recorded in {region_name}"
            description = "Intense localized downpour leading to severe inundation, localized flooding, and drainage overflow."
            advisory = "Do not attempt to drive through flooded roads. Keep mobile devices charged. Emergency evacuation readiness recommended."
        elif weather.precipitation >= 15.0 or weather.weather_code in (63, 81):
            hazard_type = "Heavy Rainfall"
            severity = "ORANGE"
            headline = f"Orange Alert: Heavy rainfall underway in {region_name}"
            description = "Persistent rainfall likely to cause water accumulation on roads and agricultural fields."
            advisory = "Drain excess water from agricultural fields. Commuters should allow extra travel time."
        
        # Thunderstorm & Lightning
        elif weather.weather_code in (95, 96, 99):
            hazard_type = "Thunderstorm & Lightning Hazard"
            severity = "ORANGE" if weather.weather_code >= 96 else "YELLOW"
            headline = f"{severity.title()} Alert: Thunderstorm & Lightning detected around {region_name}"
            description = "Convective cloud activity generating thunder, lightning, and possible hail."
            advisory = "Immediately seek indoor shelter. Avoid open fields, metal fencing, and water bodies."

        # Heatwave thresholds
        elif weather.temperature >= 44.0:
            hazard_type = "Severe Heatwave"
            severity = "RED"
            headline = f"Red Warning: Severe Heatwave ({weather.temperature:.1f}°C) in {region_name}"
            description = "Extreme heat condition poses serious risk of heat stroke and severe dehydration."
            advisory = "Avoid sun exposure completely between 11 AM - 4 PM. Stay hydrated. Farmers reschedule field work to early morning."
        elif weather.temperature >= 40.0:
            hazard_type = "Heatwave"
            severity = "YELLOW"
            headline = f"Yellow Watch: Elevated temperatures ({weather.temperature:.1f}°C) in {region_name}"
            description = "Moderate heat conditions requiring standard hydration and sun protection."
            advisory = "Drink adequate water, wear protective headwear, and protect livestock."

        # AQI / Smog thresholds
        elif weather.aqi and weather.aqi >= 300:
            hazard_type = "Hazardous Air Quality / Severe Smog"
            severity = "RED" if weather.aqi >= 400 else "ORANGE"
            headline = f"{severity.title()} Alert: Severe Pollution Level (AQI: {weather.aqi}) in {region_name}"
            description = "Air quality is in the severe category with high particulate matter (PM2.5 / PM10)."
            advisory = "Vulnerable populations, elderly and children must stay indoors. Use N95 masks if stepping outside."

        if hazard_type:
            meta = AlertsService.get_color_meta(severity)
            return AlertItem(
                alert_id=f"LIVE-{hash(region_name + str(weather.temperature)) % 100000}",
                region=region_name,
                state=None,
                hazard_type=hazard_type,
                severity=severity,
                severity_level=meta["level"],
                severity_color=meta["hex"],
                severity_title=meta["name"],
                headline=headline,
                description=description,
                advisory=advisory,
                valid_from=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                valid_until=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()
            )
        return None

    @staticmethod
    def get_alerts_for_location(region_name: str, weather_current: Optional[WeatherCurrent] = None) -> List[AlertItem]:
        """Returns matching active alerts for a given region."""
        alerts: List[AlertItem] = []
        clean_reg = region_name.lower().strip()

        # 1. Match against official database
        for b in IMD_BULLETINS_DATABASE:
            b_reg = b["region"].lower()
            b_state = (b.get("state") or "").lower()
            if (clean_reg in b_reg or b_reg in clean_reg or 
                (b_state and (clean_reg in b_state or b_state in clean_reg))):
                meta = AlertsService.get_color_meta(b["severity"])
                alerts.append(
                    AlertItem(
                        alert_id=b["alert_id"],
                        region=b["region"],
                        state=b.get("state"),
                        hazard_type=b["hazard_type"],
                        severity=b["severity"],
                        severity_level=meta["level"],
                        severity_color=meta["hex"],
                        severity_title=meta["name"],
                        headline=b["headline"],
                        description=b["description"],
                        advisory=b["advisory"],
                        valid_from=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        valid_until=b.get("valid_until"),
                    )
                )

        # 2. Add real-time sensor dynamic hazard evaluation
        if weather_current:
            live_hazard = AlertsService.evaluate_live_weather_hazard(weather_current, region_name)
            if live_hazard and not any(a.hazard_type == live_hazard.hazard_type for a in alerts):
                alerts.insert(0, live_hazard)

        # 3. If no warnings exist, return GREEN normal status
        if not alerts:
            meta = AlertsService.get_color_meta("GREEN")
            alerts.append(
                AlertItem(
                    alert_id=f"NORM-{hash(clean_reg) % 10000}",
                    region=region_name,
                    state=None,
                    hazard_type="Normal Meteorological Conditions",
                    severity="GREEN",
                    severity_level=meta["level"],
                    severity_color=meta["hex"],
                    severity_title=meta["name"],
                    headline=f"No Active Severe Weather Warnings for {region_name}",
                    description="Atmospheric conditions are within normal baseline ranges. No cyclonic, torrential rain, or severe heat hazards expected at this time.",
                    advisory="Standard daily precautions apply. Keep checking daily weather forecasts for updates.",
                    valid_from=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    valid_until=None
                )
            )

        return alerts

    @staticmethod
    def get_national_alerts_overview() -> List[AlertItem]:
        """Returns all currently active regional warnings across India."""
        results: List[AlertItem] = []
        for b in IMD_BULLETINS_DATABASE:
            meta = AlertsService.get_color_meta(b["severity"])
            results.append(
                AlertItem(
                    alert_id=b["alert_id"],
                    region=b["region"],
                    state=b.get("state"),
                    hazard_type=b["hazard_type"],
                    severity=b["severity"],
                    severity_level=meta["level"],
                    severity_color=meta["hex"],
                    severity_title=meta["name"],
                    headline=b["headline"],
                    description=b["description"],
                    advisory=b["advisory"],
                    valid_from=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    valid_until=b.get("valid_until"),
                )
            )
        return results

alerts_service = AlertsService()
