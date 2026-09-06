/**
 * WeatherGPT - Core Application Controller
 * Seamlessly integrates:
 * 1. Clean startup (main window shows welcome hero, history stored in Recent Chats)
 * 2. High-precision Markdown formatting (bold, lists, headings, zero raw asterisks/symbols)
 * 3. 3-Language Dropdown & Automatic 2-3s FastAPI Translation (English, Hindi, Bangla)
 * 4. Google Maps & MapLibre real rotation & zoom map
 * 5. Dynamic IMD Weather Alerts & Real-time Observations
 */

// Markdown Formatter with marked.js support and resilient fallback
function formatMarkdown(text) {
  if (!text) return "";

  // 1. If marked.js is available via CDN
  if (typeof marked !== "undefined" && typeof marked.parse === "function") {
    try {
      marked.setOptions({ gfm: true, breaks: true });
      let html = marked.parse(text);
      return html
        .replace(/<h3>/g, '<h3 class="font-bold text-slate-900 text-sm mt-3 mb-1">')
        .replace(/<h4>/g, '<h4 class="font-bold text-slate-800 text-xs mt-2 mb-1">')
        .replace(/<strong>/g, '<strong class="font-bold text-slate-900">')
        .replace(/<ul>/g, '<ul class="list-disc pl-5 space-y-1 my-2 text-slate-700">')
        .replace(/<ol>/g, '<ol class="list-decimal pl-5 space-y-1 my-2 text-slate-700">')
        .replace(/<li>/g, '<li class="text-sm leading-relaxed">');
    } catch (e) {
      console.warn("Marked parse error, using fallback:", e);
    }
  }

  // 2. High-precision Fallback Parser
  let clean = text
    // Strip raw asterisks from headers if already preceded by ###
    .replace(/^###\s*\*\*?(.*?)\*\*?$/gim, '<h3 class="font-bold text-slate-900 text-sm mt-3 mb-1">$1</h3>')
    .replace(/^####\s*\*\*?(.*?)\*\*?$/gim, '<h4 class="font-bold text-slate-800 text-xs mt-2 mb-1">$1</h4>')
    // Standard headings
    .replace(/^###\s+(.*$)/gim, '<h3 class="font-bold text-slate-900 text-sm mt-3 mb-1">$1</h3>')
    .replace(/^####\s+(.*$)/gim, '<h4 class="font-bold text-slate-800 text-xs mt-2 mb-1">$1</h4>')
    // Bold: **text**
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>')
    // Italic: *text*
    .replace(/\*([^\*\n]+)\*/g, '<em class="italic text-slate-700">$1</em>')
    // Bullet lists: - item or * item
    .replace(/^\s*[-*]\s+(.*$)/gim, '<li class="ml-4 list-disc text-sm text-slate-700 leading-relaxed">$1</li>')
    // Numbered lists: 1. item
    .replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="ml-4 list-decimal text-sm text-slate-700 leading-relaxed">$2</li>')
    // Replace double dashes or raw symbols
    .replace(/--+/g, '—')
    // Paragraph breaks
    .replace(/\n\n/g, '<div class="h-2"></div>')
    .replace(/\n/g, '<br>');

  return clean;
}

// Resilient API Fetch Helper with auto-retry and multi-URL fallback
async function apiFetch(endpoint, options = {}, retries = 2) {
  const isHttp = window.location.protocol === "http:" || window.location.protocol === "https:";
  const urlsToTry = [];
  if (isHttp && window.location.origin) {
    urlsToTry.push(endpoint);
  }
  urlsToTry.push(`http://127.0.0.1:8000${endpoint}`);
  urlsToTry.push(`http://localhost:8000${endpoint}`);

  let lastError = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    for (const url of urlsToTry) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 25000);
        let signal = controller.signal;
        if (options.signal) {
          if (options.signal.aborted) {
            clearTimeout(timeoutId);
            throw new DOMException("The user aborted a request.", "AbortError");
          }
          if (typeof AbortSignal !== "undefined" && AbortSignal.any) {
            signal = AbortSignal.any([options.signal, controller.signal]);
          } else {
            options.signal.addEventListener("abort", () => controller.abort(), { once: true });
          }
        }
        const res = await fetch(url, { ...options, signal });
        clearTimeout(timeoutId);
        if (res && res.ok) return res;
      } catch (err) {
        if (err.name === "AbortError" && options.signal && options.signal.aborted) {
          throw err;
        }
        lastError = err;
      }
    }
    if (attempt < retries) {
      await new Promise(r => setTimeout(r, 600));
    }
  }
  throw lastError || new Error("Failed to connect to backend server");
}

// Complete Multilingual UI Dictionary (English, Hindi, Bangla)
const UI_TRANSLATIONS = {
  en: {
    nav_chat: "Chat",
    nav_drought: "Drought & Agro Watch",
    nav_drought_badge: "IMD Aridity",
    nav_climate_badge: "ENSO / IOD",
    nav_alerts: "Alerts & Warnings",
    nav_climate: "Climate Insights",
    nav_disaster: "Disaster Info",
    nav_saved: "Saved Locations",
    nav_help: "Help & Support",
    brand_sub: "Ministry of Earth Sciences • IMD",
    new_chat: "New Chat",
    recent_chats: "Recent Chats",
    search_placeholder: "Search location, radar layer or weather question...",
    welcome_title: 'Hello! I\'m <span class="text-blue-600">WeatherGPT</span> 👋',
    welcome_sub: "Ask me anything about weather, forecasts, satellite bulletins, alerts, or climate patterns.",
    prompt_pills: [
      { text: "<span>🌦</span> Weather in my location", prompt: "What is the current weather observation in my location?" },
      { text: "<span>🌧</span> Rain forecast this weekend", prompt: "Will it rain this weekend? Show precipitation forecast." },
      { text: "<span>🌀</span> Cyclone alerts in India", prompt: "Are there any active cyclone alerts or squally wind warnings along Indian coasts?" },
      { text: "<span>🌡</span> Temperature trend this week", prompt: "Show 7-day temperature trends and heatwave outlook." }
    ],
    chat_placeholder: "Ask anything about weather, satellite bulletins, radar forecasts...",
    send_btn: "Send",
    disclaimer: "WeatherGPT integrates IMD synoptic datasets, Numerical Weather Prediction (NWP) models & OpenAI. Verify disaster alerts with local authorities.",
    current_weather: "Current Weather",
    feels_like: "Feels like",
    humidity: "Humidity",
    wind: "Wind",
    pressure: "Pressure",
    visibility: "Visibility",
    aqi: "Air Quality (AQI)",
    forecast_heading: "5-Day Forecast",
    hourly_heading: "Hourly Forecast (24h)",
    alerts_heading: "Weather Alerts",
    view_alerts: "View all national alerts",
    toast_converting: "Translating whole tab to English...",
    toast_done: "Whole tab translated to English!"
  },
  hi: {
    nav_chat: "बातचीत",
    nav_drought: "सूखा एवं कृषि निगरानी",
    nav_drought_badge: "IMD सूखा सूचकांक",
    nav_climate_badge: "ENSO / IOD",
    nav_alerts: "चेतावनी व अलर्ट",
    nav_climate: "जलवायु विश्लेषण",
    nav_disaster: "आपदा सूचना",
    nav_saved: "सहेजे गए स्थान",
    nav_help: "सहायता व दिशानिर्देश",
    brand_sub: "पृथ्वी विज्ञान मंत्रालय • भारत मौसम विज्ञान विभाग (IMD)",
    new_chat: "नई बातचीत",
    recent_chats: "हालिया बातचीत",
    search_placeholder: "स्थान, रडार परत या मौसम का प्रश्न खोजें...",
    welcome_title: 'नमस्ते! मैं <span class="text-blue-600">WeatherGPT</span> हूँ 👋',
    welcome_sub: "मौसम, पूर्वानुमान, उपग्रह बुलेटिन, चेतावनी या जलवायु के बारे में कुछ भी पूछें।",
    prompt_pills: [
      { text: "<span>🌦</span> मेरे स्थान का मौसम", prompt: "नई दिल्ली में वर्तमान मौसम की स्थिति क्या है?" },
      { text: "<span>🌧</span> इस सप्ताहांत बारिश का पूर्वानुमान", prompt: "क्या इस सप्ताहांत बारिश होगी? वर्षा का पूर्वानुमान दिखाएं।" },
      { text: "<span>🌀</span> भारत में चक्रवात अलर्ट", prompt: "क्या भारतीय तटों पर कोई सक्रिय चक्रवात चेतावनी या तेज़ हवा का अलर्ट है?" },
      { text: "<span>🌡</span> इस सप्ताह तापमान का रुझान", prompt: "7 दिनों के तापमान का रुझान और हीटवेव का अनुमान दिखाएं।" }
    ],
    chat_placeholder: "मौसम, उपग्रह बुलेटिन, रडार पूर्वानुमान के बारे में कुछ भी पूछें...",
    send_btn: "भेजें",
    disclaimer: "WeatherGPT भारतीय मौसम विभाग (IMD) सिनॉप्टिक डेटा, NWP मॉडल और AI को एकीकृत करता है। आपदा अलर्ट का सत्यापन स्थानीय प्रशासन से करें।",
    current_weather: "वर्तमान मौसम",
    feels_like: "महसूस तापमान",
    humidity: "आर्द्रता",
    wind: "हवा की गति",
    pressure: "वायुमंडलीय दबाव",
    visibility: "दृश्यता",
    aqi: "वायु गुणवत्ता (AQI)",
    forecast_heading: "5-दिवसीय पूर्वानुमान",
    hourly_heading: "प्रति घंटा पूर्वानुमान (24 घंटे)",
    alerts_heading: "मौसम चेतावनियाँ",
    view_alerts: "सभी राष्ट्रीय चेतावनियाँ देखें",
    toast_converting: "सम्पूर्ण पृष्ठ का अनुवाद हिन्दी में हो रहा है...",
    toast_done: "सम्पूर्ण पृष्ठ हिन्दी में रूपान्तरित!"
  },
  bn: {
    nav_chat: "চ্যাট",
    nav_drought: "খরা ও কৃষি পর্যবেক্ষণ",
    nav_drought_badge: "আইএমডি খরা সূচক",
    nav_climate_badge: "ENSO / IOD",
    nav_alerts: "সতর্কতা ও পূর্বাভাস",
    nav_climate: "জলবায়ু বিশ্লেষণ",
    nav_disaster: "দুর্যোগ তথ্য",
    nav_saved: "সংরক্ষিত স্থান",
    nav_help: "সাহায্য ও সমর্থন",
    brand_sub: "ভূবিজ্ঞান মন্ত্রণালয় • ভারত আবহাওয়া বিভাগ (আইএমডি)",
    new_chat: "নতুন চ্যাট",
    recent_chats: "সাম্প্রতিক চ্যাট",
    search_placeholder: "স্থান, রাডার স্তর বা আবহাওয়ার প্রশ্ন খুঁজুন...",
    welcome_title: 'নমস্কার! আমি <span class="text-blue-600">WeatherGPT</span> 👋',
    welcome_sub: "আবহাওয়া, পূর্বাভাস, উপগ্রহ বুলেটিন, সতর্কতা বা জলবায়ু সম্পর্কে যা ইচ্ছা জিজ্ঞাসা করুন।",
    prompt_pills: [
      { text: "<span>🌦</span> আমার অবস্থানের আবহাওয়া", prompt: "নতুন দিল্লিতে বর্তমান আবহাওয়া কেমন?" },
      { text: "<span>🌧</span> এই উইকএন্ডে বৃষ্টির পূর্বাভাস", prompt: "এই উইকএন্ডে কি বৃষ্টি হবে? বৃষ্টির পূর্বাভাস দেখান।" },
      { text: "<span>🌀</span> ভারতে ঘূর্ণিঝড় সতর্কতা", prompt: "ভারতীয় উপকূলে কি কোনো সক্রিয় ঘূর্ণিঝড় বা ঝড়ো বাতাসের সতর্কতা আছে?" },
      { text: "<span>🌡</span> এই সপ্তাহের তাপমাত্রার ধারা", prompt: "৭ দিনের তাপমাত্রার ধারা এবং তাপপ্রবাহের পূর্বাভাস দেখান।" }
    ],
    chat_placeholder: "আবহাওয়া, উপগ্রহ বুলেটিন, রাডার পূর্বাভাস সম্পর্কে কিছু জিজ্ঞাসা করুন...",
    send_btn: "পাঠান",
    disclaimer: "WeatherGPT ভারতীয় আবহাওয়া বিভাগ (আইএমডি) সিনপটিক ডেটাসেট, এনডব্লিউপি মডেল এবং এআই সংযুক্ত করে। দুর্যোগ সতর্কতা স্থানীয় প্রশাসনের সাথে নিশ্চিত করুন।",
    current_weather: "বর্তমান আবহাওয়া",
    feels_like: "অনুভূত তাপমাত্রা",
    humidity: "আর্দ্রতা",
    wind: "বাতাস",
    pressure: "বায়ুচাপ",
    visibility: "দৃশ্যমানতা",
    aqi: "বাতাসের মান (AQI)",
    forecast_heading: "৫ দিনের পূর্বাভাস",
    hourly_heading: "প্রতি ঘণ্টার পূর্বাভাস (২৪ ঘণ্টা)",
    alerts_heading: "আবহাওয়া সতর্কতা",
    view_alerts: "সব জাতীয় সতর্কতা দেখুন",
    toast_converting: "সম্পূর্ণ পাতা বাংলায় রূপান্তর করা হচ্ছে...",
    toast_done: "সম্পূর্ণ পাতা বাংলায় সফলভাবে রূপান্তরিত!"
  }
};

const DEFAULT_APPEARANCE = {
  mode: "light",
  light: {
    preset: "default-light",
    bg: "#F9F9F9",
    fg: "#101010",
    accent: "#007ACC"
  },
  dark: {
    preset: "default-dark",
    bg: "#101010",
    fg: "#CCCCCC",
    accent: "#007ACC"
  }
};

const THEME_PRESETS = {
  light: {
    "default-light": { bg: "#F9F9F9", fg: "#101010", accent: "#007ACC" },
    "sky-blue": { bg: "#F0F8FF", fg: "#0F172A", accent: "#0284C7" },
    "emerald-breeze": { bg: "#F0FDF4", fg: "#064E3B", accent: "#059669" },
    "sunset-amber": { bg: "#FFFBEB", fg: "#78350F", accent: "#D97706" },
    "purple-royal": { bg: "#FAF5FF", fg: "#581C87", accent: "#7C3AED" },
    "high-contrast-light": { bg: "#FFFFFF", fg: "#000000", accent: "#0000FF" }
  },
  dark: {
    "default-dark": { bg: "#101010", fg: "#CCCCCC", accent: "#007ACC" },
    "midnight-blue": { bg: "#0B1329", fg: "#E2E8F0", accent: "#38BDF8" },
    "deep-charcoal": { bg: "#18181B", fg: "#F4F4F5", accent: "#A1A1AA" },
    "emerald-night": { bg: "#022C22", fg: "#E6F4EA", accent: "#10B981" },
    "cyber-purple": { bg: "#1A0B2E", fg: "#F3E8FF", accent: "#A855F7" },
    "oled-black": { bg: "#000000", fg: "#FFFFFF", accent: "#3B82F6" }
  }
};


