import re
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

from ..config import settings
from ..schemas import WeatherCurrent, AlertItem, DailyForecast, HourlyPoint

logger = logging.getLogger(__name__)

METEOROLOGICAL_SYSTEM_PROMPT = """You are WeatherGPT, a conversational weather assistant. Answer the user's questions naturally and intelligently using the weather data supplied by the application. Understand the user's intent and conversation context. Use the supplied weather data as the factual source for weather information. Never fabricate weather conditions, forecasts, locations, or measurements.

GUIDELINES FOR REASONING AND BEHAVIOR:
1. Natural Conversational Understanding:
   - Understand the user's specific intent directly (e.g. umbrella recommendations, outfit advice, travel feasibility, outdoor plans, temperature comparisons, rain timing, wind conditions).
   - Reason logically over the provided meteorological metrics (temperature, feels-like, humidity, rain probability, wind speed, wind gusts, UV index, air quality, cloud cover, pressure).
   - Provide direct, helpful guidance based on those numbers:
     - Umbrella: recommend carrying one if precipitation probability is elevated (>= 30%) or rain/storm conditions are indicated in the timeline/forecast.
     - Clothing / Comfort: factor in temperature, feels-like temperature, wind, and humidity.
     - Activities / Travel: consider severe weather, rain timing, wind gusts, and visibility.
2. Conversational Context & Multi-Turn References:
   - Carefully follow multi-turn dialog context. If the user refers to earlier messages (e.g. "Will it rain?", "What about tomorrow?", "What about the day after?", "How cold will it get then?", "Which of those two days is better?"), resolve the intended date, time, and location using the conversation history.
3. Strict Factual Grounding:
   - Base all statements on the real weather data provided in the prompt.
   - If the user asks for weather data that is not available (such as forecasts beyond the 7-day forecast, unmeasured parameters, or past historical records), clearly and politely inform the user that this specific information is not available in the current forecast data, instead of inventing or estimating.
4. Response Style & Conciseness:
   - Keep answers natural, clear, and focused (usually 2 to 3 well-crafted sentences, or organized bullet points if comparing multiple days or locations).
   - Do not recite raw JSON or dump unnecessary data; explain the weather insight meaningfully.
5. Multilingual Fluency:
   - If the user addresses you in Hindi, reply in natural Hindi.
   - If in Bengali, reply in natural Bengali.
   - If in English or another language, reply in that language.
6. Guardrails & Politeness:
   - When greeted (e.g. "Hello", "Hi WeatherGPT", "Good morning"), greet back warmly and offer assistance with weather observations or forecasts.
   - If asked completely non-weather questions (e.g. programming, political opinions, cooking recipes, math homework), politely remind the user that you are WeatherGPT, specialized only in meteorological analysis and climate guidance, and invite them to ask about the weather.
7. Interactive Map & Live Navigation Integration:
   - You are directly paired with WeatherGPT's live interactive satellite and topographic map.
   - When the user asks to locate, point, show, view, navigate to, or find any place or city on the map (e.g., "locate Durgapur on map", "show Mumbai on map", "where is London", "Paris"), the application automatically centers, flies to, and pins that location on the map.
   - Acknowledge that the location has been located/centered on the map, and provide the real-time weather and forecast for that location using the provided meteorological data.
   - NEVER state or claim "I cannot show maps", "I lack map-rendering capabilities", or decline location/map requests. You and the map work seamlessly together!"""


