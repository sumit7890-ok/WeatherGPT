/**
 * WeatherGPT - Weather UI Module
 * Tailored for modern Tailwind CSS 3-column layout
 */

const ThermalScale = {
  getUnit() {
    try {
      return localStorage.getItem("weathergpt_thermal_scale") || "C";
    } catch {
      return "C";
    }
  },

  setUnit(unit) {
    try {
      localStorage.setItem("weathergpt_thermal_scale", unit);
    } catch {}
  },

  convert(celsius) {
    if (celsius == null || isNaN(celsius)) return "--";
    const c = parseFloat(celsius);
    const unit = this.getUnit();
    if (unit === "F") {
      // Exact formula: F = (C * 9/5) + 32
      return Math.round((c * 9 / 5) + 32);
    } else if (unit === "K") {
      // Exact formula: K = C + 273.15
      return Math.round(c + 273.15);
    }
    return Math.round(c);
  },

  unitSymbol() {
    const unit = this.getUnit();
    if (unit === "F") return "°F";
    if (unit === "K") return "K";
    return "°C";
  },

  format(celsius, withDegree = true) {
    if (celsius == null || isNaN(celsius)) return "--";
    const val = this.convert(celsius);
    const sym = this.unitSymbol();
    if (!withDegree) {
      return sym === "K" ? `${val}K` : `${val}°`;
    }
    return sym === "K" ? `${val} K` : `${val}${sym}`;
  }
};