class WeatherGPTApp {
  constructor() {
    this.sessionId = localStorage.getItem("weathergpt_active_session_id") || this.createNewSessionId();
    try {
      localStorage.setItem("weathergpt_active_session_id", this.sessionId);
    } catch {}
    // Single Source of Truth: Active Location (Normalized Location Model)
    this.activeLocation = {
      name: "Kolkata",
      latitude: 22.5726,
      longitude: 88.3639,
      country: "India",
      state: "West Bengal",
      district: "Kolkata",
      city: "Kolkata",
      locality: "Kolkata",
      sublocality: "",
      neighborhood: "",
      postalCode: "",
      placeId: "",
      formattedAddress: "Kolkata, West Bengal, India",
      timezone: "Asia/Kolkata",
      isCurrentLocation: false
    };
    this.currentLocation = this.activeLocation; // Alias for backward compatibility
    this.currentLanguage = "en";
    this.isListening = false;
    this.speechRecognition = null;
    this.currentUser = this.loadUserProfile();
    this.appearance = this.loadAppearance();
    this.clientSearchCache = new Map();
    this.searchAbortController = null;
    this.isGenerating = false;
    this.chatAbortController = null;
    this.currentTypingId = null;

    this.initElements();
    this.initEvents();
    this.initSpeech();
    this.renderUserProfile();
    this.initMap();
    this.initAppearance();
    this.initThermalScaleUI();
    this.initSupabaseUI();
    this.initLiveClock();
    this.bootstrap();
  }

  initLiveClock() {
    const updateClock = () => {
      const clockEl = document.getElementById("live-clock-time");
      if (clockEl) {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString([], { hour12: false });
      }
    };
    updateClock();
    setInterval(updateClock, 1000);

    // Silent background live telemetry refresh every 30s
    setInterval(async () => {
      if (this.activeLocation && this.activeLocation.latitude != null) {
        try {
          const { latitude, longitude, city } = this.activeLocation;
          const res = await apiFetch(`/api/weather/forecast?lat=${latitude}&lon=${longitude}&city=${encodeURIComponent(city || '')}`);
          if (res && res.ok) {
            const data = await res.json();
            if (data.current) {
              data.current.city = this.activeLocation.name || this.activeLocation.city || data.current.city;
            }
            WeatherUI.renderHero(data.current);
            WeatherUI.renderMetrics(data.current);
            WeatherUI.renderHourlyForecast(data.hourly_24h);
            WeatherUI.renderDailyForecast(data.daily_7d);
          }
        } catch (e) {
          console.debug("Silent background weather refresh error:", e);
        }
      }
    }, 30000);
  }