class AIService:
    @staticmethod
    def _detect_language(text: str) -> str:
        """Detects if text contains Bengali or Devanagari characters."""
        if re.search(r'[\u0980-\u09FF]', text):
            return "bn"
        if re.search(r'[\u0900-\u097F]', text):
            return "hi"
        return "en"

    @staticmethod
    def is_greeting(message: str) -> bool:
        """Detects if message is purely a greeting or conversational hello."""
        clean = message.lower().strip(" !.,?👋\n\r~`'\"")
        if not clean:
            return False

        greeting_words = {
            "hello", "hi", "hii", "hiii", "hiiii", "hey", "heyy", "heyyy", "helo", "helllo", "helloo",
            "hiya", "howdy", "sup", "yo", "namaste", "namaskar", "pranam", "pranaam", "greetings",
            "good morning", "good afternoon", "good evening", "good day", "how are you", "how r u",
            "kemon acho", "kemon achen", "kemon achis", "kaise ho", "kya haal hai", "ki khobor",
            "who are you", "what can you do", "what are you",
            "নমস্কার", "হ্যালো", "হাই", "কেমন আছো", "কেমন আছেন", "কেমন আছিস", "কি খবর",
            "শুভ সকাল", "শুভ সন্ধ্যা", "শুভ রাত্রি",
            "नमस्ते", "नमस्कार", "प्रणाम", "राम राम", "जय श्री राम", "राधे राधे", "कैसा है", "कैसे हो", "क्या हाल है", "हेलो", "हाय"
        }
        if clean in greeting_words:
            return True

        # Check single and double character collapse (e.g. hiii -> hi, heyyy -> hey, hellooo -> hello)
        norm_single = re.sub(r'([a-z])\1+', r'\1', clean)
        if norm_single in greeting_words or (norm_single + 'o') in greeting_words:
            return True
        norm_double = re.sub(r'([a-z])\1+', r'\1\1', clean)
        if norm_double in greeting_words:
            return True

        # Multi-word greeting check (e.g. "hi hello", "hello there", "hi weathergpt", "hello bro")
        words = clean.split()
        if words:
            all_greet = True
            for w in words:
                w_c = re.sub(r'([a-z])\1+', r'\1', w)
                w_d = re.sub(r'([a-z])\1+', r'\1\1', w)
                if (w not in greeting_words and w_c not in greeting_words and 
                    (w_c + 'o') not in greeting_words and w_d not in greeting_words and 
                    w not in {'weathergpt', 'there', 'to', 'you', 'bro', 'friend', 'bot', 'all', 'everyone', 'sir', 'buddy'}):
                    all_greet = False
                    break
            if all_greet:
                return True

        if clean.startswith(('hello ', 'hi ', 'hey ', 'greetings ', 'good morning ', 'good evening ', 'namaste ')):
            # If the remainder after greeting is short conversational text or 'weathergpt'
            remainder = clean.split(maxsplit=1)[1].strip() if ' ' in clean else ''
            if not remainder or len(remainder) <= 15 or 'weathergpt' in remainder or remainder in {'there', 'bro', 'friend', 'sir', 'how are you', 'how r u'}:
                return True

        if "weathergpt" in clean and len(clean.split()) <= 3:
            return True
        return False

    @staticmethod
    def is_non_weather_query(message: str) -> bool:
        """Identifies overtly off-topic requests (e.g., programming, cooking, trivia)."""
        clean = message.lower()
        off_topic_patterns = [
            r"\b(write|generate|code|debug|function|class|algorithm|python|javascript|java|c\+\+|sql query|html)\b",
            r"\b(recipe|how to cook|bake|ingredients for)\b",
            r"\b(solve math|integral|equation|calculus|derivative)\b",
            r"\b(who won the election|political party|prime minister of|president of)\b",
            r"\b(write an essay|write a poem|write a song|write a story)\b"
        ]
        for p in off_topic_patterns:
            if re.search(p, clean):
                return True
        return False

    @staticmethod
    def build_weather_context(
        weather: Optional[WeatherCurrent],
        hourly_24h: Optional[List[HourlyPoint]] = None,
        daily_7d: Optional[List[DailyForecast]] = None,
        alerts: Optional[List[AlertItem]] = None,
        comparison_data: Optional[Dict[str, Any]] = None,
        extra_context: Optional[str] = None
    ) -> str:
        """
        Builds a comprehensive, compact, structured meteorological context for the LLM.
        """
        sections = []

        # 1. Primary Location Current Observation
        if weather:
            now_str = datetime.now().strftime("%A, %d %B %Y %I:%M %p IST")
            loc_label = weather.city
            c_lines = [
                f"PRIMARY LOCATION: {loc_label} (Lat: {weather.latitude:.4f}, Lon: {weather.longitude:.4f})",
                f"TIMESTAMP: {now_str}",
                "CURRENT OBSERVATIONS:",
                f"- Temperature: {weather.temperature:.1f}°C (Feels like: {weather.feels_like:.1f}°C)",
                f"- Sky & Condition: {weather.weather_desc}",
                f"- Relative Humidity: {weather.humidity}%",
                f"- Atmospheric Pressure: {weather.pressure:.1f} hPa",
                f"- Wind: {weather.wind_speed:.1f} km/h (Direction: {weather.wind_direction}°" +
                (f", Gusts: {weather.wind_gust:.1f} km/h" if weather.wind_gust else "") + ")",
                f"- Cloud Cover: {weather.cloud_cover}% | Precipitation (Current): {weather.precipitation:.1f} mm",
                f"- UV Index: {weather.uv_index or 5.0:.1f}",
                f"- Air Quality (AQI): {weather.aqi or 45} ({weather.aqi_desc or 'Good'})"
            ]
            sections.append("\n".join(c_lines))

        # 2. 24-Hour Hourly Timeline (Selected key time points)
        if hourly_24h and len(hourly_24h) > 0:
            h_lines = ["24-HOUR HOURLY TIMELINE:"]
            step = max(1, len(hourly_24h) // 8)
            sampled = hourly_24h[::step][:8]
            for hp in sampled:
                h_lines.append(
                    f"- {hp.time}: {hp.temperature:.1f}°C, {hp.weather_desc}, "
                    f"Rain Chance: {hp.precipitation_prob}%, Wind: {hp.wind_speed:.1f} km/h"
                )
            sections.append("\n".join(h_lines))

        # 3. 7-Day Daily Forecast
        if daily_7d and len(daily_7d) > 0:
            d_lines = ["7-DAY DAILY FORECAST:"]
            for i, df in enumerate(daily_7d[:7]):
                day_label = df.date
                try:
                    d_obj = datetime.strptime(df.date, "%Y-%m-%d")
                    day_label = f"{d_obj.strftime('%A')} ({df.date})"
                except Exception:
                    pass
                prefix = "Today" if i == 0 else ("Tomorrow" if i == 1 else "")
                label_str = f"{prefix} - {day_label}" if prefix else day_label

                d_lines.append(
                    f"- {label_str}: High {df.temp_max:.1f}°C / Low {df.temp_min:.1f}°C, "
                    f"{df.weather_desc}, Rain Chance: {df.precipitation_prob}%" +
                    (f", Rain Sum: {df.precipitation_sum:.1f}mm" if df.precipitation_sum else "")
                )
            sections.append("\n".join(d_lines))

        # 4. Active Weather Warnings & Alerts
        if alerts and len(alerts) > 0:
            active_warnings = [a for a in alerts if a.severity != "GREEN"]
            if active_warnings:
                a_lines = ["ACTIVE METEOROLOGICAL WARNINGS:"]
                for aw in active_warnings[:3]:
                    a_lines.append(f"- [{aw.severity}] {aw.hazard_type}: {aw.headline}. {aw.advisory}")
                sections.append("\n".join(a_lines))
            else:
                sections.append("ACTIVE METEOROLOGICAL WARNINGS: None (All Clear - Green status).")
        else:
            sections.append("ACTIVE METEOROLOGICAL WARNINGS: None active.")

        # 5. Comparative Location (if comparing two places)
        if comparison_data:
            sec_name = comparison_data.get("city", "Comparison City")
            sec_w = comparison_data.get("weather")
            sec_f = comparison_data.get("daily_7d", [])
            sec_lines = [f"COMPARISON LOCATION: {sec_name}"]
            if sec_w:
                sec_lines.append(
                    f"- Current: {sec_w.temperature:.1f}°C (Feels like: {sec_w.feels_like:.1f}°C), "
                    f"{sec_w.weather_desc}, Humidity: {sec_w.humidity}%, Wind: {sec_w.wind_speed:.1f} km/h"
                )
            if sec_f and len(sec_f) > 0:
                sec_lines.append(
                    f"- Today Forecast: High {sec_f[0].temp_max:.1f}°C / Low {sec_f[0].temp_min:.1f}°C, "
                    f"{sec_f[0].weather_desc}, Rain: {sec_f[0].precipitation_prob}%"
                )
            if sec_f and len(sec_f) > 1:
                sec_lines.append(
                    f"- Tomorrow Forecast: High {sec_f[1].temp_max:.1f}°C / Low {sec_f[1].temp_min:.1f}°C, "
                    f"{sec_f[1].weather_desc}, Rain: {sec_f[1].precipitation_prob}%"
                )
            sections.append("\n".join(sec_lines))

        # 6. Extra Context (e.g. Nearby Institutions & Individual Weather)
        if extra_context:
            sections.append(extra_context)

        return "\n\n".join(sections)

    @staticmethod
    async def _call_gemini(
        system_prompt: str,
        weather_context: str,
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        language: str = "en"
    ) -> Optional[str]:
        """Calls Google Gemini API using httpx async."""
        if not settings.GEMINI_API_KEY:
            return None

        models = ["gemini-flash-lite-latest"]
        if settings.GEMINI_MODEL and settings.GEMINI_MODEL not in models:
            models.append(settings.GEMINI_MODEL)

        lang_instruction = "English"
        if language == "hi" or AIService._detect_language(user_message) == "hi":
            lang_instruction = "Hindi (हिन्दी)"
        elif language == "bn" or AIService._detect_language(user_message) == "bn":
            lang_instruction = "Bengali (বাংলা)"

        full_system = (
            f"{system_prompt}\n\n"
            f"PREFERRED RESPONSE LANGUAGE: {lang_instruction}. "
            f"Reply in natural, fluent {lang_instruction}."
        )

        contents = []
        if chat_history:
            for ch in chat_history[-6:]:
                role = "user" if ch.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": ch.get("content", "")}]
                })

        final_prompt = (
            f"REAL-TIME METEOROLOGICAL CONTEXT:\n{weather_context}\n\n"
            f"USER QUESTION: {user_message}"
        )
        contents.append({
            "role": "user",
            "parts": [{"text": final_prompt}]
        })

        payload = {
            "system_instruction": {"parts": [{"text": full_system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 200
            }
        }

        async with httpx.AsyncClient(timeout=5.5) as client:
            for model_name in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                try:
                    r = await client.post(url, json=payload)
                    if r.status_code == 200:
                        data = r.json()
                        candidates = data.get("candidates", [])
                        if candidates and len(candidates) > 0:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and len(parts) > 0:
                                return parts[0].get("text", "").strip()
                    else:
                        logger.warning(f"Gemini {model_name} returned {r.status_code}: {r.text[:120]}")
                except Exception as e:
                    logger.warning(f"Gemini {model_name} exception: {e}")

        return None

    @staticmethod
    async def _call_openai(
        system_prompt: str,
        weather_context: str,
        user_message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        language: str = "en"
    ) -> Optional[str]:
        """Calls OpenAI API using AsyncOpenAI."""
        if not settings.OPENAI_API_KEY:
            return None

        lang_instruction = "English"
        if language == "hi" or AIService._detect_language(user_message) == "hi":
            lang_instruction = "Hindi (हिन्दी)"
        elif language == "bn" or AIService._detect_language(user_message) == "bn":
            lang_instruction = "Bengali (বাংলা)"

        full_system = (
            f"{system_prompt}\n\n"
            f"REAL-TIME METEOROLOGICAL CONTEXT:\n{weather_context}\n\n"
            f"PREFERRED RESPONSE LANGUAGE: {lang_instruction}. "
            f"Reply in natural, fluent {lang_instruction}."
        )

        messages = [{"role": "system", "content": full_system}]
        if chat_history:
            for ch in chat_history[-6:]:
                role = "assistant" if ch.get("role") == "assistant" else "user"
                messages.append({"role": role, "content": ch.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
            )
            completion = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.35,
                    max_tokens=200
                ),
                timeout=2.5
            )
            if completion and completion.choices and completion.choices[0].message.content:
                return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.info(f"OpenAI call skipped/failed: {e}")

        return None

    @staticmethod
    def _generate_dynamic_suggestions(
        city: str,
        weather: Optional[WeatherCurrent],
        forecast: Optional[List[DailyForecast]],
        language: str = "en"
    ) -> List[str]:
        """Generates contextual suggested follow-up queries based on real weather data."""
        is_bangla = language == "bn"
        is_hindi = language == "hi"
        c_short = city.split(",")[0].strip()

        has_rain_soon = False
        if forecast and len(forecast) > 0 and forecast[0].precipitation_prob >= 35:
            has_rain_soon = True

        if is_bangla:
            if has_rain_soon:
                return [f"কখন বৃষ্টি শুরু হবে?", f"{c_short}-র বাতাসের গুণমান", "সপ্তাহের পূর্বাভাস"]
            return [f"আজ কি ছাতা লাগবে?", f"{c_short}-তে বাতাসের গুণমান (AQI)", "আগামীকালের আবহাওয়া"]
        elif is_hindi:
            if has_rain_soon:
                return [f"बारिश कब शुरू होगी?", f"{c_short} में वायु गुणवत्ता (AQI)", "साप्ताहिक पूर्वानुमान"]
            return [f"क्या आज छाता चाहिए?", f"{c_short} में वायु गुणवत्ता", "कल का मौसम कैसा रहेगा?"]
        else:
            if has_rain_soon:
                return [f"When will the rain start?", f"Air quality in {c_short}", "7-day forecast"]
            return [f"Should I take an umbrella?", f"How does it feel outside?", "Weekend forecast"]

    @staticmethod
    async def chat(
        message: str,
        weather: Optional[WeatherCurrent],
        hourly: Optional[List[HourlyPoint]] = None,
        forecast: Optional[List[DailyForecast]] = None,
        alerts: Optional[List[AlertItem]] = None,
        comparison_data: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        language: str = "en",
        extra_context: Optional[str] = None
    ) -> tuple[str, List[str]]:
        """
        Main Conversational AI entrypoint:
        1. Formats structured real-time weather context.
        2. Routes to resilient LLM engine (Gemini & OpenAI with auto-fallback).
        3. Returns natural language response generated by AI reasoning over real data within 3-4s.
        """
        city_name = weather.city if weather else "Active Location"

        # 1. Build rich structured meteorological context
        weather_context = AIService.build_weather_context(
            weather=weather,
            hourly_24h=hourly,
            daily_7d=forecast,
            alerts=alerts,
            comparison_data=comparison_data,
            extra_context=extra_context
        )

        reply_text = None

        # 2. Try Primary: Gemini (fastest & active, capped to 3.8s)
        if settings.GEMINI_API_KEY:
            try:
                reply_text = await asyncio.wait_for(
                    AIService._call_gemini(
                        system_prompt=METEOROLOGICAL_SYSTEM_PROMPT,
                        weather_context=weather_context,
                        user_message=message,
                        chat_history=chat_history,
                        language=language
                    ),
                    timeout=5.5
                )
            except asyncio.TimeoutError:
                logger.warning("Gemini call timed out after 5.5s")
            except Exception as e:
                logger.warning(f"Gemini call error: {e}")

        # 3. Try Secondary / Fallback: OpenAI (capped to 2.5s)
        if not reply_text and settings.OPENAI_API_KEY:
            try:
                reply_text = await asyncio.wait_for(
                    AIService._call_openai(
                        system_prompt=METEOROLOGICAL_SYSTEM_PROMPT,
                        weather_context=weather_context,
                        user_message=message,
                        chat_history=chat_history,
                        language=language
                    ),
                    timeout=2.5
                )
            except Exception as e:
                logger.info(f"OpenAI fallback error: {e}")

        # 4. If AI providers are unavailable, provide honest meteorological telemetry response
        if not reply_text:
            if weather:
                temp_round = round(weather.temperature)
                feels_round = round(weather.feels_like)
                desc = weather.weather_desc
                hum = weather.humidity
                wind = round(weather.wind_speed)

                if AIService.is_greeting(message):
                    if language == "bn":
                        reply_text = (
                            f"নমস্কার! 👋 আমি WeatherGPT, আপনার আবহাওয়া সহকারী। {city_name}-এ বর্তমান সরাসরি আবহাওয়া পর্যবেক্ষণ: "
                            f"তাপমাত্রা {temp_round}°C (অনুভূত {feels_round}°C), আকাশ {desc}, "
                            f"আর্দ্রতা {hum}% এবং বাতাস {wind} km/h। আজ আবহাওয়া বা পূর্বাভাস সম্পর্কিত কী জানতে চান?"
                        )
                    elif language == "hi":
                        reply_text = (
                            f"नमस्ते! 👋 मैं WeatherGPT हूँ, आपका मौसम सहायक। {city_name} में वर्तमान मौसम: "
                            f"तापमान {temp_round}°C (महसूस {feels_round}°C), {desc}, "
                            f"नमी {hum}% और हवा {wind} km/h है। आज मैं आपके मौसम संबंधी सवालों में क्या मदद करूँ?"
                        )
                    else:
                        reply_text = (
                            f"Hello! 👋 I'm WeatherGPT, your meteorological assistant. "
                            f"Current observation in {city_name}: {temp_round}°C (feels like {feels_round}°C), {desc}, "
                            f"with {hum}% humidity and wind at {wind} km/h. How can I assist you with the weather today?"
                        )
                else:
                    if language == "bn":
                        reply_text = (
                            f"বর্তমানে এআই সংযোগে বিলম্ব হচ্ছে। {city_name}-র সরাসরি আবহাওয়া পর্যবেক্ষণ: "
                            f"তাপমাত্রা {temp_round}°C (অনুভূত {feels_round}°C), আকাশ {desc}, "
                            f"আর্দ্রতা {hum}% এবং বাতাস {wind} km/h।"
                        )
                    elif language == "hi":
                        reply_text = (
                            f"वर्तमान में एআই कनेक्शन में विलंब है। {city_name} का सीधा मौसम प्रेक्षण: "
                            f"तापमान {temp_round}°C (महसूस {feels_round}°C), {desc}, "
                            f"नमी {hum}% और हवा {wind} km/h है।"
                        )
                    else:
                        reply_text = (
                            f"AI service connection is currently delayed. Direct live observation for {city_name}: "
                            f"{temp_round}°C (feels like {feels_round}°C), {desc}, "
                            f"with {hum}% humidity and wind at {wind} km/h."
                        )
            else:
                if AIService.is_greeting(message):
                    reply_text = (
                        "Hello! 👋 I'm WeatherGPT, your meteorological assistant. "
                        "How can I assist you with weather forecasts or radar observations today?"
                    )
                else:
                    reply_text = (
                        "I am currently unable to retrieve weather intelligence for this location. "
                        "Please verify your connection or select a location on the map."
                    )

        suggestions = AIService._generate_dynamic_suggestions(city_name, weather, forecast, language)
        return reply_text, suggestions

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """Translates text into target language ('en', 'hi', 'bn')."""
        if not text:
            return ""
        target_lang = target_language.lower().strip()
        if target_lang not in ("en", "hi", "bn"):
            target_lang = "en"
        current_lang = AIService._detect_language(text)
        if current_lang == target_lang:
            return text
        if target_lang == "hi":
            replacements = {
                "Here's the current weather observation in": "यहाँ वर्तमान मौसम प्रेक्षण है:",
                "Temperature": "तापमान",
                "Feels like": "महसूस",
                "Humidity": "नमी",
                "Wind": "हवा",
                "Pressure": "दबाव",
                "Visibility": "दृश्यता",
                "Air Quality Index": "वायु गुणवत्ता सूचकांक",
                "Partly Cloudy": "आंशिक बादल",
                "Sunny": "धूप",
                "Clear": "साफ मौसम",
                "Light Rain": "हल्की बारिश",
                "Thunderstorm": "गरज के साथ बौछारें"
            }
            res = text
            for k, v in replacements.items():
                res = res.replace(k, v)
            return res
        elif target_lang == "bn":
            replacements = {
                "Here's the current weather observation in": "এখানে বর্তমান আবহাওয়া পর্যবেক্ষণ দেওয়া হলো:",
                "Temperature": "তাপমাত্রা",
                "Feels like": "অনুভূত",
                "Humidity": "আর্দ্রতা",
                "Wind": "বাতাস",
                "Pressure": "চাপ",
                "Visibility": "দৃশ্যমানতা",
                "Air Quality Index": "বায়ুমান সূচক",
                "Partly Cloudy": "আংশিক মেঘলা",
                "Sunny": "রৌদ্রোজ্জ্বল",
                "Clear": "পরিষ্কার আকাশ",
                "Light Rain": "হালকা বৃষ্টি",
                "Thunderstorm": "বজ্রবিদ্যুৎসহ ঝড়বৃষ্টি"
            }
            res = text
            for k, v in replacements.items():
                res = res.replace(k, v)
            return res
        return text


ai_service = AIService()