const WeatherUI = {
  lastWeather: null,
  lastHourly: null,
  lastDaily: null,

  refreshThermalDisplays() {
    if (this.lastWeather) this.renderHero(this.lastWeather);
    if (this.lastHourly) this.renderHourly(this.lastHourly);
    if (this.lastDaily) this.renderDaily(this.lastDaily);
  },

  renderHero(weather) {
    if (!weather) return;
    this.lastWeather = weather;

    let cityName = weather.city || "Active Location";

    // Prevent coordinates or generic placeholders from leaking into cityName display
    const isCoordPattern = (str) => {
      if (!str) return true;
      const s = String(str).toLowerCase().trim();
      return s.includes("location (") || s.includes("coordinates (") || s.includes("coords (") || s === "selected location" || s === "selected place" || /^-?\d+(\.\d+)?°?\s*[nsew]?,?\s*-?\d+(\.\d+)?°?\s*[nsew]?/i.test(s);
    };

    const activeLoc = window.WeatherApp?.activeLocation;
    const granularName = activeLoc ? (activeLoc.sublocality || activeLoc.neighborhood || activeLoc.locality || activeLoc.name || activeLoc.city) : null;
    if (granularName && !isCoordPattern(granularName)) {
      cityName = granularName;
    } else if (isCoordPattern(cityName)) {
      cityName = (activeLoc?.name && !isCoordPattern(activeLoc.name)) ? activeLoc.name : "Kolkata";
    }

    const fullLabel = cityName;

    // 1. Navbar location label (No extra pin emoji; icon is already in the parent button)
    const navLabel = document.getElementById("nav-city-label");
    if (navLabel) {
      if (activeLoc && activeLoc.isCurrentLocation) {
        navLabel.innerHTML = `<span class="text-emerald-500 font-semibold">Current Location:</span> ${cityName}`;
      } else {
        navLabel.textContent = fullLabel;
      }
    }

    // 2. Right card city name next to Live clock (User Request 4: Real place name, never Selected Location)
    const cardCity = document.getElementById("card-city-name");
    if (cardCity) cardCity.textContent = cityName.split(",")[0].trim();

    // 3. Search input beside search icon (User Request 3: Real place name)
    const globalSearch = document.getElementById("global-search");
    if (globalSearch && (!globalSearch.value || isCoordPattern(globalSearch.value))) {
      globalSearch.value = cityName.split(",")[0].trim();
    }

    // 4. Update small coordinates tab at bottom of current weather platelet
    const lat = weather.latitude != null ? weather.latitude : (window.WeatherApp?.activeLocation?.latitude);
    const lon = weather.longitude != null ? weather.longitude : (window.WeatherApp?.activeLocation?.longitude);
    let coordFormatted = "";
    if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
      const latDir = lat >= 0 ? "N" : "S";
      const lonDir = lon >= 0 ? "E" : "W";
      coordFormatted = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
    }

    const elCoords = document.getElementById("card-coordinates-val");
    if (elCoords && coordFormatted) {
      elCoords.textContent = coordFormatted;
    }

    // 5. Update map bottom black box with coordinates (User Request 2: Longitude and Latitude)
    const sideMapCoords = document.getElementById("sidebar-map-coords");
    if (sideMapCoords && coordFormatted) {
      sideMapCoords.textContent = coordFormatted;
    }
    const fsMapCoords = document.getElementById("fs-coords-hud");
    if (fsMapCoords && coordFormatted) {
      fsMapCoords.textContent = coordFormatted;
    }

    // 3. Right card temperatures
    const tempNum = ThermalScale.convert(weather.temperature);
    const feelsNum = ThermalScale.convert(weather.feels_like);
    const sym = ThermalScale.unitSymbol();

    const elTemp = document.getElementById("card-temp-num") || document.getElementById("card-temp");
    if (elTemp) elTemp.textContent = tempNum;

    const elTempUnit = document.getElementById("card-temp-unit");
    if (elTempUnit) elTempUnit.textContent = sym === "K" ? " K" : sym;

    const elFeels = document.getElementById("card-feels-num") || document.getElementById("card-feels");
    if (elFeels) elFeels.textContent = feelsNum;

    const elFeelsUnit = document.getElementById("card-feels-unit");
    if (elFeelsUnit) elFeelsUnit.textContent = sym === "K" ? " K" : sym;

    const elIcon = document.getElementById("card-weather-emoji") || document.getElementById("card-weather-icon");
    if (elIcon) elIcon.textContent = weather.weather_icon || "☀️";

    const elCond = document.getElementById("card-cond-desc") || document.getElementById("card-condition");
    if (elCond) elCond.textContent = weather.weather_desc || "Clear Sky";

    // 4. Update metrics grid (including UV Index)
    this.renderMetrics(weather);
  },

  renderMetrics(weather) {
    if (!weather) return;

    // Humidity
    const elHum = document.getElementById("card-humidity-val") || document.getElementById("card-humidity");
    if (elHum) elHum.textContent = `${weather.humidity}%`;

    // Wind
    const elWind = document.getElementById("card-wind-val") || document.getElementById("card-wind");
    if (elWind) elWind.textContent = `${Math.round(weather.wind_speed)} km/h`;

    // Pressure
    const elPress = document.getElementById("card-pressure-val") || document.getElementById("card-pressure");
    if (elPress) elPress.textContent = `${Math.round(weather.pressure)} hPa`;

    // Visibility
    const elVis = document.getElementById("card-visibility-val") || document.getElementById("card-visibility");
    let vis = "10 km";
    if (weather.weather_code >= 45 && weather.weather_code <= 48) vis = "2 km";
    else if (weather.weather_code >= 51 && weather.weather_code <= 67) vis = "4 km";
    else if (weather.weather_code >= 80) vis = "8 km";
    if (elVis) elVis.textContent = vis;

    // UV Index
    const uvNum = weather.uv_index !== undefined && weather.uv_index !== null ? Math.round(weather.uv_index * 10) / 10 : 5.0;
    const elUv = document.getElementById("card-uv-val");
    if (elUv) {
      let uvDesc = "Moderate";
      if (uvNum < 3) uvDesc = "Low";
      else if (uvNum >= 6 && uvNum < 8) uvDesc = "High";
      else if (uvNum >= 8 && uvNum < 11) uvDesc = "Very High";
      else if (uvNum >= 11) uvDesc = "Extreme";
      elUv.textContent = `${uvNum} (${uvDesc})`;
    }

    // AQI Pill
    const aqiNum = weather.aqi || 48;
    const elAqi = document.getElementById("card-aqi-pill") || document.getElementById("card-aqi");
    if (elAqi) {
      let aqiText = `Good (${aqiNum})`;
      let aqiClass = "font-bold text-emerald-700 bg-emerald-200/60 px-2 py-0.5 rounded-md";
      if (aqiNum > 50 && aqiNum <= 100) {
        aqiText = `Moderate (${aqiNum})`;
        aqiClass = "font-bold text-amber-700 bg-amber-200/60 px-2 py-0.5 rounded-md";
      } else if (aqiNum > 100 && aqiNum <= 200) {
        aqiText = `Sensitive (${aqiNum})`;
        aqiClass = "font-bold text-orange-700 bg-orange-200/60 px-2 py-0.5 rounded-md";
      } else if (aqiNum > 200) {
        aqiText = `Poor (${aqiNum})`;
        aqiClass = "font-bold text-rose-700 bg-rose-200/60 px-2 py-0.5 rounded-md";
      }
      elAqi.className = aqiClass;
      elAqi.textContent = aqiText;
    }
  },

  renderHourly(hourlyList) {
    this.lastHourly = hourlyList;
    const container = document.getElementById("hourly-forecast-strip");
    if (!container) return;
    if (!hourlyList || hourlyList.length === 0) {
      container.innerHTML = '<span class="text-xs text-slate-400 italic">No hourly telemetry available</span>';
      return;
    }

    container.innerHTML = "";
    
    // Display 8 intervals across next 24 hours
    const points = hourlyList.slice(0, 8);
    points.forEach((item, idx) => {
      let timeStr = item.time || "--:--";
      if (idx === 0) {
        timeStr = "Now";
      } else if (timeStr.includes("T")) {
        timeStr = timeStr.split("T")[1].slice(0, 5);
      }

      const temp = ThermalScale.convert(item.temperature);
      const sym = ThermalScale.unitSymbol();
      const tempStr = sym === "K" ? `${temp}K` : `${temp}°`;
      const icon = item.weather_icon || (item.precipitation_prob > 40 ? "🌧️" : "🌤️");
      const rain = item.precipitation_prob !== undefined && item.precipitation_prob !== null ? item.precipitation_prob : 0;
      const wind = item.wind_speed !== undefined && item.wind_speed !== null ? Math.round(item.wind_speed) : 0;

      const card = document.createElement("div");
      card.className = "flex flex-col items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100 min-w-[62px] shrink-0 text-center hover:bg-blue-50/50 hover:border-blue-200 transition-colors shadow-xs";
      card.innerHTML = `
        <span class="text-[10px] font-semibold text-slate-500">${timeStr}</span>
        <span class="text-xl my-1">${icon}</span>
        <span class="text-xs font-bold text-slate-800">${tempStr}</span>
        <span class="text-[9px] ${rain >= 30 ? 'text-blue-600 font-bold' : 'text-slate-400'} mt-0.5">💧${rain}%</span>
        <span class="text-[8px] text-slate-400 mt-0.5 font-mono">${wind}k</span>
      `;
      container.appendChild(card);
    });
  },

  renderDaily(dailyList) {
    this.lastDaily = dailyList;
    const container = document.getElementById("right-forecast-list");
    if (!container || !dailyList || dailyList.length === 0) return;

    container.innerHTML = "";
    
    // Exactly 5 days: Today, Tomorrow, Day 3, Day 4, Day 5
    const fiveDays = dailyList.slice(0, 5);
    const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

    fiveDays.forEach((d, idx) => {
      let label = d.date;
      if (idx === 0) {
        label = "Today";
      } else if (idx === 1) {
        label = "Tomorrow";
      } else if (d.date && d.date.includes("-")) {
        try {
          const parsed = new Date(d.date + "T00:00:00");
          if (!isNaN(parsed.getDay())) {
            label = dayNames[parsed.getDay()];
          }
        } catch {
          label = d.date;
        }
      }

      const row = document.createElement("div");
      row.className = "flex items-center justify-between py-2 border-b border-slate-100 last:border-0 text-xs";

      const maxT = ThermalScale.convert(d.temp_max);
      const minT = ThermalScale.convert(d.temp_min);
      const sym = ThermalScale.unitSymbol();
      const deg = sym === "K" ? "K" : "°";
      const rain = d.precipitation_prob !== undefined && d.precipitation_prob !== null ? d.precipitation_prob : 0;
      const rainColor = rain >= 40 ? "text-blue-600 font-bold" : "text-slate-400 font-medium";

      row.innerHTML = `
        <div class="flex items-center gap-2 min-w-[85px]">
          <span class="text-base">${d.weather_icon || "☀️"}</span>
          <div>
            <strong class="text-slate-800 font-semibold block text-[11px] leading-tight">${label}</strong>
            <span class="text-[10px] text-slate-400 block truncate max-w-[80px]" title="${d.weather_desc}">${d.weather_desc}</span>
          </div>
        </div>
        <div class="text-center font-bold text-slate-800 text-[11px]">
          ${maxT}${deg} / <span class="text-slate-500 font-medium">${minT}${deg}</span>
        </div>
        <div class="${rainColor} text-[11px] text-right min-w-[55px]">
          💧 ${rain}%
        </div>
      `;
      container.appendChild(row);
    });

    // Also update forecast modal if present
    const modalContent = document.getElementById("modal-forecast-content");
    if (modalContent) {
      modalContent.innerHTML = "";
      fiveDays.forEach((d, idx) => {
        let label = idx === 0 ? "Today" : (idx === 1 ? "Tomorrow" : d.date);
        const item = document.createElement("div");
        item.className = "p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs";
        item.innerHTML = `
          <div class="flex items-center gap-3">
            <span class="text-3xl">${d.weather_icon || "☀️"}</span>
            <div>
              <strong class="text-slate-900 font-bold text-sm">${label}</strong>
              <p class="text-slate-500 mt-0.5">${d.weather_desc}</p>
            </div>
          </div>
          <div class="text-right">
            <span class="font-bold text-slate-900 text-sm">${ThermalScale.format(d.temp_max)}</span>
            <span class="text-slate-500 font-medium"> / ${ThermalScale.format(d.temp_min)}</span>
            <p class="text-blue-600 font-semibold mt-0.5">💧 Rain ${d.precipitation_prob || 0}%</p>
          </div>
        `;
        modalContent.appendChild(item);
      });
    }
  }
};

WeatherUI.renderHourlyForecast = WeatherUI.renderHourly;
WeatherUI.renderDailyForecast = WeatherUI.renderDaily;

window.WeatherUI = WeatherUI;
window.ThermalScale = ThermalScale;