  loadAppearance() {
    try {
      const raw = localStorage.getItem("weathergpt_appearance");
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          mode: parsed.mode || "light",
          light: { ...DEFAULT_APPEARANCE.light, ...(parsed.light || {}) },
          dark: { ...DEFAULT_APPEARANCE.dark, ...(parsed.dark || {}) }
        };
      }
    } catch (e) {
      console.debug("Error loading appearance:", e);
    }
    const legacy = localStorage.getItem("weathergpt_theme");
    const mode = legacy === "night" ? "dark" : "light";
    return { ...DEFAULT_APPEARANCE, mode };
  }

  saveAppearance() {
    try {
      localStorage.setItem("weathergpt_appearance", JSON.stringify(this.appearance));
      localStorage.setItem("weathergpt_theme", this.isDarkMode() ? "night" : "light");
    } catch (e) {
      console.debug("Error saving appearance:", e);
    }
  }

  hexToRgb(hex) {
    if (!hex) return { r: 0, g: 122, b: 204 };
    let c = String(hex).replace("#", "").trim();
    if (c.length === 3) c = c.split("").map(x => x + x).join("");
    const num = parseInt(c, 16);
    if (isNaN(num)) return { r: 0, g: 122, b: 204 };
    return {
      r: (num >> 16) & 255,
      g: (num >> 8) & 255,
      b: num & 255
    };
  }

  isDarkMode() {
    if (this.appearance.mode === "system") {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return this.appearance.mode === "dark";
  }

  initAppearance() {
    if (window.matchMedia) {
      try {
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
          if (this.appearance.mode === "system") {
            this.applyDynamicTheme();
          }
        });
      } catch (e) {}
    }
    this.renderAppearanceUI();
    this.applyDynamicTheme();
    this.bindAppearanceEvents();
  }

  initTheme() {
    this.initAppearance();
  }

  setTheme(theme) {
    if (theme === "night" || theme === "dark") {
      this.setThemeMode("dark");
    } else {
      this.setThemeMode("light");
    }
  }

  setThemeMode(mode) {
    this.appearance.mode = mode;
    this.saveAppearance();
    this.applyDynamicTheme();
    this.updateSegmentedButtonsUI();
  }

  updateSegmentedButtonsUI() {
    const btns = [
      { el: this.btnThemeSystem, mode: "system" },
      { el: this.btnThemeLight, mode: "light" },
      { el: this.btnThemeDark, mode: "dark" }
    ];

    const currentPalette = this.isDarkMode() ? this.appearance.dark : this.appearance.light;
    const accent = currentPalette.accent || "#007ACC";

    btns.forEach(({ el, mode }) => {
      if (!el) return;
      if (this.appearance.mode === mode) {
        el.className = "px-3 py-1.5 rounded-lg text-xs font-semibold text-white shadow-xs transition flex items-center justify-center active-theme-mode";
        el.style.backgroundColor = accent;
      } else {
        el.className = "px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 transition flex items-center justify-center";
        el.style.backgroundColor = "";
      }
    });
  }

  renderAppearanceUI() {
    if (this.pickerLightBg) this.pickerLightBg.value = this.appearance.light.bg;
    if (this.hexLightBg) this.hexLightBg.value = this.appearance.light.bg.toUpperCase();
    if (this.pickerLightFg) this.pickerLightFg.value = this.appearance.light.fg;
    if (this.hexLightFg) this.hexLightFg.value = this.appearance.light.fg.toUpperCase();
    if (this.pickerLightAccent) this.pickerLightAccent.value = this.appearance.light.accent;
    if (this.hexLightAccent) this.hexLightAccent.value = this.appearance.light.accent.toUpperCase();
    if (this.selectLightPreset) this.selectLightPreset.value = this.appearance.light.preset || "default-light";

    if (this.pickerDarkBg) this.pickerDarkBg.value = this.appearance.dark.bg;
    if (this.hexDarkBg) this.hexDarkBg.value = this.appearance.dark.bg.toUpperCase();
    if (this.pickerDarkFg) this.pickerDarkFg.value = this.appearance.dark.fg;
    if (this.hexDarkFg) this.hexDarkFg.value = this.appearance.dark.fg.toUpperCase();
    if (this.pickerDarkAccent) this.pickerDarkAccent.value = this.appearance.dark.accent;
    if (this.hexDarkAccent) this.hexDarkAccent.value = this.appearance.dark.accent.toUpperCase();
    if (this.selectDarkPreset) this.selectDarkPreset.value = this.appearance.dark.preset || "default-dark";

    this.updateSegmentedButtonsUI();
  }

  applyDynamicTheme() {
    const isDark = this.isDarkMode();
    this.currentTheme = isDark ? "night" : "light";

    if (isDark) {
      document.body.classList.add("theme-night");
      document.documentElement.classList.add("theme-night");
    } else {
      document.body.classList.remove("theme-night");
      document.documentElement.classList.remove("theme-night");
    }

    const currentPalette = isDark ? this.appearance.dark : this.appearance.light;
    const accent = currentPalette.accent || "#007ACC";
    const bg = currentPalette.bg || (isDark ? "#101010" : "#F9F9F9");
    const fg = currentPalette.fg || (isDark ? "#CCCCCC" : "#101010");

    const { r, g, b } = this.hexToRgb(accent);
    const rgba10 = `rgba(${r}, ${g}, ${b}, 0.12)`;
    const rgba18 = `rgba(${r}, ${g}, ${b}, 0.20)`;
    const rgba28 = `rgba(${r}, ${g}, ${b}, 0.28)`;
    const rgba38 = `rgba(${r}, ${g}, ${b}, 0.40)`;
    const rgbaHover = `rgba(${r}, ${g}, ${b}, 0.08)`;

    let dynamicCss = `
      :root {
        --custom-accent: ${accent};
        --custom-accent-rgb: ${r}, ${g}, ${b};
        --custom-bg: ${bg};
        --custom-fg: ${fg};
      }

      /* 1. Active Sidebar Tab & Nav Links (User requirement: change tab color properly) */
      body #nav-chat,
      body .active-nav-tab,
      body .nav-link.active,
      body #nav-chat.bg-blue-50\\/70,
      body .nav-link.bg-blue-50\\/70,
      body.theme-night #nav-chat,
      body.theme-night .active-nav-tab,
      body.theme-night .nav-link.active,
      body.theme-night #nav-chat.bg-blue-50\\/70,
      body.theme-night .nav-link.bg-blue-50\\/70 {
        background-color: ${isDark ? rgba18 : rgba10} !important;
        color: ${accent} !important;
        border: 1px solid ${rgba38} !important;
      }
      body #nav-chat i,
      body .active-nav-tab i,
      body .nav-link.active i,
      body.theme-night #nav-chat i,
      body.theme-night .active-nav-tab i,
      body.theme-night .nav-link.active i {
        color: ${accent} !important;
      }
      body .nav-link:hover:not(#nav-chat):not(.active),
      body.theme-night .nav-link:hover:not(#nav-chat):not(.active) {
        background-color: ${rgbaHover} !important;
      }

      /* 2. Modal Navigation Tabs */
      .modal-tab-btn.active-modal-tab,
      #modal-tab-btn-appearance.active-modal-tab,
      #modal-tab-btn-thermal.active-modal-tab,
      #modal-tab-btn-help.active-modal-tab {
        background-color: ${isDark ? rgba18 : rgba10} !important;
        color: ${accent} !important;
        border-color: ${rgba38} !important;
      }
      .modal-tab-btn.active-modal-tab i,
      #modal-tab-btn-appearance.active-modal-tab i,
      #modal-tab-btn-thermal.active-modal-tab i,
      #modal-tab-btn-help.active-modal-tab i {
        color: ${accent} !important;
      }

      /* 3. Action Buttons & Interactive Accents */
      #new-chat-btn {
        background-color: ${accent} !important;
        border-color: ${accent} !important;
        box-shadow: 0 4px 14px rgba(${r}, ${g}, ${b}, 0.35) !important;
      }
      #new-chat-btn:hover {
        filter: brightness(0.92) !important;
      }
      #btn-send-message {
        background-color: ${accent} !important;
      }
      #btn-send-message:hover {
        filter: brightness(0.92) !important;
      }
      .bg-blue-600 {
        background-color: ${accent} !important;
      }
      .text-blue-600 {
        color: ${accent} !important;
      }
      .border-blue-600 {
        border-color: ${accent} !important;
      }

      /* 4. Active Segmented Theme Button */
      #theme-mode-segmented button.active-theme-mode {
        background-color: ${accent} !important;
        color: #ffffff !important;
      }
    `;

    if (isDark) {
      dynamicCss += `
        body.theme-night,
        html.theme-night {
          background-color: ${bg} !important;
          color: ${fg} !important;
        }
        body.theme-night aside,
        body.theme-night [data-purpose="navigation-sidebar"] {
          background-color: ${bg} !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }
        body.theme-night [data-purpose="top-nav"] {
          background-color: ${bg} !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }
        body.theme-night [data-purpose="weather-intelligence-panel"] {
          background-color: ${bg} !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }
        body.theme-night [data-purpose="current-weather-card"],
        body.theme-night [data-purpose="five-day-forecast-card"],
        body.theme-night [data-purpose="disaster-alerts-card"],
        body.theme-night .bg-white {
          background-color: #111116 !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
          color: ${fg} !important;
        }
        body.theme-night .text-slate-900,
        body.theme-night .text-slate-800,
        body.theme-night .text-slate-700 {
          color: ${fg} !important;
        }
        body.theme-night #modal-settings .bg-white {
          background-color: ${bg} !important;
          border-color: rgba(255, 255, 255, 0.1) !important;
          color: ${fg} !important;
        }
        body.theme-night #modal-settings .bg-slate-50 {
          background-color: rgba(255, 255, 255, 0.04) !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }
        body.theme-night .prompt-pill {
          background-color: rgba(255, 255, 255, 0.04) !important;
          border-color: rgba(255, 255, 255, 0.08) !important;
        }
        body.theme-night .prompt-pill:hover {
          border-color: ${accent} !important;
        }
      `;
    } else {
      dynamicCss += `
        body,
        html {
          background-color: ${bg} !important;
          color: ${fg} !important;
        }
        .bg-\\[\\#f4f7fb\\] {
          background-color: ${bg} !important;
        }
        .text-slate-900,
        .text-slate-800 {
          color: ${fg} !important;
        }
      `;
    }

    let styleEl = document.getElementById("weathergpt-dynamic-theme");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "weathergpt-dynamic-theme";
      document.head.appendChild(styleEl);
    }
    styleEl.textContent = dynamicCss;

    this.updateSegmentedButtonsUI();
  }

  bindAppearanceEvents() {
    // 1. Theme Mode Segmented Controls
    if (this.btnThemeSystem) {
      this.btnThemeSystem.addEventListener("click", () => this.setThemeMode("system"));
    }
    if (this.btnThemeLight) {
      this.btnThemeLight.addEventListener("click", () => this.setThemeMode("light"));
    }
    if (this.btnThemeDark) {
      this.btnThemeDark.addEventListener("click", () => this.setThemeMode("dark"));
    }

    // 2. Presets Dropdowns
    if (this.selectLightPreset) {
      this.selectLightPreset.addEventListener("change", () => {
        const p = this.selectLightPreset.value;
        if (THEME_PRESETS.light[p]) {
          this.appearance.light = { preset: p, ...THEME_PRESETS.light[p] };
          this.renderAppearanceUI();
          this.saveAppearance();
          this.applyDynamicTheme();
        }
      });
    }

    if (this.selectDarkPreset) {
      this.selectDarkPreset.addEventListener("change", () => {
        const p = this.selectDarkPreset.value;
        if (THEME_PRESETS.dark[p]) {
          this.appearance.dark = { preset: p, ...THEME_PRESETS.dark[p] };
          this.renderAppearanceUI();
          this.saveAppearance();
          this.applyDynamicTheme();
        }
      });
    }

    // 3. Two-Way Color & Hex Binding
    const attachTwoWay = (picker, hexInput, themeKey, fieldKey, selectPresetEl) => {
      if (picker && hexInput) {
        picker.addEventListener("input", () => {
          const val = picker.value;
          hexInput.value = val.toUpperCase();
          this.appearance[themeKey][fieldKey] = val;
          this.appearance[themeKey].preset = "custom";
          if (selectPresetEl) {
            let matched = "custom";
            for (const [presetKey, presetVals] of Object.entries(THEME_PRESETS[themeKey])) {
              if (
                presetVals.bg.toLowerCase() === this.appearance[themeKey].bg.toLowerCase() &&
                presetVals.fg.toLowerCase() === this.appearance[themeKey].fg.toLowerCase() &&
                presetVals.accent.toLowerCase() === this.appearance[themeKey].accent.toLowerCase()
              ) {
                matched = presetKey;
                break;
              }
            }
            this.appearance[themeKey].preset = matched;
            selectPresetEl.value = matched;
          }
          this.saveAppearance();
          this.applyDynamicTheme();
        });

        hexInput.addEventListener("input", () => {
          let val = hexInput.value.trim();
          if (!val.startsWith("#")) val = "#" + val;
          if (/^#([0-9A-Fa-f]{6})$/.test(val)) {
            picker.value = val;
            this.appearance[themeKey][fieldKey] = val;
            this.appearance[themeKey].preset = "custom";
            this.saveAppearance();
            this.applyDynamicTheme();
          }
        });
      }
    };

    attachTwoWay(this.pickerLightBg, this.hexLightBg, "light", "bg", this.selectLightPreset);
    attachTwoWay(this.pickerLightFg, this.hexLightFg, "light", "fg", this.selectLightPreset);
    attachTwoWay(this.pickerLightAccent, this.hexLightAccent, "light", "accent", this.selectLightPreset);

    attachTwoWay(this.pickerDarkBg, this.hexDarkBg, "dark", "bg", this.selectDarkPreset);
    attachTwoWay(this.pickerDarkFg, this.hexDarkFg, "dark", "fg", this.selectDarkPreset);
    attachTwoWay(this.pickerDarkAccent, this.hexDarkAccent, "dark", "accent", this.selectDarkPreset);

    // 4. Reset to Default Colors
    if (this.btnResetThemeColors) {
      this.btnResetThemeColors.addEventListener("click", () => {
        this.appearance.light = { ...DEFAULT_APPEARANCE.light };
        this.appearance.dark = { ...DEFAULT_APPEARANCE.dark };
        this.renderAppearanceUI();
        this.saveAppearance();
        this.applyDynamicTheme();
      });
    }

    // 5. Help & Setting Modal Tabs Navigation
    if (this.modalTabBtnAppearance) {
      this.modalTabBtnAppearance.addEventListener("click", () => this.switchModalTab("appearance"));
    }
    if (this.modalTabBtnThermal) {
      this.modalTabBtnThermal.addEventListener("click", () => this.switchModalTab("thermal"));
    }
    if (this.modalTabBtnHelp) {
      this.modalTabBtnHelp.addEventListener("click", () => this.switchModalTab("help"));
    }
  }

  switchModalTab(tabName) {
    const tabs = [
      { name: "appearance", btn: this.modalTabBtnAppearance, content: this.modalContentAppearance },
      { name: "thermal", btn: this.modalTabBtnThermal, content: this.modalContentThermal },
      { name: "help", btn: this.modalTabBtnHelp, content: this.modalContentHelp }
    ];

    tabs.forEach(({ name, btn, content }) => {
      if (name === tabName) {
        if (content) content.classList.remove("hidden");
        if (btn) {
          btn.className = "modal-tab-btn active-modal-tab px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 bg-blue-50 text-blue-600 border border-blue-200";
        }
      } else {
        if (content) content.classList.add("hidden");
        if (btn) {
          btn.className = "modal-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 border border-transparent transition flex items-center gap-1.5";
        }
      }
    });

    this.applyDynamicTheme();
  }

  openSettingsModal() {
    this.renderAppearanceUI();
    this.switchModalTab("appearance");
    const modal = document.getElementById("modal-settings");
    if (modal) {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    }
  }

  initThermalScaleUI() {
    const btnC = document.getElementById("btn-scale-celsius");
    const btnF = document.getElementById("btn-scale-fahrenheit");
    const btnK = document.getElementById("btn-scale-kelvin");
    const activeBadge = document.getElementById("active-scale-badge");

    const scales = [
      { unit: "C", btn: btnC, name: "Celsius", sym: "°C" },
      { unit: "F", btn: btnF, name: "Fahrenheit", sym: "°F" },
      { unit: "K", btn: btnK, name: "Kelvin", sym: "K" }
    ];

    const updateScaleUI = (selectedUnit) => {
      scales.forEach(({ unit, btn, name, sym }) => {
        if (!btn) return;
        const checkIcon = btn.querySelector(".scale-check");
        if (unit === selectedUnit) {
          btn.className = "thermal-scale-btn p-3.5 rounded-2xl bg-blue-50/40 border-2 border-blue-500 text-left transition shadow-2xs hover:border-blue-400 group cursor-pointer relative";
          if (checkIcon) {
            checkIcon.classList.remove("hidden");
            checkIcon.classList.add("flex");
          }
          if (activeBadge) {
            activeBadge.textContent = `${name} (${sym}) Active`;
          }
        } else {
          btn.className = "thermal-scale-btn p-3.5 rounded-2xl bg-white border border-slate-200 text-left transition shadow-2xs hover:border-slate-300 group cursor-pointer relative";
          if (checkIcon) {
            checkIcon.classList.remove("flex");
            checkIcon.classList.add("hidden");
          }
        }
      });
    };

    const getTS = () => window.ThermalScale || (typeof ThermalScale !== "undefined" ? ThermalScale : null);
    const getWUI = () => window.WeatherUI || (typeof WeatherUI !== "undefined" ? WeatherUI : null);

    const currentUnit = getTS()?.getUnit() || "C";
    updateScaleUI(currentUnit);

    scales.forEach(({ unit, btn }) => {
      if (!btn) return;
      btn.addEventListener("click", () => {
        const ts = getTS();
        if (ts) {
          ts.setUnit(unit);
        }
        updateScaleUI(unit);
        const wui = getWUI();
        if (wui && wui.refreshThermalDisplays) {
          wui.refreshThermalDisplays();
        }
      });
    });
  }

  handleLogout() {
    localStorage.removeItem("weathergpt_google_user");
    this.currentUser = {
      name: "User Profile",
      email: "Account",
      avatar: "U",
      connected: false
    };
    this.renderUserProfile();
    if (this.translationToast && this.translationToastText) {
      if (this.translationToastIcon) {
        this.translationToastIcon.className = "fa-solid fa-check text-emerald-400 text-sm";
      }
      this.translationToastText.textContent = "Logged out successfully!";
      this.translationToast.classList.remove("hidden");
      this.translationToast.classList.add("flex");
      setTimeout(() => {
        this.translationToast.classList.add("hidden");
        this.translationToast.classList.remove("flex");
      }, 1500);
    }
  }

  createNewSessionId() {
    return "sess_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now();
  }

  loadUserProfile() {
    const saved = localStorage.getItem("weathergpt_google_user");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return {
      name: "Guest User",
      email: "",
      avatar: "U",
      connected: false
    };
  }

  renderUserProfile() {
    const nameEl = document.getElementById("user-display-name");
    const subEl = document.getElementById("user-account-sub");
    const avatarBadge = document.getElementById("user-avatar-badge");

    if (nameEl) nameEl.textContent = this.currentUser.connected ? this.currentUser.name : "User Profile";
    if (subEl) subEl.textContent = this.currentUser.connected ? this.currentUser.email : "Account";
    if (avatarBadge) {
      if (this.currentUser.connected) {
        avatarBadge.textContent = this.currentUser.avatar || this.currentUser.name.charAt(0).toUpperCase();
      } else {
        avatarBadge.innerHTML = `<i class="fa-regular fa-user text-xs"></i>`;
      }
    }

    // Settings modal profile elements
    const sName = document.getElementById("settings-user-name");
    const sEmail = document.getElementById("settings-user-email");
    const sAvatar = document.getElementById("settings-user-avatar");
    const sStatus = document.getElementById("settings-account-status");

    if (sName) sName.textContent = this.currentUser.name;
    if (sEmail) sEmail.textContent = this.currentUser.email || "Guest Session";
    if (sAvatar) sAvatar.textContent = this.currentUser.avatar || this.currentUser.name.charAt(0);
    if (sStatus) {
      sStatus.textContent = this.currentUser.connected ? "Account Synced" : "Guest Mode (Not Signed In)";
      sStatus.className = this.currentUser.connected ? "text-emerald-600" : "text-slate-400";
    }
  }

  initElements() {
    // Chat elements
    this.chatInput = document.getElementById("chat-input");
    this.btnSend = document.getElementById("btn-send-message");
    this.btnMic = document.getElementById("btn-voice-mic");
    this.messagesContainer = document.getElementById("chat-messages-container");
    this.welcomeBanner = document.getElementById("chat-welcome-banner");
    this.chatScroll = document.getElementById("chat-scroll-container");
    this.newChatBtn = document.getElementById("new-chat-btn");

    // Search and location
    this.globalSearch = document.getElementById("global-search");
    this.searchDropdown = document.getElementById("search-autocomplete-dropdown");
    this.btnCityDropdown = document.getElementById("btn-city-dropdown");
    this.cardChangeCity = document.getElementById("card-change-city");

    // Language Dropdown Elements
    this.btnLangDropdown = document.getElementById("btn-language-dropdown");
    this.langMenu = document.getElementById("language-menu");
    this.langChevron = document.getElementById("lang-chevron");
    this.langLabel = document.getElementById("lang-label");
    this.langOptions = document.querySelectorAll(".lang-option");
    this.translationToast = document.getElementById("translation-toast");
    this.translationToastIcon = document.getElementById("translation-toast-icon");
    this.translationToastText = document.getElementById("translation-toast-text");

    // Profile & Settings
    this.btnGoogleLogin = document.getElementById("btn-google-login");
    this.btnOpenSettings = document.getElementById("btn-open-settings");
    this.btnSaveApiKeys = document.getElementById("btn-save-api-keys");
    this.btnThemeToggle = document.getElementById("btn-theme-toggle");

    // Alerts
    this.btnViewAllAlerts = document.getElementById("btn-view-all-alerts");
    this.navAlerts = document.getElementById("nav-alerts");

    // Nav Links
    this.navChat = document.getElementById("nav-chat");
    this.navDrought = document.getElementById("nav-drought");
    this.navClimate = document.getElementById("nav-climate");
    this.navDisaster = document.getElementById("nav-disaster");
    this.navSaved = document.getElementById("nav-saved");

    // Theme & Logout elements
    this.btnThemeDay = document.getElementById("btn-theme-day");
    this.btnThemeNight = document.getElementById("btn-theme-night");
    this.btnLogout = document.getElementById("btn-logout-account");

    // Appearance & Settings Modal Elements
    this.btnThemeSystem = document.getElementById("btn-theme-system");
    this.btnThemeLight = document.getElementById("btn-theme-light");
    this.btnThemeDark = document.getElementById("btn-theme-dark");
    this.selectLightPreset = document.getElementById("select-light-preset");
    this.pickerLightBg = document.getElementById("picker-light-bg");
    this.hexLightBg = document.getElementById("hex-light-bg");
    this.pickerLightFg = document.getElementById("picker-light-fg");
    this.hexLightFg = document.getElementById("hex-light-fg");
    this.pickerLightAccent = document.getElementById("picker-light-accent");
    this.hexLightAccent = document.getElementById("hex-light-accent");
    this.selectDarkPreset = document.getElementById("select-dark-preset");
    this.pickerDarkBg = document.getElementById("picker-dark-bg");
    this.hexDarkBg = document.getElementById("hex-dark-bg");
    this.pickerDarkFg = document.getElementById("picker-dark-fg");
    this.hexDarkFg = document.getElementById("hex-dark-fg");
    this.pickerDarkAccent = document.getElementById("picker-dark-accent");
    this.hexDarkAccent = document.getElementById("hex-dark-accent");
    this.btnResetThemeColors = document.getElementById("btn-reset-theme-colors");
    this.modalTabBtnAppearance = document.getElementById("modal-tab-btn-appearance");
    this.modalTabBtnThermal = document.getElementById("modal-tab-btn-thermal");
    this.modalTabBtnHelp = document.getElementById("modal-tab-btn-help");
    this.modalContentAppearance = document.getElementById("modal-content-appearance");
    this.modalContentThermal = document.getElementById("modal-content-thermal");
    this.modalContentHelp = document.getElementById("modal-content-help");

    // Prompt pills & Recent Chats
    this.promptPills = document.querySelectorAll(".prompt-pill");
    this.recentChatsList = document.getElementById("recent-chats-list");
    this.btnClearRecentChats = document.getElementById("btn-clear-recent-chats");

    // In-Screen Delete Confirmation Modal Elements (User Request)
    this.modalConfirmDelete = document.getElementById("modal-confirm-delete");
    this.confirmDeleteMsg = document.getElementById("confirm-delete-message");
    this.btnConfirmDelete = document.getElementById("btn-confirm-delete");
    this.btnCancelDelete = document.getElementById("btn-cancel-delete");
    this.pendingDeleteType = null;
    this.pendingDeleteSessionId = null;
  }

  initEvents() {
    // 1. Send / Cancel Message on Click & Enter
    if (this.btnSend) {
      this.btnSend.addEventListener("click", () => {
        if (this.isGenerating) {
          this.cancelCurrentMessage();
        } else {
          this.handleSendMessage();
        }
      });
    }
    if (this.chatInput) {
      this.chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          if (this.isGenerating) return;
          this.handleSendMessage();
        }
      });
    }

    // 2. New Chat Button
    if (this.newChatBtn) {
      this.newChatBtn.addEventListener("click", () => this.startNewChat());
    }

    // 2.1 Delete Confirmation Modal Controls
    if (this.btnCancelDelete) {
      this.btnCancelDelete.addEventListener("click", () => this.closeDeleteModal());
    }
    if (this.modalConfirmDelete) {
      this.modalConfirmDelete.addEventListener("click", (e) => {
        if (e.target === this.modalConfirmDelete) this.closeDeleteModal();
      });
    }
    if (this.btnConfirmDelete) {
      this.btnConfirmDelete.addEventListener("click", () => this.handleConfirmDelete());
    }

    // 2.2 Clear All Recent Chats Button
    if (this.btnClearRecentChats) {
      this.btnClearRecentChats.addEventListener("click", (e) => {
        e.preventDefault();
        this.openDeleteModal({
          type: "all",
          message: "Do you really want to delete all recent history?"
        });
      });
    }

    // 3. Prompt Pills
    this.promptPills.forEach(pill => {
      pill.addEventListener("click", () => {
        const text = pill.dataset.prompt || pill.innerText.trim();
        if (this.chatInput) {
          this.chatInput.value = text;
          this.handleSendMessage();
        }
      });
    });

    // 4. Global Search Autocomplete (Matching Locations)
    let searchTimeout = null;
    if (this.globalSearch) {
      this.globalSearch.addEventListener("focus", () => {
        const q = (this.globalSearch.value || "").trim();
        if (q.length >= 2) {
          this.searchLocations(q);
        }
      });

      this.globalSearch.addEventListener("input", (e) => {
        clearTimeout(searchTimeout);
        const q = e.target.value.trim();
        if (q.length < 2) {
          if (this.searchDropdown) this.searchDropdown.classList.add("hidden");
          return;
        }
        searchTimeout = setTimeout(() => this.searchLocations(q), 120);
      });

      document.addEventListener("click", (e) => {
        if (!this.globalSearch.contains(e.target) && this.searchDropdown && !this.searchDropdown.contains(e.target)) {
          this.searchDropdown.classList.add("hidden");
        }
      });
    }

    // 5. Language Dropdown Controls & Fast Auto-Translation
    if (this.btnLangDropdown && this.langMenu) {
      this.btnLangDropdown.addEventListener("click", (e) => {
        e.stopPropagation();
        const isHidden = this.langMenu.classList.contains("hidden");
        if (isHidden) {
          this.langMenu.classList.remove("hidden");
          if (this.langChevron) this.langChevron.classList.add("rotate-180");
        } else {
          this.langMenu.classList.add("hidden");
          if (this.langChevron) this.langChevron.classList.remove("rotate-180");
        }
      });

      document.addEventListener("click", (e) => {
        if (!this.btnLangDropdown.contains(e.target) && !this.langMenu.contains(e.target)) {
          this.langMenu.classList.add("hidden");
          if (this.langChevron) this.langChevron.classList.remove("rotate-180");
        }
      });
    }

    if (this.langOptions) {
      this.langOptions.forEach(opt => {
        opt.addEventListener("click", () => {
          const lang = opt.dataset.lang;
          if (this.langMenu) this.langMenu.classList.add("hidden");
          if (this.langChevron) this.langChevron.classList.remove("rotate-180");
          this.setLanguage(lang);
        });
      });
    }

    // 6. Google Login Modal Triggers
    if (this.btnGoogleLogin) {
      this.btnGoogleLogin.addEventListener("click", () => {
        const modal = document.getElementById("modal-google-login");
        if (modal) {
          modal.classList.remove("hidden");
          modal.classList.add("flex");
        }
      });
    }

    const btnSyncGoogle = document.getElementById("btn-sync-google-account");
    if (btnSyncGoogle) {
      btnSyncGoogle.addEventListener("click", () => {
        const nameInput = document.getElementById("input-google-name");
        const emailInput = document.getElementById("input-google-email");
        const name = nameInput ? nameInput.value.trim() : "User";
        const email = emailInput ? emailInput.value.trim() : "";

        this.currentUser = {
          name: name || "User",
          email: email || "",
          avatar: (name || "U").charAt(0).toUpperCase(),
          connected: true
        };
        localStorage.setItem("weathergpt_google_user", JSON.stringify(this.currentUser));
        this.renderUserProfile();
        this.closeAllModals();
      });
    }

    // 7. View All National Alerts Modal
    const openAlertsModal = (e) => {
      if (e) e.preventDefault();
      this.loadNationalAlerts();
      const modal = document.getElementById("modal-alerts");
      if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
      }
    };
    if (this.btnViewAllAlerts) this.btnViewAllAlerts.addEventListener("click", openAlertsModal);
    if (this.navAlerts) this.navAlerts.addEventListener("click", openAlertsModal);

    // 8. Nav Links & Modals
    this.setupModalLink(this.navDrought, "modal-drought");
    this.setupModalLink(this.navClimate, "modal-climate");
    this.setupModalLink(this.navDisaster, "modal-disaster");
    this.setupModalLink(this.navSaved, "modal-saved", () => this.renderSavedLocationsModal());

    // Day & Night Theme Switcher (1st Header Icon & Modal Buttons)
    if (this.btnThemeToggle) {
      this.btnThemeToggle.addEventListener("click", () => {
        const next = this.currentTheme === "night" ? "light" : "night";
        this.setTheme(next);
      });
    }
    if (this.btnThemeDay) {
      this.btnThemeDay.addEventListener("click", () => this.setTheme("light"));
    }
    if (this.btnThemeNight) {
      this.btnThemeNight.addEventListener("click", () => this.setTheme("night"));
    }

    // Account Log Out Button in Settings
    if (this.btnLogout) {
      this.btnLogout.addEventListener("click", () => this.handleLogout());
    }

    if (this.navChat) {
      this.navChat.addEventListener("click", (e) => {
        e.preventDefault();
        this.closeAllModals();
        if (this.chatScroll) this.chatScroll.scrollTop = 0;
      });
    }

    // 9. Settings Modal (Help & Setting)
    if (this.btnOpenSettings) {
      this.btnOpenSettings.addEventListener("click", () => {
        this.openSettingsModal();
      });
    }

    const modalSettings = document.getElementById("modal-settings");
    if (modalSettings) {
      modalSettings.addEventListener("click", (e) => {
        if (e.target === modalSettings) {
          modalSettings.classList.add("hidden");
          modalSettings.classList.remove("flex");
        }
      });
    }

    if (this.btnSaveApiKeys) {
      this.btnSaveApiKeys.addEventListener("click", () => this.saveApiSettings());
    }

    // 10. Voice Mic
    if (this.btnMic) {
      this.btnMic.addEventListener("click", () => this.toggleVoice());
    }

    // 11. Modal Close Buttons
    document.querySelectorAll(".modal-close").forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.target;
        const modal = document.getElementById(targetId);
        if (modal) {
          modal.classList.add("hidden");
          modal.classList.remove("flex");
        }
      });
    });

    // 12. City Change Click
    if (this.btnCityDropdown) {
      this.btnCityDropdown.addEventListener("click", () => this.renderSavedLocationsModal(true));
    }
    if (this.cardChangeCity) {
      this.cardChangeCity.addEventListener("click", () => this.renderSavedLocationsModal(true));
    }
  }

  setupModalLink(navElem, modalId, onOpen) {
    if (!navElem) return;
    navElem.addEventListener("click", (e) => {
      e.preventDefault();
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        if (onOpen) onOpen();
      }
    });
  }

  closeAllModals() {
    document.querySelectorAll("[id^='modal-']").forEach(m => {
      m.classList.add("hidden");
      m.classList.remove("flex");
    });
  }

  initMap() {
    if (typeof MapController !== "undefined") {
      MapController.init(async (lat, lon) => {
        await this.handleMapLocationSelect(lat, lon);
      });
    }
  }

  async handleMapLocationSelect(lat, lon) {
    const parsedLat = parseFloat(lat);
    const parsedLon = parseFloat(lon);
    if (isNaN(parsedLat) || isNaN(parsedLon)) return;

    // Immediately update coordinate displays in map footer, fullscreen HUD, and card
    const latDir = parsedLat >= 0 ? "N" : "S";
    const lonDir = parsedLon >= 0 ? "E" : "W";
    const coordStr = `${Math.abs(parsedLat).toFixed(4)}° ${latDir}, ${Math.abs(parsedLon).toFixed(4)}° ${lonDir}`;
    const sideCoords = document.getElementById("sidebar-map-coords");
    if (sideCoords) sideCoords.textContent = coordStr;
    const fsCoords = document.getElementById("fs-coords-hud");
    if (fsCoords) fsCoords.textContent = coordStr;
    const elCoords = document.getElementById("card-coordinates-val");
    if (elCoords) elCoords.textContent = coordStr;

    // Temporary indicator while resolving local place
    const navLabel = document.getElementById("nav-city-label");
    if (navLabel) navLabel.innerHTML = `<span class="text-blue-500 animate-pulse">Locating place...</span>`;
    const cardCity = document.getElementById("card-city-name");
    if (cardCity) cardCity.textContent = "Locating...";

    let d = null;
    try {
      const res = await apiFetch(`/api/weather/reverse-geocode?lat=${parsedLat}&lon=${parsedLon}`);
      if (res && res.ok) {
        d = await res.json();
      }
    } catch (e) {
      console.warn("Reverse geocoding error:", e);
    }

    const isBad = (str) => !str || str === "Selected Location" || str === "Selected Place" || str.includes("Location (") || str.includes("Coordinates (");

    // 2. Direct BigDataCloud client API fallback if backend returned nothing or generic coordinates
    if (!d || !d.name || isBad(d.name)) {
      try {
        const bdcRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${parsedLat}&longitude=${parsedLon}&localityLanguage=en`);
        if (bdcRes.ok) {
          const bdc = await bdcRes.json();
          const city = bdc.city || "";
          const locality = bdc.locality || "";
          const state = bdc.principalSubdivision || "";
          const country = bdc.countryName || "";
          let district = "";
          if (bdc.localityInfo && Array.isArray(bdc.localityInfo.administrative)) {
            for (const admin of bdc.localityInfo.administrative) {
              const aname = admin.name || "";
              if (aname.toLowerCase().includes("district") || aname.toLowerCase().includes("county")) {
                district = aname.replace(/ district/i, "").replace(/ county/i, "");
                break;
              }
            }
          }
          const primary = locality || city || district || state || country;
          if (primary) {
            const parts = [primary, city, district, state, country].filter((v, i, a) => v && a.indexOf(v) === i);
            const formatted = parts.join(", ");
            d = {
              name: primary,
              city: city || locality || primary,
              locality: locality || city || primary,
              sublocality: locality !== city ? locality : "",
              district,
              state,
              country,
              formattedAddress: formatted,
              formatted,
              latitude: parsedLat,
              longitude: parsedLon
            };
          }
        }
      } catch (bdcErr) {
        console.warn("Direct BDC client fallback error:", bdcErr);
      }
    }

    // 3. Direct OSM fallback if still unresolved
    if (!d || !d.name || isBad(d.name)) {
      try {
        const osmRes = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${parsedLat}&lon=${parsedLon}&format=json&zoom=18&addressdetails=1&accept-language=en`, {
          headers: { "Accept": "application/json" }
        });
        if (osmRes.ok) {
          const osmData = await osmRes.json();
          const addr = osmData.address || {};
          const sublocality = addr.suburb || addr.neighbourhood || addr.residential || addr.subdistrict || "";
          const city = addr.city || addr.town || addr.municipality || addr.village || "";
          const district = addr.state_district || addr.county || addr.district || "";
          const state = addr.state || "";
          const country = addr.country || "";
          const name = sublocality || addr.neighbourhood || city || district || state || country || coordStr;
          d = {
            name,
            sublocality,
            neighborhood: addr.neighbourhood || "",
            locality: city || sublocality,
            city,
            district,
            state,
            country,
            formattedAddress: osmData.display_name || name,
            formatted: osmData.display_name || name,
            latitude: parsedLat,
            longitude: parsedLon
          };
        }
      } catch (osmErr) {
        console.warn("Direct OSM fallback error:", osmErr);
      }
    }

    const candidates = d ? [d.sublocality, d.neighborhood, d.locality, d.name, d.city, d.district, d.state, d.country] : [];
    const resolvedName = candidates.find(x => !isBad(x)) || (d && d.name && !isBad(d.name) ? d.name : coordStr);

    await this.setActiveLocation({
      ...(d || {}),
      name: resolvedName,
      city: (d && d.city) || resolvedName,
      latitude: parsedLat,
      longitude: parsedLon,
      isCurrentLocation: false
    });

    const secondary = (d && (d.district || d.state || d.country)) || "";
    this.showToast(`📍 Located: ${resolvedName}${secondary ? ', ' + secondary : ''}`, "info");
  }

  async triggerMapPlaceWeatherChat(cityName, formattedLabel, lat, lon) {
    if (this.isGenerating) {
      this.cancelCurrentMessage();
    }
    const placeName = formattedLabel || cityName;
    if (this.welcomeBanner) this.welcomeBanner.classList.add("hidden");

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userQuery = `Detailed weather and climate analysis for ${placeName}`;
    this.appendUserMessage(userQuery, timeStr);

    this.chatAbortController = new AbortController();
    this.setChatGeneratingState(true);
    this.currentTypingId = this.showTypingIndicator();

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: userQuery,
          language: this.currentLanguage,
          location: placeName,
          latitude: lat,
          longitude: lon
        }),
        signal: this.chatAbortController.signal
      });

      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }

      if (res && res.ok) {
        const data = await res.json();
        const resTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.appendAssistantMessage(data.reply, data.weather, resTime, null, data.matching_locations);

        if (typeof SupabaseService !== "undefined") {
          SupabaseService.saveChatMessage(this.sessionId, userQuery, data.reply, placeName);
        }
        await this.loadRecentChats();
      } else {
        this.appendAssistantMessage(`Unable to retrieve meteorological intelligence for ${placeName}.`, null, timeStr);
      }
    } catch (e) {
      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }
      if (e.name === "AbortError" || (this.chatAbortController && this.chatAbortController.signal.aborted)) {
        return;
      }
      this.appendAssistantMessage("Network connection error. Please verify FastAPI backend is active.", null, timeStr);
    } finally {
      this.setChatGeneratingState(false);
      this.chatAbortController = null;
      this.currentTypingId = null;
      if (this.chatInput) this.chatInput.focus();
    }
  }


  // ----------------------------------------------------
  // Geolocation & Active Location Methods
  // ----------------------------------------------------

  async requestCurrentLocation(onSuccessCallback = null) {
    const navLabel = document.getElementById("nav-city-label");
    if (navLabel) {
      navLabel.innerHTML = `<span class="text-blue-500 animate-pulse">Detecting live location...</span>`;
    }
    this.showToast("📍 Detecting your live location...", "info");

    const resolveCoords = async (lat, lon, sourceLabel = "") => {
      try {
        let d = null;
        try {
          const res = await apiFetch(`/api/weather/reverse-geocode?lat=${lat}&lon=${lon}`);
          if (res && res.ok) d = await res.json();
        } catch {}

        if (!d || !d.name || d.name === "Selected Location") {
          try {
            const bdcRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`);
            if (bdcRes.ok) {
              const bdc = await bdcRes.json();
              const city = bdc.city || bdc.locality || "";
              const state = bdc.principalSubdivision || "";
              const country = bdc.countryName || "";
              d = {
                name: city || state || country,
                city: city || state,
                state,
                country,
                formattedAddress: [city, state, country].filter(Boolean).join(", "),
                latitude: lat,
                longitude: lon
              };
            }
          } catch {}
        }

        const resolvedName = (d && d.name) || (d && d.city) || "Current Location";
        const secondary = (d && (d.district || d.state || d.country)) || "";

        await this.setActiveLocation({
          ...(d || {}),
          name: resolvedName,
          city: (d && d.city) || resolvedName,
          latitude: lat,
          longitude: lon,
          isCurrentLocation: true
        });

        this.showToast(`📍 Live Location: ${resolvedName}${secondary ? ', ' + secondary : ''}${sourceLabel}`, "success");
        if (typeof onSuccessCallback === "function") {
          onSuccessCallback(this.activeLocation);
        }
        return true;
      } catch (err) {
        console.error("Coordinate resolution failed:", err);
        return false;
      }
    };

    // IP Geolocation fallback for laptops where hardware GPS is unavailable or blocked
    const fallbackToIPLocation = async (reason) => {
      console.warn("Falling back to IP geolocation:", reason);
      try {
        const ipRes = await fetch("https://api.bigdatacloud.net/data/reverse-geocode-client?localityLanguage=en");
        if (ipRes.ok) {
          const data = await ipRes.json();
          const lat = parseFloat(data.latitude);
          const lon = parseFloat(data.longitude);
          if (!isNaN(lat) && !isNaN(lon)) {
            const city = data.city || data.locality || "";
            const state = data.principalSubdivision || "";
            const country = data.countryName || "";
            const name = city || state || country || "Live Location";
            await this.setActiveLocation({
              name,
              city: city || name,
              state,
              country,
              latitude: lat,
              longitude: lon,
              formattedAddress: [city, state, country].filter(Boolean).join(", "),
              isCurrentLocation: true
            });
            this.showToast(`📍 Live Location: ${name}${state ? ', ' + state : ''} (Network Detected)`, "success");
            if (typeof onSuccessCallback === "function") {
              onSuccessCallback(this.activeLocation);
            }
            return true;
          }
        }
      } catch (e) {
        console.warn("BigDataCloud IP detection failed, trying ipapi:", e);
      }

      try {
        const ipapiRes = await fetch("https://ipapi.co/json/");
        if (ipapiRes.ok) {
          const data = await ipapiRes.json();
          const lat = parseFloat(data.latitude);
          const lon = parseFloat(data.longitude);
          if (!isNaN(lat) && !isNaN(lon)) {
            const city = data.city || "";
            const state = data.region || "";
            const country = data.country_name || "";
            const name = city || state || country || "Live Location";
            await this.setActiveLocation({
              name,
              city: city || name,
              state,
              country,
              latitude: lat,
              longitude: lon,
              formattedAddress: [city, state, country].filter(Boolean).join(", "),
              isCurrentLocation: true
            });
            this.showToast(`📍 Live Location: ${name}${state ? ', ' + state : ''} (Network Detected)`, "success");
            if (typeof onSuccessCallback === "function") {
              onSuccessCallback(this.activeLocation);
            }
            return true;
          }
        }
      } catch (e) {
        console.warn("Secondary IP detection failed:", e);
      }

      this.showToast("⚠️ Could not detect live location. Please search location manually.", "error");
      return false;
    };

    if (!navigator.geolocation) {
      await fallbackToIPLocation("Geolocation API unsupported");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        await resolveCoords(lat, lon);
      },
      async (err) => {
        console.warn("Browser GPS error, falling back to IP location:", err);
        await fallbackToIPLocation(err.message || "GPS unavailable");
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 30000
      }
    );
  }

  async setActiveLocation(loc) {
    if (!loc) return;
    const lat = parseFloat(loc.latitude != null ? loc.latitude : loc.lat);
    const lon = parseFloat(loc.longitude != null ? loc.longitude : loc.lon);
    if (isNaN(lat) || isNaN(lon)) return;

    const isCoordString = (str) => {
      if (!str) return true;
      const s = String(str).toLowerCase().trim();
      return s.includes("location (") || s.includes("coordinates (") || s.includes("coords (") || s === "selected location" || s === "selected place" || s === "locating..." || /^-?\d+(\.\d+)?°?\s*[nsew]?,?\s*-?\d+(\.\d+)?°?\s*[nsew]?/i.test(s);
    };

    let name = loc.name || loc.city || loc.locality || loc.sublocality || "";
    if (isCoordString(name)) name = "";

    let city = loc.city || loc.locality || loc.name || "";
    if (isCoordString(city)) city = "";

    const locality = loc.locality || "";
    const sublocality = loc.sublocality || "";
    const neighborhood = loc.neighborhood || "";
    const district = loc.district || loc.admin2 || "";
    const state = loc.state || loc.admin1 || "";
    const country = loc.country || "India";
    const postalCode = loc.postalCode || "";
    const placeId = loc.placeId || "";
    let formattedAddress = loc.formattedAddress || loc.formatted || "";
    if (isCoordString(formattedAddress)) formattedAddress = "";
    const isCurrent = !!loc.isCurrentLocation;

    // Single source of truth: Normalized Location Model
    this.activeLocation = {
      name: name || "Kolkata",
      latitude: lat,
      longitude: lon,
      country: country,
      state: state,
      district: district,
      city: city || name || "Kolkata",
      locality: locality,
      sublocality: sublocality,
      neighborhood: neighborhood,
      postalCode: postalCode,
      placeId: placeId,
      formattedAddress: formattedAddress,
      timezone: loc.timezone || "Asia/Kolkata",
      isCurrentLocation: isCurrent
    };
    this.currentLocation = this.activeLocation;

    try {
      localStorage.setItem("weathergpt_active_location", JSON.stringify(this.activeLocation));
    } catch {}

    // Primary prominent display name (local neighborhood / suburb / town first)
    const candidates = [sublocality, neighborhood, locality, name, city];
    let primaryName = candidates.find(x => x && !isCoordString(x));
    if (!primaryName) {
      primaryName = (this.activeLocation && this.activeLocation.name && !isCoordString(this.activeLocation.name))
        ? this.activeLocation.name
        : "Kolkata";
    }
    const secondaryParts = [];
    if (city && city !== primaryName) secondaryParts.push(city);
    if (district && district !== primaryName && district !== city) secondaryParts.push(district);
    if (state && state !== primaryName && state !== city) secondaryParts.push(state);
    if (country && secondaryParts.length < 2) secondaryParts.push(country);

    let fullLabel = primaryName;
    if (secondaryParts.length > 0) {
      fullLabel += `, ${secondaryParts.slice(0, 2).join(", ")}`;
    }

    // 1. Update Navbar Label (No extra pin emoji; #btn-city-dropdown already contains the location pin icon)
    const navLabel = document.getElementById("nav-city-label");
    if (navLabel) {
      if (isCurrent) {
        navLabel.innerHTML = `<span class="text-emerald-500 font-semibold">Current Location:</span> ${this.escapeHTML(fullLabel)}`;
      } else {
        navLabel.textContent = fullLabel;
      }
    }

    // 1.1 Keep search input placeholder ("Search Locations...") visible; do not force place name into input value

    // 1.2 Update Card 1 city name next to Live clock (User Request 4)
    const cardCity = document.getElementById("card-city-name");
    if (cardCity) {
      cardCity.textContent = primaryName.split(",")[0].trim();
    }

    // 1.3 Dedicated small tab for coordinates at bottom of Current Weather platelet
    const elCoords = document.getElementById("card-coordinates-val");
    if (elCoords) {
      const latDir = lat >= 0 ? "N" : "S";
      const lonDir = lon >= 0 ? "E" : "W";
      elCoords.textContent = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
    }

    // 1.4 Immediate Map flyTo & active pin (zero-delay before network requests)
    if (typeof MapController !== "undefined" && MapController.updateActiveLocation) {
      MapController.updateActiveLocation(lat, lon, primaryName, isCurrent);
    }

    // 2. Update Weather Card
    try {
      const queryCity = primaryName || city || name;
      const forecastRes = await apiFetch(`/api/weather/forecast?lat=${lat}&lon=${lon}&city=${encodeURIComponent(queryCity)}`);
      if (forecastRes && forecastRes.ok) {
        const data = await forecastRes.json();
        if (data.current) {
          data.current.city = primaryName;
        }
        WeatherUI.renderHero(data.current);
        WeatherUI.renderMetrics(data.current);
        WeatherUI.renderHourlyForecast(data.hourly_24h);
        WeatherUI.renderDailyForecast(data.daily_7d);
      }
    } catch (e) {
      console.warn("Forecast fetch failure:", e);
    }

    // 3. Update Alerts
    try {
      const alertRegion = primaryName || city;
      const alertRes = await apiFetch(`/api/alerts/active?region=${encodeURIComponent(alertRegion)}&lat=${lat}&lon=${lon}`);
      if (alertRes && alertRes.ok) {
        const alerts = await alertRes.json();
        AlertsUI.renderActiveAlert(alerts);
      }
    } catch (e) {
      console.warn("Alerts fetch failure:", e);
    }
  }

  async updateLocation(name, lat, lon) {
    // Reverse-geocode if name is generic
    let state = "";
    let country = "";
    let cityName = name;
    if (!cityName || cityName.includes("Coords (") || cityName.includes("Location (") || cityName.includes("Selected Location")) {
      try {
        const res = await apiFetch(`/api/weather/reverse-geocode?lat=${lat}&lon=${lon}`);
        if (res && res.ok) {
          const d = await res.json();
          cityName = d.city || d.locality || cityName;
          state = d.state || "";
          country = d.country || "";
        }
      } catch {}
    }
    await this.setActiveLocation({
      latitude: lat,
      longitude: lon,
      city: cityName,
      state: state,
      country: country,
      isCurrentLocation: false
    });
    this.showToast(`📍 Located: ${cityName}${country ? ', ' + country : ''}`, "info");
  }

  openLocationSearch() {
    if (this.globalSearch) {
      this.globalSearch.focus();
      this.globalSearch.placeholder = "Search location";
    }
  }

  // ----------------------------------------------------
  // Supabase UI Wiring (Auth, Saved Locations, Feedback)
  // ----------------------------------------------------

  async initSupabaseUI() {
    // 1. Initialize client
    if (typeof SupabaseService !== "undefined") {
      await SupabaseService.init();
      this.updateAuthHeader();

      SupabaseService.onAuthStateChange((event, user) => {
        this.updateAuthHeader();
        this.loadRecentChats();
      });
    }

    // 2. Wire Header Auth Button
    const btnOpenAuth = document.getElementById("btn-open-auth");
    if (btnOpenAuth) {
      btnOpenAuth.addEventListener("click", () => {
        if (typeof SupabaseService !== "undefined" && SupabaseService.getUser()) {
          // Open Settings or Profile
          const modalSettings = document.getElementById("modal-settings");
          if (modalSettings) {
            modalSettings.classList.remove("hidden");
            modalSettings.classList.add("flex");
          }
        } else {
          this.openAuthModal("signin");
        }
      });
    }

    // 3. Wire GPS Navbar button
    const btnUseGPS = document.getElementById("btn-use-gps");
    if (btnUseGPS) {
      btnUseGPS.addEventListener("click", () => {
        this.requestCurrentLocation();
      });
    }

    // 4. Wire Feedback Button & Modal
    const btnOpenFeedback = document.getElementById("btn-open-feedback");
    const modalFeedback = document.getElementById("modal-feedback");
    const formFeedback = document.getElementById("form-feedback");
    if (btnOpenFeedback && modalFeedback) {
      btnOpenFeedback.addEventListener("click", () => {
        modalFeedback.classList.remove("hidden");
        modalFeedback.classList.add("flex");
      });
    }

    if (formFeedback) {
      let selectedStar = 5;
      const stars = document.querySelectorAll("#feedback-rating-stars .star-btn");
      const starLabel = document.getElementById("feedback-rating-label");
      stars.forEach(s => {
        s.addEventListener("click", () => {
          selectedStar = parseInt(s.getAttribute("data-star"), 10);
          stars.forEach((st, idx) => {
            st.classList.toggle("text-amber-400", idx < selectedStar);
            st.classList.toggle("text-slate-300", idx >= selectedStar);
          });
          if (starLabel) starLabel.textContent = `${selectedStar} Stars`;
        });
      });

      formFeedback.addEventListener("submit", async (e) => {
        e.preventDefault();
        const cat = document.getElementById("feedback-category").value;
        const comment = document.getElementById("feedback-comment").value;
        const alertBox = document.getElementById("feedback-alert");

        try {
          if (typeof SupabaseService !== "undefined") {
            await SupabaseService.submitFeedback(selectedStar, cat, comment);
          }
          if (alertBox) {
            alertBox.className = "p-3 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 block";
            alertBox.textContent = "Thank you! Your feedback has been received.";
          }
          setTimeout(() => {
            if (modalFeedback) {
              modalFeedback.classList.add("hidden");
              modalFeedback.classList.remove("flex");
            }
            formFeedback.reset();
            if (alertBox) alertBox.classList.add("hidden");
          }, 1600);
        } catch (err) {
          if (alertBox) {
            alertBox.className = "p-3 rounded-xl text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 block";
            alertBox.textContent = err.message || "Feedback submission error";
          }
        }
      });
    }

    // 5. Wire Auth Modal Forms
    this.wireAuthForms();

    // 6. Wire Saved Locations Modal
    this.wireSavedLocations();
  }

  updateAuthHeader() {
    const navUserLabel = document.getElementById("nav-user-label");
    const profileName = document.getElementById("user-profile-name");
    const profileEmail = document.getElementById("user-profile-email");

    if (typeof SupabaseService !== "undefined" && SupabaseService.getUser()) {
      const u = SupabaseService.getUser();
      const name = SupabaseService.getUserDisplayName();
      if (navUserLabel) navUserLabel.textContent = name;
      if (profileName) profileName.textContent = name;
      if (profileEmail) profileEmail.textContent = u.email;
    } else {
      if (navUserLabel) navUserLabel.textContent = "Sign In";
      if (profileName) profileName.textContent = "Guest User";
      if (profileEmail) profileEmail.textContent = "Sign in with Supabase to sync";
    }
  }

  openAuthModal(mode = "signin") {
    const modal = document.getElementById("modal-auth");
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    this.switchAuthTab(mode);
  }

  switchAuthTab(mode) {
    const tabSignin = document.getElementById("auth-tab-signin");
    const tabSignup = document.getElementById("auth-tab-signup");
    const tabForgot = document.getElementById("auth-tab-forgot");
    const formSignin = document.getElementById("form-auth-signin");
    const formSignup = document.getElementById("form-auth-signup");
    const formForgot = document.getElementById("form-auth-forgot");
    const title = document.getElementById("auth-title");
    const alertBox = document.getElementById("auth-alert");
    if (alertBox) alertBox.classList.add("hidden");

    [tabSignin, tabSignup, tabForgot].forEach(t => {
      if (t) t.className = "flex-1 py-1.5 rounded-lg text-slate-500 hover:text-slate-900 transition";
    });
    [formSignin, formSignup, formForgot].forEach(f => {
      if (f) f.classList.add("hidden");
    });

    if (mode === "signin") {
      if (tabSignin) tabSignin.className = "flex-1 py-1.5 rounded-lg bg-white text-slate-900 shadow-sm transition";
      if (formSignin) formSignin.classList.remove("hidden");
      if (title) title.textContent = "Sign In to WeatherGPT";
    } else if (mode === "signup") {
      if (tabSignup) tabSignup.className = "flex-1 py-1.5 rounded-lg bg-white text-slate-900 shadow-sm transition";
      if (formSignup) formSignup.classList.remove("hidden");
      if (title) title.textContent = "Create Free Account";
    } else if (mode === "forgot") {
      if (tabForgot) tabForgot.className = "flex-1 py-1.5 rounded-lg bg-white text-slate-900 shadow-sm transition";
      if (formForgot) formForgot.classList.remove("hidden");
      if (title) title.textContent = "Reset Your Password";
    }
  }

  wireAuthForms() {
    const tabSignin = document.getElementById("auth-tab-signin");
    const tabSignup = document.getElementById("auth-tab-signup");
    const tabForgot = document.getElementById("auth-tab-forgot");
    if (tabSignin) tabSignin.addEventListener("click", () => this.switchAuthTab("signin"));
    if (tabSignup) tabSignup.addEventListener("click", () => this.switchAuthTab("signup"));
    if (tabForgot) tabForgot.addEventListener("click", () => this.switchAuthTab("forgot"));

    const formSignin = document.getElementById("form-auth-signin");
    const formSignup = document.getElementById("form-auth-signup");
    const formForgot = document.getElementById("form-auth-forgot");
    const alertBox = document.getElementById("auth-alert");

    const showAlert = (msg, isError = true) => {
      if (!alertBox) return;
      alertBox.className = isError
        ? "p-3 rounded-xl text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 block"
        : "p-3 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 block";
      alertBox.textContent = msg;
    };

    if (formSignin) {
      formSignin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("signin-email").value;
        const pass = document.getElementById("signin-password").value;
        try {
          if (typeof SupabaseService === "undefined" || !SupabaseService.isConfigured) {
            showAlert("Supabase URL is not configured yet in .env. Logging in as guest session.", false);
            setTimeout(() => {
              document.getElementById("modal-auth").classList.add("hidden");
            }, 1200);
            return;
          }
          await SupabaseService.signIn(email, pass);
          showAlert("Signed in successfully!", false);
          setTimeout(() => {
            document.getElementById("modal-auth").classList.add("hidden");
            this.updateAuthHeader();
          }, 800);
        } catch (err) {
          showAlert(err.message || "Sign in failed");
        }
      });
    }

    if (formSignup) {
      formSignup.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("signup-name").value;
        const email = document.getElementById("signup-email").value;
        const pass = document.getElementById("signup-password").value;
        try {
          if (typeof SupabaseService === "undefined" || !SupabaseService.isConfigured) {
            showAlert("Supabase URL is not configured in .env. Please configure your project URL.", true);
            return;
          }
          await SupabaseService.signUp(email, pass, name);
          showAlert("Account created! Please check your email to confirm or sign in.", false);
        } catch (err) {
          showAlert(err.message || "Sign up failed");
        }
      });
    }

    if (formForgot) {
      formForgot.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("forgot-email").value;
        try {
          if (typeof SupabaseService === "undefined" || !SupabaseService.isConfigured) {
            showAlert("Supabase URL is not configured in .env.", true);
            return;
          }
          await SupabaseService.resetPassword(email);
          showAlert("Password reset email sent!", false);
        } catch (err) {
          showAlert(err.message || "Password reset failed");
        }
      });
    }
  }

  wireSavedLocations() {
    const navSaved = document.getElementById("nav-saved");
    const modalSaved = document.getElementById("modal-saved");
    const btnSaveCurrent = document.getElementById("btn-save-current-location");

    if (navSaved && modalSaved) {
      navSaved.addEventListener("click", async (e) => {
        e.preventDefault();
        modalSaved.classList.remove("hidden");
        modalSaved.classList.add("flex");
        await this.renderSavedLocations();
      });
    }

    if (btnSaveCurrent) {
      btnSaveCurrent.addEventListener("click", async () => {
        if (!this.activeLocation || !this.activeLocation.latitude) {
          this.showToast("⚠️ No active location to save. Detect or search a location first.", "error");
          return;
        }
        try {
          if (typeof SupabaseService !== "undefined") {
            await SupabaseService.addSavedLocation({
              name: this.activeLocation.city,
              state: this.activeLocation.state || "",
              country: this.activeLocation.country || "India",
              latitude: this.activeLocation.latitude,
              longitude: this.activeLocation.longitude
            });
            this.showToast(`⭐ Bookmarked: ${this.activeLocation.city}`, "success");
            await this.renderSavedLocations();
          }
        } catch (err) {
          this.showToast(`Failed to save: ${err.message}`, "error");
        }
      });
    }
  }

  async renderSavedLocations() {
    const container = document.getElementById("saved-locations-list");
    if (!container) return;

    let locs = [];
    if (typeof SupabaseService !== "undefined") {
      locs = await SupabaseService.getSavedLocations();
    }

    if (!locs || locs.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-slate-400">No saved locations yet.<br>Click "Bookmark Active Location" above to save one!</div>`;
      return;
    }

    container.innerHTML = "";
    locs.forEach(l => {
      const div = document.createElement("div");
      div.className = "flex items-center justify-between p-2.5 bg-slate-50 hover:bg-blue-50/60 rounded-xl border border-slate-200 transition cursor-pointer";
      div.innerHTML = `
        <div class="flex items-center gap-2.5">
          <i class="fa-solid fa-location-dot text-rose-500 text-sm"></i>
          <div>
            <strong class="text-slate-800 font-semibold block text-xs">${this.escapeHTML(l.name)}</strong>
            <span class="text-[10px] text-slate-400">${this.escapeHTML(l.state || l.country || "India")}</span>
          </div>
        </div>
        <button class="btn-del-saved text-slate-400 hover:text-rose-600 p-1.5" title="Remove">✕</button>
      `;

      div.addEventListener("click", (e) => {
        if (e.target.classList.contains("btn-del-saved")) return;
        this.setActiveLocation({
          latitude: l.latitude,
          longitude: l.longitude,
          city: l.name,
          state: l.state,
          country: l.country,
          isCurrentLocation: false
        });
        document.getElementById("modal-saved").classList.add("hidden");
      });

      const delBtn = div.querySelector(".btn-del-saved");
      if (delBtn) {
        delBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (typeof SupabaseService !== "undefined") {
            await SupabaseService.removeSavedLocation(l.id);
            await this.renderSavedLocations();
          }
        });
      }

      container.appendChild(div);
    });
  }

  async bootstrap() {
    // 1. By default set the location strictly to Kolkata (User requirement: no auto geolocation on open/refresh)
    try {
      localStorage.removeItem("weathergpt_active_location");
    } catch {}
    await this.setActiveLocation({
      latitude: 22.5726,
      longitude: 88.3639,
      city: "Kolkata",
      state: "West Bengal",
      country: "India",
      isCurrentLocation: false
    });

    // 2. Load stored SQLite conversation sessions into left sidebar "Recent chats"
    await this.loadRecentChats();

    // 3. User requirement: Do NOT stay stuck on previous chat on open or refresh! Start fresh chat!
    this.startNewChat();
  }

  async setLanguage(langCode) {
    if (this.currentLanguage === langCode) return;
    this.currentLanguage = langCode;

    // 1. Update Dropdown Label
    const labels = {
      en: "English (EN)",
      hi: "हिन्दी (HI)",
      bn: "বাংলা (BN)"
    };
    if (this.langLabel) {
      this.langLabel.textContent = labels[langCode] || "English (EN)";
    }

    // 2. Show Translation Toast immediately
    this.showTranslationToast(langCode);
    const startTime = Date.now();

    // 3. Immediately Translate Entire Tab / UI Elements
    this.applyTabTranslations(langCode);

    // 4. Concurrently translate active chat messages if present via FastAPI /api/translate
    const assistantRows = this.messagesContainer?.querySelectorAll(".assistant-message-row");
    if (assistantRows && assistantRows.length > 0) {
      try {
        const transPromises = Array.from(assistantRows).map(async (row) => {
          const rawText = row.dataset.rawText;
          if (!rawText) return;

          const res = await apiFetch("/api/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text: rawText,
              target_language: langCode,
              session_id: this.sessionId
            })
          });

          if (res && res.ok) {
            const data = await res.json();
            const translated = data.translated_text;
            row.dataset.rawText = translated;
            const contentEl = row.querySelector(".assistant-text-content");
            if (contentEl) {
              contentEl.innerHTML = formatMarkdown(translated);
            }
          }
        });
        await Promise.allSettled(transPromises);
      } catch (err) {
        console.warn("Message translation error:", err);
      }
    }

    // 5. Enforce crisp 2.0 to 2.3 seconds duration per user specification ("in 2-3 seconds")
    const elapsed = Date.now() - startTime;
    const remaining = Math.max(400, 2100 - elapsed);
    setTimeout(() => {
      this.finishTranslationToast(langCode);
    }, remaining);
  }

  applyTabTranslations(langCode) {
    const t = UI_TRANSLATIONS[langCode] || UI_TRANSLATIONS.en;

    // 1. Navigation items
    const setNavSpan = (id, text) => {
      const el = document.getElementById(id);
      if (!el) return;
      const spans = el.querySelectorAll("span");
      for (const sp of spans) {
        if (!sp.classList.contains("rounded-full")) {
          sp.textContent = text;
          break;
        }
      }
    };
    setNavSpan("nav-chat", t.nav_chat);
    setNavSpan("nav-drought", t.nav_drought);
    setNavSpan("nav-alerts", t.nav_alerts);
    setNavSpan("nav-climate", t.nav_climate);
    setNavSpan("nav-disaster", t.nav_disaster);
    setNavSpan("nav-saved", t.nav_saved);

    // Live 3D badge on map nav
    const mapBadge = document.querySelector("#nav-map span.rounded-full");
    if (mapBadge) mapBadge.textContent = t.nav_map_badge;

    // Brand sub title
    const brandSub = document.getElementById("brand-sub-title");
    if (brandSub) brandSub.textContent = t.brand_sub;

    // New Chat button
    const newChatSpan = document.querySelector("#new-chat-btn span");
    if (newChatSpan) newChatSpan.textContent = t.new_chat;

    // Recent chats heading
    const recentHeading = document.getElementById("heading-recent-chats");
    if (recentHeading) recentHeading.textContent = t.recent_chats;

    // Global search placeholder
    if (this.globalSearch) {
      this.globalSearch.placeholder = t.search_placeholder;
    }

    // Welcome banner
    if (this.welcomeBanner) {
      const h2 = this.welcomeBanner.querySelector("h2");
      const p = this.welcomeBanner.querySelector("p");
      if (h2) h2.innerHTML = t.welcome_title;
      if (p) p.textContent = t.welcome_sub;
    }

    // Prompt pills (text and click prompt)
    const pillButtons = document.querySelectorAll(".prompt-pill");
    if (pillButtons && t.prompt_pills) {
      pillButtons.forEach((pill, idx) => {
        if (t.prompt_pills[idx]) {
          pill.innerHTML = t.prompt_pills[idx].text;
          pill.dataset.prompt = t.prompt_pills[idx].prompt;
        }
      });
    }

    // Chat input placeholder & Send button
    if (this.chatInput) {
      this.chatInput.placeholder = t.chat_placeholder;
    }
    const sendSpan = document.querySelector("#btn-send-message span");
    if (sendSpan) sendSpan.textContent = t.send_btn;

    // Disclaimer
    const disclaimer = document.getElementById("chat-disclaimer-text");
    if (disclaimer) disclaimer.textContent = t.disclaimer;

    // Right Panel: Weather cards
    const curHeading = document.getElementById("card-current-heading");
    if (curHeading) curHeading.textContent = t.current_weather;

    const feelsLabel = document.getElementById("card-feels-label");
    if (feelsLabel) feelsLabel.textContent = t.feels_like;

    const lblHumidity = document.getElementById("lbl-humidity");
    if (lblHumidity) lblHumidity.textContent = t.humidity;

    const lblWind = document.getElementById("lbl-wind");
    if (lblWind) lblWind.textContent = t.wind;

    const lblPressure = document.getElementById("lbl-pressure");
    if (lblPressure) lblPressure.textContent = t.pressure;

    const lblVisibility = document.getElementById("lbl-visibility");
    if (lblVisibility) lblVisibility.textContent = t.visibility;

    const lblAqi = document.getElementById("lbl-aqi");
    if (lblAqi) lblAqi.textContent = t.aqi;

    const forecastHeading = document.getElementById("card-forecast-heading");
    if (forecastHeading) forecastHeading.textContent = t.forecast_heading;

    const hourlyHeading = document.getElementById("card-hourly-heading");
    if (hourlyHeading) hourlyHeading.textContent = t.hourly_heading || "Hourly Forecast (24h)";

    const alertsHeading = document.getElementById("card-alerts-heading");
    if (alertsHeading) alertsHeading.textContent = t.alerts_heading;

    const viewAlertsText = document.getElementById("btn-view-all-alerts-text");
    if (viewAlertsText) viewAlertsText.textContent = t.view_alerts;

    // Refresh active alert card in chosen language
    if (typeof AlertsUI !== "undefined" && AlertsUI.renderActiveAlert) {
      AlertsUI.renderActiveAlert(AlertsUI.activeAlerts);
    }
  }

  showTranslationToast(langCode) {
    if (!this.translationToast) return;
    const t = UI_TRANSLATIONS[langCode] || UI_TRANSLATIONS.en;
    if (this.translationToastIcon) {
      this.translationToastIcon.className = "fa-solid fa-arrows-rotate animate-spin text-blue-400 text-sm";
    }
    if (this.translationToastText) {
      this.translationToastText.textContent = t.toast_converting;
    }
    this.translationToast.classList.remove("hidden");
    this.translationToast.classList.add("flex");
  }

  finishTranslationToast(langCode) {
    if (!this.translationToast) return;
    const t = UI_TRANSLATIONS[langCode] || UI_TRANSLATIONS.en;
    if (this.translationToastIcon) {
      this.translationToastIcon.className = "fa-solid fa-check text-emerald-400 text-sm";
    }
    if (this.translationToastText) {
      this.translationToastText.textContent = t.toast_done;
    }
    setTimeout(() => {
      this.translationToast.classList.add("hidden");
      this.translationToast.classList.remove("flex");
    }, 1100);
  }

  async searchLocations(query) {
    if (!this.searchDropdown) return;
    const cleanQ = (query || "").trim();
    if (cleanQ.length < 2) {
      this.searchDropdown.classList.add("hidden");
      return;
    }

    const cacheKey = cleanQ.toLowerCase();

    // 1. Instant Cache Hit (0ms response)
    if (this.clientSearchCache && this.clientSearchCache.has(cacheKey)) {
      const cachedItems = this.clientSearchCache.get(cacheKey);
      this.renderSearchResults(cleanQ, cachedItems);
      return;
    }

    // Cancel any previous in-flight request
    if (this.searchAbortController) {
      this.searchAbortController.abort();
    }
    this.searchAbortController = new AbortController();
    const currentSignal = this.searchAbortController.signal;

    // Instant searching feedback
    this.searchDropdown.innerHTML = `
      <div class="px-4 py-3 text-xs text-slate-500 flex items-center justify-center gap-2">
        <i class="fa-solid fa-circle-notch fa-spin text-blue-600 text-xs"></i>
        <span>Searching matching locations for "<strong>${this.escapeHTML(cleanQ)}</strong>"...</span>
      </div>
    `;
    this.searchDropdown.classList.remove("hidden");

    try {
      let items = null;

      // 2. Primary: backend search with fast weather preview (strict 1.8s timeout)
      try {
        const tid = setTimeout(() => {
          if (this.searchAbortController && !currentSignal.aborted) {
            this.searchAbortController.abort();
          }
        }, 1800);
        const res = await fetch(`/api/weather/search?q=${encodeURIComponent(cleanQ)}&include_weather=true&limit=6`, { signal: currentSignal });
        clearTimeout(tid);
        if (res && res.ok) {
          items = await res.json();
        }
      } catch (errW) {
        if (errW.name !== "AbortError") {
          console.warn("Search with weather timed out, trying fast search without weather:", errW);
        }
      }

      // 3. Fallback: fast search without weather if primary was slow
      if (!items && !currentSignal.aborted) {
        try {
          const fastRes = await apiFetch(`/api/weather/search?q=${encodeURIComponent(cleanQ)}&include_weather=false&limit=6`);
          if (fastRes && fastRes.ok) {
            items = await fastRes.json();
          }
        } catch (errF) {
          console.warn("Backend fast search failed:", errF);
        }
      }

      // 3. Direct client OSM Nominatim fallback if backend unreachable
      if (!items || items.length === 0) {
        try {
          const directRes = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cleanQ)}&format=json&addressdetails=1&accept-language=en&limit=6`);
          if (directRes.ok) {
            const rawData = await directRes.json();
            if (Array.isArray(rawData) && rawData.length > 0) {
              items = rawData.map(it => {
                const addr = it.address || {};
                const name = it.name || addr.suburb || addr.city || addr.town || addr.state || cleanQ;
                const parts = [name, addr.city || addr.town, addr.state, addr.country].filter(Boolean);
                const uniqueParts = [...new Set(parts)];
                return {
                  name,
                  city: addr.city || addr.town || name,
                  state: addr.state || "",
                  country: addr.country || "",
                  latitude: parseFloat(it.lat),
                  longitude: parseFloat(it.lon),
                  formattedAddress: uniqueParts.join(", ")
                };
              });
            }
          }
        } catch (nomErr) {
          console.warn("Direct client Nominatim fallback failed:", nomErr);
        }
      }

      if (items && items.length > 0) {
        if (this.clientSearchCache) {
          this.clientSearchCache.set(cacheKey, items);
        }
      }

      this.renderSearchResults(cleanQ, items);
    } catch (e) {
      console.warn("Search fetch failed:", e);
    }
  }

  renderSearchResults(cleanQ, items) {
    if (!this.searchDropdown) return;
    this.searchDropdown.innerHTML = "";

    if (!items || items.length === 0) {
      this.searchDropdown.innerHTML = `
        <div class="px-4 py-3 text-xs text-slate-500 text-center">
          No matching locations found for "<strong>${this.escapeHTML(cleanQ)}</strong>"
        </div>
      `;
      this.searchDropdown.classList.remove("hidden");
      return;
    }

    // Header Component (Matching Pic 2)
    const headerEl = document.createElement("div");
    headerEl.className = "px-4 py-2.5 bg-slate-50/95 backdrop-blur-xs border-b border-slate-200/80 sticky top-0 z-10";
    headerEl.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-bold tracking-wider text-slate-700 uppercase flex items-center gap-1.5">
          <i class="fa-solid fa-layer-group text-blue-600 text-xs"></i>
          MATCHING LOCATIONS (${items.length})
        </span>
      </div>
      <p class="text-[11px] text-slate-400 mt-0.5">Showing all matching locations returned by the location service.</p>
    `;
    this.searchDropdown.appendChild(headerEl);

    // Location Cards
    items.forEach(loc => {
      const card = document.createElement("div");
      card.className = "p-3 hover:bg-blue-50/40 border-b border-slate-100 last:border-b-0 transition flex flex-col gap-2 cursor-pointer";

      const primaryName = loc.name || loc.sublocality || loc.neighborhood || loc.locality || loc.city || "Location";
      
      const hierarchyParts = [];
      if (loc.city && loc.city !== primaryName) hierarchyParts.push(loc.city);
      if (loc.district && loc.district !== primaryName && loc.district !== loc.city) hierarchyParts.push(loc.district);
      if (loc.state && loc.state !== primaryName && loc.state !== loc.city) hierarchyParts.push(loc.state);
      if (loc.country) hierarchyParts.push(loc.country);
      const secondaryText = hierarchyParts.length > 0 ? hierarchyParts.join(", ") : (loc.formattedAddress || "");

      const latNum = parseFloat(loc.latitude != null ? loc.latitude : loc.lat) || 0;
      const lonNum = parseFloat(loc.longitude != null ? loc.longitude : loc.lon) || 0;
      const coordsText = `Lat: ${latNum.toFixed(4)}, Lon: ${lonNum.toFixed(4)}`;

      let weatherBadgeHTML = "";
      if (loc.weather) {
        const temp = Math.round(loc.weather.temperature);
        const feels = Math.round(loc.weather.feels_like);
        const desc = loc.weather.weather_desc || "Clear";
        const icon = loc.weather.weather_icon || "☀️";
        const hum = loc.weather.humidity != null ? `${loc.weather.humidity}%` : "--";
        const wind = loc.weather.wind_speed != null ? `${Math.round(loc.weather.wind_speed)} km/h` : "--";

        weatherBadgeHTML = `
          <div class="flex items-center justify-between bg-slate-50/90 rounded-xl px-2.5 py-1.5 border border-slate-200/60 text-[11px]">
            <div class="flex items-center gap-1.5 text-slate-800 font-bold">
              <span class="text-sm">${icon}</span>
              <span>${temp}°C</span>
              <span class="text-slate-500 font-normal text-[10px]">• ${desc}</span>
            </div>
            <div class="flex items-center gap-2 text-[10px] text-slate-500">
              <span>Feels ${feels}°C</span>
              <span>• Hum ${hum}</span>
              <span>• Wind ${wind}</span>
            </div>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="flex items-start justify-between gap-2.5">
          <div class="min-w-0 flex-1">
            <div class="font-bold text-slate-800 text-xs truncate flex items-center gap-1.5">
              <i class="fa-solid fa-location-dot text-blue-600 text-[11px] shrink-0"></i>
              <span class="truncate">${this.escapeHTML(primaryName)}</span>
            </div>
            <div class="text-slate-500 text-[11px] truncate mt-0.5">${this.escapeHTML(secondaryText)}</div>
            <div class="text-slate-400 text-[10px] font-mono mt-0.5">${coordsText}</div>
          </div>
          <button class="btn-select-location px-3 py-1.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-[11px] font-semibold rounded-lg shrink-0 transition shadow-xs flex items-center gap-1">
            Select
          </button>
        </div>
        ${weatherBadgeHTML}
      `;

      const selectHandler = (e) => {
        e.stopPropagation();
        this.setActiveLocation({
          ...loc,
          isCurrentLocation: false
        });
        if (this.searchDropdown) this.searchDropdown.classList.add("hidden");
        if (this.globalSearch) this.globalSearch.value = "";
      };

      card.addEventListener("click", selectHandler);
      const btn = card.querySelector(".btn-select-location");
      if (btn) btn.addEventListener("click", selectHandler);

      this.searchDropdown.appendChild(card);
    });

    this.searchDropdown.classList.remove("hidden");
  }


  async loadNationalAlerts() {
    try {
      const res = await apiFetch("/api/alerts/national");
      if (res && res.ok) {
        const alerts = await res.json();
        AlertsUI.renderNationalModal(alerts);
      }
    } catch (e) {
      console.error("Failed to load national alerts:", e);
    }
  }

  // ========================================================
  // Conversation History & SQLite Storage Methods
  // ========================================================

  openDeleteModal({ type, sessionId, message }) {
    this.pendingDeleteType = type; // "single" or "all"
    this.pendingDeleteSessionId = sessionId || null;
    if (this.confirmDeleteMsg) {
      this.confirmDeleteMsg.textContent = message || "Do you really want to delete this message?";
    }
    if (this.modalConfirmDelete) {
      this.modalConfirmDelete.classList.remove("hidden");
      this.modalConfirmDelete.classList.add("flex");
    }
  }

  closeDeleteModal() {
    if (this.modalConfirmDelete) {
      this.modalConfirmDelete.classList.add("hidden");
      this.modalConfirmDelete.classList.remove("flex");
    }
    this.pendingDeleteType = null;
    this.pendingDeleteSessionId = null;
  }

  async handleConfirmDelete() {
    const type = this.pendingDeleteType;
    const targetSessionId = this.pendingDeleteSessionId;
    this.closeDeleteModal();

    if (type === "all") {
      try {
        await apiFetch("/api/conversations", { method: "DELETE" });
      } catch (e) {
        console.warn("Error clearing chat history:", e);
      }
      this.startNewChat();
    } else if (type === "single" && targetSessionId) {
      try {
        await apiFetch(`/api/chat/sessions/${targetSessionId}`, { method: "DELETE" });
      } catch (e) {
        console.warn("Error deleting session:", e);
      }
      if (this.sessionId === targetSessionId) {
        this.startNewChat();
      } else {
        await this.loadRecentChats();
      }
    }
  }

  async loadRecentChats() {
    if (!this.recentChatsList) return;
    try {
      const res = await apiFetch("/api/conversations");
      if (res && res.ok) {
        const sessions = await res.json();
        this.recentChatsList.innerHTML = "";

        if (sessions.length === 0) {
          this.recentChatsList.innerHTML = `<p class="text-[11px] text-slate-400 py-2 px-1 italic">No past conversations</p>`;
          return;
        }

        sessions.slice(0, 15).forEach(s => {
          const itemWrap = document.createElement("div");
          const isActive = s.id === this.sessionId;
          itemWrap.className = `w-full flex items-center gap-1.5 p-1 rounded-xl transition text-xs group ${
            isActive ? "bg-blue-50 text-blue-700 font-semibold border border-blue-200 shadow-xs" : "hover:bg-slate-100 text-slate-700"
          }`;

          const cleanTitle = s.title || "Weather Consultation";
          const displayTime = s.time_display || this.formatDate(s.updated_at);

          // User Request: Dustbin symbol to the LEFT side of each Recent history message
          const btnTrash = document.createElement("button");
          btnTrash.type = "button";
          btnTrash.className = "w-6 h-6 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center shrink-0 transition";
          btnTrash.title = "Delete message";
          btnTrash.innerHTML = `<i class="fa-regular fa-trash-can text-[11px]"></i>`;
          btnTrash.addEventListener("click", (e) => {
            e.stopPropagation();
            this.openDeleteModal({
              type: "single",
              sessionId: s.id,
              message: "Do you really want to delete this message?"
            });
          });

          const btnText = document.createElement("button");
          btnText.type = "button";
          btnText.className = "flex-1 text-left py-1 pr-1.5 flex items-center justify-between min-w-0";
          btnText.innerHTML = `
            <span class="truncate ${isActive ? 'font-semibold text-blue-700' : 'text-slate-700'}">${this.escapeHTML(cleanTitle)}</span>
            <span class="text-slate-400 shrink-0 text-[10px] font-medium ml-1.5">${displayTime}</span>
          `;
          btnText.addEventListener("click", () => {
            this.switchSession(s.id);
          });

          itemWrap.appendChild(btnTrash);
          itemWrap.appendChild(btnText);
          this.recentChatsList.appendChild(itemWrap);
        });
      }
    } catch (e) {
      console.warn("Could not load recent chats:", e);
    }
  }

  async loadSessionMessages(sessionId) {
    if (!sessionId) return;
    try {
      const res = await apiFetch(`/api/conversations/${sessionId}`);
      if (res && res.ok) {
        const messages = await res.json();
        if (messages.length > 0) {
          if (this.welcomeBanner) this.welcomeBanner.classList.add("hidden");
          this.messagesContainer.innerHTML = "";
          messages.forEach(m => {
            const timeStr = m.time_display || this.formatTime(m.created_at);
            if (m.role === "user") {
              this.appendUserMessage(m.content, timeStr);
            } else {
              this.appendAssistantMessage(m.content, m.weather_data, timeStr, m.id, m.matching_locations || m.weather_data?.matching_locations);
            }
          });
        }
      }
    } catch (e) {
      console.warn("Failed to load session messages:", e);
    }
  }

  switchSession(sessionId) {
    this.sessionId = sessionId;
    try {
      localStorage.setItem("weathergpt_active_session_id", sessionId);
    } catch {}
    this.loadSessionMessages(sessionId);
    this.loadRecentChats();
  }

  startNewChat() {
    this.sessionId = this.createNewSessionId();
    try {
      localStorage.setItem("weathergpt_active_session_id", this.sessionId);
    } catch {}
    if (this.messagesContainer) this.messagesContainer.innerHTML = "";
    if (this.welcomeBanner) this.welcomeBanner.classList.remove("hidden");
    if (this.chatInput) {
      this.chatInput.value = "";
      this.chatInput.focus();
    }
    this.loadRecentChats();
  }

  setChatGeneratingState(isGenerating) {
    this.isGenerating = !!isGenerating;
    if (!this.btnSend) return;

    if (this.isGenerating) {
      // Turn into the Cancel / Stop generation button just like the user's uploaded image
      this.btnSend.className = "h-9 w-9 p-0 rounded-full bg-[#1e2229] hover:bg-[#2d323b] active:scale-90 text-white flex items-center justify-center transition-all shadow-md border border-slate-700/80 cursor-pointer shrink-0";
      this.btnSend.title = "Cancel / Stop generation";
      this.btnSend.disabled = false;
      this.btnSend.innerHTML = `
        <span class="w-3.5 h-3.5 bg-[#e05a5a] rounded-[2.5px] block shadow-xs transition-transform hover:scale-110 pointer-events-none"></span>
      `;
    } else {
      // Revert back to the standard Send button
      const sendText = (typeof UI_TRANSLATIONS !== "undefined" && UI_TRANSLATIONS[this.currentLanguage]?.send_btn) || "Send";
      this.btnSend.className = "h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-medium text-sm flex items-center justify-center gap-1.5 shadow-sm transition cursor-pointer shrink-0";
      this.btnSend.title = "Send Message";
      this.btnSend.disabled = false;
      this.btnSend.innerHTML = `
        <span>${sendText}</span>
        <i class="fa-regular fa-paper-plane text-xs"></i>
      `;
    }
  }

  cancelCurrentMessage() {
    if (!this.isGenerating) return;

    if (this.chatAbortController) {
      try {
        this.chatAbortController.abort();
      } catch {}
      this.chatAbortController = null;
    }

    if (this.currentTypingId) {
      this.removeTypingIndicator(this.currentTypingId);
      this.currentTypingId = null;
    }

    this.setChatGeneratingState(false);

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    this.appendAssistantMessage("*Message cancelled*", null, timeStr);
    this.showToast("⏹️ Message cancelled", "info");

    if (this.chatInput) {
      this.chatInput.focus();
    }
  }

  async handleSendMessage() {
    if (this.isGenerating) {
      this.cancelCurrentMessage();
      return;
    }

    const text = this.chatInput ? this.chatInput.value.trim() : "";
    if (!text) return;

    // Check if user is asking for their current location before coordinates are resolved
    const isLocQuery = /\b(my location|here|near me|current location|where i am|at my location)\b/i.test(text);
    if (isLocQuery && (!this.activeLocation || !this.activeLocation.latitude)) {
      if (this.welcomeBanner) this.welcomeBanner.classList.add("hidden");
      if (this.chatInput) this.chatInput.value = "";
      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      this.appendUserMessage(text, timeStr);
      this.currentTypingId = this.showTypingIndicator();
      this.setChatGeneratingState(true);

      this.requestCurrentLocation(async (resolvedLoc) => {
        if (this.currentTypingId) {
          this.removeTypingIndicator(this.currentTypingId);
          this.currentTypingId = null;
        }
        await this.sendChatPayload(text, timeStr);
      });
      return;
    }

    if (this.welcomeBanner) this.welcomeBanner.classList.add("hidden");
    if (this.chatInput) this.chatInput.value = "";

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    this.appendUserMessage(text, timeStr);

    this.chatAbortController = new AbortController();
    this.setChatGeneratingState(true);
    this.currentTypingId = this.showTypingIndicator();

    try {
      const locName = this.activeLocation.formattedAddress || 
        [this.activeLocation.sublocality, this.activeLocation.locality, this.activeLocation.city, this.activeLocation.state].filter(Boolean).join(", ") || 
        this.activeLocation.name || 
        this.activeLocation.city || 
        "Active Location";

      const res = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: text,
          language: this.currentLanguage,
          location: locName,
          latitude: this.activeLocation.latitude,
          longitude: this.activeLocation.longitude
        }),
        signal: this.chatAbortController.signal
      });

      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }

      if (res && res.ok) {
        const data = await res.json();
        const resTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.appendAssistantMessage(data.reply, data.weather, resTime, null, data.matching_locations);

        // Immediate Map flyTo & active pin when an explicit location is queried
        const isGreeting = /^(hi+|he+y+|hello+|namaste|pranam|greetings|good\s+(morning|afternoon|evening|day)|how\s+are\s+you|kemon\s+acho|kaise\s+ho)\b/i.test(text.trim());
        if (!isGreeting && data.weather && data.weather.latitude != null && data.weather.longitude != null) {
          const currentLat = this.activeLocation?.latitude;
          const currentLon = this.activeLocation?.longitude;
          const hasMoved = currentLat == null || currentLon == null ||
            Math.abs(data.weather.latitude - currentLat) > 0.005 ||
            Math.abs(data.weather.longitude - currentLon) > 0.005;
          const cityChanged = data.weather.city && (!this.activeLocation || data.weather.city !== this.activeLocation.city);

          if (hasMoved || cityChanged) {
            if (typeof MapController !== "undefined" && MapController.updateActiveLocation) {
              MapController.updateActiveLocation(data.weather.latitude, data.weather.longitude, data.weather.city || "Active Location", false);
            }
            await this.setActiveLocation({
              latitude: data.weather.latitude,
              longitude: data.weather.longitude,
              city: data.weather.city,
              name: data.weather.city,
              isCurrentLocation: false
            });
          }
        }

        if (data.alerts) {
          AlertsUI.renderActiveAlert(data.alerts);
        }

        // Sync message to Supabase chat_history
        if (typeof SupabaseService !== "undefined") {
          SupabaseService.saveChatMessage(this.sessionId, text, data.reply, this.activeLocation.city);
        }

        // Refresh stored conversation list in left sidebar
        await this.loadRecentChats();

      } else {
        this.appendAssistantMessage("Sorry, I could not retrieve weather intelligence at this moment. Please try again.", null, timeStr);
      }
    } catch (e) {
      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }
      if (e.name === "AbortError" || (this.chatAbortController && this.chatAbortController.signal.aborted)) {
        // Already handled by cancelCurrentMessage
        return;
      }
      console.error("Chat API fetch failure:", e);
      this.appendAssistantMessage("Unable to connect to WeatherGPT server. Please verify FastAPI is active on port 8000.", null, timeStr);
    } finally {
      this.setChatGeneratingState(false);
      this.chatAbortController = null;
      this.currentTypingId = null;
      if (this.chatInput) this.chatInput.focus();
    }
  }


  async sendChatPayload(text, timeStr) {
    this.chatAbortController = new AbortController();
    this.setChatGeneratingState(true);
    this.currentTypingId = this.showTypingIndicator();

    try {
      const locName = this.activeLocation.formattedAddress || 
        [this.activeLocation.sublocality, this.activeLocation.locality, this.activeLocation.city, this.activeLocation.state].filter(Boolean).join(", ") || 
        this.activeLocation.name || 
        this.activeLocation.city || 
        "Active Location";

      const res = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: text,
          language: this.currentLanguage,
          location: locName,
          latitude: this.activeLocation.latitude,
          longitude: this.activeLocation.longitude
        }),
        signal: this.chatAbortController.signal
      });

      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }

      if (res && res.ok) {
        const data = await res.json();
        const resTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.appendAssistantMessage(data.reply, data.weather, resTime, null, data.matching_locations);

        // Immediate Map flyTo & active pin when an explicit location is queried
        const isGreeting = /^(hi+|he+y+|hello+|namaste|pranam|greetings|good\s+(morning|afternoon|evening|day)|how\s+are\s+you|kemon\s+acho|kaise\s+ho)\b/i.test(text.trim());
        if (!isGreeting && data.weather && data.weather.latitude != null && data.weather.longitude != null) {
          const currentLat = this.activeLocation?.latitude;
          const currentLon = this.activeLocation?.longitude;
          const hasMoved = currentLat == null || currentLon == null ||
            Math.abs(data.weather.latitude - currentLat) > 0.005 ||
            Math.abs(data.weather.longitude - currentLon) > 0.005;
          const cityChanged = data.weather.city && (!this.activeLocation || data.weather.city !== this.activeLocation.city);

          if (hasMoved || cityChanged) {
            if (typeof MapController !== "undefined" && MapController.updateActiveLocation) {
              MapController.updateActiveLocation(data.weather.latitude, data.weather.longitude, data.weather.city || "Active Location", false);
            }
            await this.setActiveLocation({
              latitude: data.weather.latitude,
              longitude: data.weather.longitude,
              city: data.weather.city,
              name: data.weather.city,
              isCurrentLocation: false
            });
          }
        }

        if (typeof SupabaseService !== "undefined") {
          SupabaseService.saveChatMessage(this.sessionId, text, data.reply, this.activeLocation.city);
        }
        await this.loadRecentChats();
      } else {
        this.appendAssistantMessage("Could not retrieve meteorological intelligence. Please try again.", null, timeStr);
      }
    } catch (e) {
      if (this.currentTypingId) {
        this.removeTypingIndicator(this.currentTypingId);
        this.currentTypingId = null;
      }
      if (e.name === "AbortError" || (this.chatAbortController && this.chatAbortController.signal.aborted)) {
        return;
      }
      this.appendAssistantMessage("Network connection error. Please verify FastAPI backend is active.", null, timeStr);
    } finally {
      this.setChatGeneratingState(false);
      this.chatAbortController = null;
      this.currentTypingId = null;
      if (this.chatInput) this.chatInput.focus();
    }
  }

  appendUserMessage(text, time) {
    if (!this.messagesContainer) return;
    const row = document.createElement("div");
    row.className = "flex justify-end";
    row.innerHTML = `
      <div class="bg-blue-50 border border-blue-200/80 rounded-2xl rounded-tr-none px-4 py-2.5 max-w-md shadow-sm">
        <p class="text-slate-800 text-sm leading-relaxed">${this.escapeHTML(text)}</p>
        <div class="flex items-center justify-end gap-1 mt-1 text-[11px] text-blue-500">
          <span>${time}</span>
          <i class="fa-solid fa-check-double text-[10px]"></i>
        </div>
      </div>
    `;
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  }

  appendAssistantMessage(replyText, weather, time, messageId = null, matchingLocations = null) {
    if (!this.messagesContainer) return;
    const row = document.createElement("div");
    row.className = "flex items-start gap-3 assistant-message-row";
    if (messageId) row.dataset.messageId = messageId;
    row.dataset.rawText = replyText;

    let weatherCardHTML = "";
    if (weather) {
      const aqiNum = weather.aqi || 48;
      let aqiBg = "bg-emerald-100 text-emerald-700";
      let aqiText = `Good (${aqiNum})`;
      if (aqiNum > 50) {
        aqiBg = "bg-amber-100 text-amber-700";
        aqiText = `Moderate (${aqiNum})`;
      }
      if (aqiNum > 100) {
        aqiBg = "bg-rose-100 text-rose-700";
        aqiText = `Poor (${aqiNum})`;
      }

      weatherCardHTML = `
        <div class="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm mt-3">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-amber-500 text-2xl shadow-inner">
                <span>${weather.weather_icon || "☀️"}</span>
              </div>
              <div>
                <div class="flex items-baseline gap-1">
                  <span class="text-3xl font-bold text-slate-900">${Math.round(weather.temperature)}</span>
                  <span class="text-xl font-bold text-slate-700">°C</span>
                </div>
                <p class="text-xs font-semibold text-slate-700">${weather.weather_desc || "Sunny"} <span class="font-normal text-slate-400">• Feels like ${Math.round(weather.feels_like)}°C</span></p>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div><span class="text-slate-400">Humidity:</span> <span class="font-semibold text-slate-700 ml-1">${weather.humidity}%</span></div>
              <div><span class="text-slate-400">Wind:</span> <span class="font-semibold text-slate-700 ml-1">${Math.round(weather.wind_speed)} km/h</span></div>
              <div><span class="text-slate-400">Pressure:</span> <span class="font-semibold text-slate-700 ml-1">${Math.round(weather.pressure)} hPa</span></div>
              <div><span class="text-slate-400">Visibility:</span> <span class="font-semibold text-slate-700 ml-1">6 km</span></div>
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between text-xs pt-1">
            <div class="flex items-center gap-2">
              <span class="text-slate-500">Air Quality Index:</span>
              <span class="px-2 py-0.5 ${aqiBg} font-semibold rounded-md flex items-center gap-1 text-[11px]">
                <span class="w-1.5 h-1.5 rounded-full bg-current"></span> ${aqiText}
              </span>
            </div>
          </div>
        </div>
      `;
    }

    let matchingLocationsHTML = "";
    if (matchingLocations && Array.isArray(matchingLocations) && matchingLocations.length > 0) {
      const count = matchingLocations.length;
      const cards = matchingLocations.map((loc, idx) => {
        const primaryName = loc.name || loc.sublocality || loc.neighborhood || loc.locality || loc.city || "Location";
        const hierarchyParts = [];
        if (loc.city && loc.city !== primaryName) hierarchyParts.push(loc.city);
        if (loc.district && loc.district !== primaryName && loc.district !== loc.city) hierarchyParts.push(loc.district);
        if (loc.state && loc.state !== primaryName && loc.state !== loc.city) hierarchyParts.push(loc.state);
        if (loc.country) hierarchyParts.push(loc.country);
        const secondaryText = hierarchyParts.length > 0 ? hierarchyParts.join(", ") : (loc.formattedAddress || "");

        const latNum = parseFloat(loc.latitude != null ? loc.latitude : loc.lat) || 0;
        const lonNum = parseFloat(loc.longitude != null ? loc.longitude : loc.lon) || 0;
        const coordsText = `Lat: ${latNum.toFixed(4)}, Lon: ${lonNum.toFixed(4)}`;

        let wHTML = "";
        if (loc.weather) {
          const temp = Math.round(loc.weather.temperature);
          const feels = Math.round(loc.weather.feels_like);
          const desc = loc.weather.weather_desc || "Clear";
          const icon = loc.weather.weather_icon || "☀️";
          const hum = loc.weather.humidity != null ? `${loc.weather.humidity}%` : "--";
          const wind = loc.weather.wind_speed != null ? `${Math.round(loc.weather.wind_speed)} km/h` : "--";

          wHTML = `
            <div class="flex items-center justify-between bg-white rounded-lg px-2.5 py-1.5 border border-slate-200/70 text-[11px] mt-1 shadow-2xs">
              <div class="flex items-center gap-1.5 text-slate-800 font-bold">
                <span class="text-sm">${icon}</span>
                <span>${temp}°C</span>
                <span class="text-slate-500 font-normal text-[10px]">• ${desc}</span>
              </div>
              <div class="flex items-center gap-2 text-[10px] text-slate-500">
                <span>Feels ${feels}°C</span>
                <span>• Hum ${hum}</span>
                <span>• Wind ${wind}</span>
              </div>
            </div>
          `;
        }

        return `
          <div class="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80 hover:bg-blue-50/40 transition flex flex-col gap-1.5">
            <div class="flex items-start justify-between gap-2.5">
              <div class="min-w-0 flex-1">
                <div class="font-bold text-slate-800 text-xs truncate flex items-center gap-1.5">
                  <i class="fa-solid fa-location-dot text-blue-600 text-[11px] shrink-0"></i>
                  <span class="truncate">${this.escapeHTML(primaryName)}</span>
                </div>
                <div class="text-slate-500 text-[11px] truncate mt-0.5">${this.escapeHTML(secondaryText)}</div>
                <div class="text-slate-400 text-[10px] font-mono mt-0.5">${coordsText}</div>
              </div>
              <button class="btn-select-chat-loc px-3 py-1.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-[11px] font-semibold rounded-lg shrink-0 transition shadow-xs flex items-center gap-1" data-idx="${idx}">
                Select
              </button>
            </div>
            ${wHTML}
          </div>
        `;
      }).join("");

      matchingLocationsHTML = `
        <div class="bg-white rounded-2xl border border-slate-200 p-3.5 shadow-sm mt-3 space-y-2.5">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <div class="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wider">
              <i class="fa-solid fa-layer-group text-blue-600"></i>
              MATCHING LOCATIONS (${count})
            </div>
          </div>
          <p class="text-[11px] text-slate-500">Showing all matching locations returned by the location service. Click <strong class="text-slate-700">Select</strong> to set as active location.</p>
          <div class="space-y-2 max-h-80 overflow-y-auto pr-1">
            ${cards}
          </div>
        </div>
      `;
    }

    const formattedHTML = formatMarkdown(replyText);

    row.innerHTML = `
      <div class="w-5 h-5 rounded-md bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
        <i class="fa-solid fa-cloud-sun text-[10px]"></i>
      </div>
      <div class="space-y-2 max-w-xl">
        <div class="text-xs text-slate-500 font-medium">WeatherGPT</div>
        <div class="text-slate-700 text-sm leading-relaxed assistant-text-content">${formattedHTML}</div>
        ${weatherCardHTML}
        ${matchingLocationsHTML}
        <span class="text-[11px] text-slate-400 block pt-0.5">${time}</span>
      </div>
    `;

    if (matchingLocations && Array.isArray(matchingLocations) && matchingLocations.length > 0) {
      const selectBtns = row.querySelectorAll(".btn-select-chat-loc");
      selectBtns.forEach(btn => {
        const idx = parseInt(btn.dataset.idx, 10);
        const loc = matchingLocations[idx];
        if (loc) {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            this.setActiveLocation({
              ...loc,
              isCurrentLocation: false
            });
            btn.innerHTML = `<i class="fa-solid fa-check text-xs mr-1"></i> Selected`;
            btn.classList.remove("bg-blue-600", "hover:bg-blue-700");
            btn.classList.add("bg-emerald-600", "hover:bg-emerald-700");
          });
        }
      });
    }

    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  }

  showTypingIndicator() {
    const id = "typing_" + Date.now();
    const row = document.createElement("div");
    row.id = id;
    row.className = "flex items-start gap-3";
    row.innerHTML = `
      <div class="w-5 h-5 rounded-md bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
        <i class="fa-solid fa-cloud-sun text-[10px]"></i>
      </div>
      <div class="bg-white border border-slate-200/90 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-1.5 mt-0.5">
        <span class="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 0ms"></span>
        <span class="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 150ms"></span>
        <span class="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 300ms"></span>
      </div>
    `;
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
    return id;
  }

  removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  renderSavedLocationsModal(autoOpen = false) {
    const list = document.getElementById("saved-locations-list");
    const modal = document.getElementById("modal-saved");
    if (!list) return;

    const cities = [
      { name: "New Delhi", state: "Delhi", lat: 28.6139, lon: 77.2090 },
      { name: "Mumbai", state: "Maharashtra", lat: 19.0760, lon: 72.8777 },
      { name: "Bengaluru", state: "Karnataka", lat: 12.9716, lon: 77.5946 },
      { name: "Kolkata", state: "West Bengal", lat: 22.5726, lon: 88.3639 },
      { name: "Chennai", state: "Tamil Nadu", lat: 13.0827, lon: 80.2707 },
      { name: "Jaipur", state: "Rajasthan", lat: 26.9124, lon: 75.7873 },
      { name: "Ahmedabad", state: "Gujarat", lat: 23.0225, lon: 72.5714 }
    ];

    list.innerHTML = "";
    cities.forEach(c => {
      const row = document.createElement("div");
      row.className = "p-2.5 bg-slate-50 hover:bg-blue-50/50 border border-slate-200 rounded-xl flex items-center justify-between cursor-pointer transition";
      row.innerHTML = `
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-xs">
            <i class="fa-solid fa-location-dot"></i>
          </div>
          <div>
            <p class="font-bold text-slate-800 text-xs">${c.name}</p>
            <p class="text-[10px] text-slate-400">${c.state}, India</p>
          </div>
        </div>
        <i class="fa-solid fa-arrow-right text-[10px] text-slate-400"></i>
      `;
      row.addEventListener("click", () => {
        this.updateLocation(c.name, c.lat, c.lon);
        this.closeAllModals();
      });
      list.appendChild(row);
    });

    if (autoOpen && modal) {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    }
  }

  async loadApiSettings() {
    try {
      const res = await apiFetch("/api/settings");
      if (res && res.ok) {
        const data = await res.json();
        const modelSelect = document.getElementById("setting-openai-model");
        const statusLabel = document.getElementById("api-key-status");
        if (modelSelect && data.openai_model) modelSelect.value = data.openai_model;
        if (statusLabel) {
          statusLabel.textContent = data.openai_configured ? "OpenAI Connected (Active)" : "Using Built-in Meteorological Engine";
          statusLabel.className = data.openai_configured ? "text-[11px] text-emerald-600 font-semibold" : "text-[11px] text-blue-600 font-semibold";
        }
      }
    } catch (e) {
      console.warn("Failed to load settings:", e);
    }
  }

  async saveApiSettings() {
    const openaiKey = document.getElementById("setting-openai-key")?.value.trim();
    const openaiModel = document.getElementById("setting-openai-model")?.value;
    const weatherKey = document.getElementById("setting-weather-key")?.value.trim();
    const statusLabel = document.getElementById("api-key-status");
    if (statusLabel) {
      statusLabel.textContent = "Saving...";
      statusLabel.className = "text-[11px] text-blue-600 font-semibold";
    }

    try {
      const payload = { openai_model: openaiModel };
      if (openaiKey) payload.openai_api_key = openaiKey;
      if (weatherKey) payload.weather_api_key = weatherKey;

      const res = await apiFetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res && res.ok) {
        const data = await res.json();
        if (statusLabel) {
          statusLabel.textContent = data.openai_configured ? `OpenAI Key Saved (${data.openai_model})` : "Settings saved!";
          statusLabel.className = "text-[11px] text-emerald-600 font-semibold";
        }
        const keyInput = document.getElementById("setting-openai-key");
        if (keyInput && openaiKey) keyInput.value = "";
      }
    } catch (e) {
      if (statusLabel) {
        statusLabel.textContent = "Error saving settings";
        statusLabel.className = "text-[11px] text-rose-600 font-semibold";
      }
    }
  }

  initSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.speechRecognition = new SpeechRecognition();
      this.speechRecognition.continuous = false;
      this.speechRecognition.interimResults = false;

      this.speechRecognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (this.chatInput) {
          this.chatInput.value = transcript;
          this.stopVoice();
          this.handleSendMessage();
        }
      };
      this.speechRecognition.onerror = () => this.stopVoice();
      this.speechRecognition.onend = () => this.stopVoice();
    }
  }

  toggleVoice() {
    if (!this.speechRecognition) return;
    if (this.isListening) {
      this.stopVoice();
    } else {
      this.startVoice();
    }
  }

  startVoice() {
    if (!this.speechRecognition) return;
    try {
      this.speechRecognition.start();
      this.isListening = true;
      if (this.btnMic) {
        this.btnMic.classList.add("text-rose-600", "animate-pulse");
      }
    } catch (e) {}
  }

  stopVoice() {
    if (!this.speechRecognition) return;
    try {
      this.speechRecognition.stop();
    } catch (e) {}
    this.isListening = false;
    if (this.btnMic) {
      this.btnMic.classList.remove("text-rose-600", "animate-pulse");
    }
  }

  scrollToBottom() {
    if (this.chatScroll) {
      setTimeout(() => {
        this.chatScroll.scrollTop = this.chatScroll.scrollHeight;
      }, 60);
    }
  }

  formatDate(dateStr) {
    if (!dateStr) return "Recent";
    const d = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diffDays === 1) return "Yesterday";
    return `${diffDays} days ago`;
  }

  formatTime(dateStr) {
    if (!dateStr) return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  escapeHTML(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.app = new WeatherGPTApp();
  window.WeatherApp = window.app;
});
