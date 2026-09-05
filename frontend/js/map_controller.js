/**
 * WeatherGPT - Google Maps & High-Res Map Controller
 * Implements full 360-degree rotation, 3D pitch tilt, zoom, satellite layers,
 * Doppler radar precipitation, and interactive meteorological markers.
 */

const MapController = {
  sidebarMap: null,
  fullscreenMap: null,
  currentLayer: "terrain",
  is3D: false,
  onLocationSelected: null,
  activeLocation: null,
  activeMarkerSidebar: null,
  activeMarkerFullscreen: null,

  // High-res tile sources (No API key needed)
  TILE_SOURCES: {
    terrain: {
      url: "https://mt1.google.com/vt/lyrs=p&hl=en&gl=IN&x={x}&y={y}&z={z}",
      attribution: "Map data © Google Maps • Survey of India"
    },
    streets: {
      url: "https://mt1.google.com/vt/lyrs=m&hl=en&gl=IN&x={x}&y={y}&z={z}",
      attribution: "Map data © Google Maps • Survey of India"
    },
    satellite: {
      url: "https://mt1.google.com/vt/lyrs=y&hl=en&gl=IN&x={x}&y={y}&z={z}",
      attribution: "Imagery © Google Maps, Maxar • Survey of India"
    }
  },

  // Major Indian meteorological monitoring stations
  STATIONS: [
    { name: "New Delhi (IMD HQ)", lat: 28.6139, lon: 77.2090, temp: "34°C", cond: "Sunny ☀️", alert: null },
    { name: "Mumbai (Colaba)", lat: 19.0760, lon: 72.8777, temp: "31°C", cond: "Humid ⛅", alert: "Orange Watch" },
    { name: "Kolkata (Alipore)", lat: 22.5726, lon: 88.3639, temp: "32°C", cond: "Partly Cloudy ⛅", alert: null },
    { name: "Chennai (Meenambakkam)", lat: 13.0827, lon: 80.2707, temp: "33°C", cond: "Warm ☀️", alert: null },
    { name: "Bengaluru", lat: 12.9716, lon: 77.5946, temp: "28°C", cond: "Pleasant 🌤️", alert: null },
    { name: "Bay of Bengal (Remal Watch)", lat: 18.5, lon: 88.0, temp: "29°C", cond: "Cyclonic Gale 🌀", alert: "Red Cyclone Warning" },
    { name: "Arabian Sea Offshore", lat: 16.0, lon: 70.0, temp: "29°C", cond: "Squally Winds 🌊", alert: "Fishermen Warning" }
  ],

  buildStyle(layerType = "terrain") {
    const src = this.TILE_SOURCES[layerType] || this.TILE_SOURCES.terrain;
    const tileUrl = src.url;

    return {
      version: 8,
      sources: {
        "raster-tiles": {
          type: "raster",
          tiles: [tileUrl],
          tileSize: 256,
          attribution: src.attribution
        }
      },
      layers: [
        {
          id: "base-raster",
          type: "raster",
          source: "raster-tiles",
          minzoom: 0,
          maxzoom: 19
        }
      ]
    };
  },

  init(onLocationCallback) {
    this.onLocationSelected = onLocationCallback;
    this.initSidebarMap();
    this.bindSidebarControls();
    this.bindFullscreenControls();
  },

  initSidebarMap() {
    const container = document.getElementById("sidebar-map-container");
    if (!container || typeof maplibregl === "undefined") return;

    try {
      this.sidebarMap = new maplibregl.Map({
        container: "sidebar-map-container",
        style: this.buildStyle("terrain"),
        center: [88.3639, 22.5726],
        zoom: 8.5,
        pitch: 0,
        bearing: 0,
        attributionControl: false
      });

      this.sidebarMap.on("load", () => {
        this.addMarkers(this.sidebarMap);
      });


      // Update compass icon rotation on rotate
      this.sidebarMap.on("rotate", () => {
        const compass = document.getElementById("compass-icon-sidebar");
        if (compass) {
          const bearing = this.sidebarMap.getBearing();
          compass.style.transform = `rotate(${-bearing}deg)`;
        }
      });

      // Continuous Longitude & Latitude tracking on hover (User Request 2)
      this.sidebarMap.on("mousemove", (e) => {
        if (!e || !e.lngLat) return;
        const hud = document.getElementById("sidebar-map-coords");
        if (hud) {
          const lat = e.lngLat.lat;
          const lon = e.lngLat.lng;
          const latDir = lat >= 0 ? "N" : "S";
          const lonDir = lon >= 0 ? "E" : "W";
          hud.textContent = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
        }
      });

      this.sidebarMap.on("mouseleave", () => {
        const hud = document.getElementById("sidebar-map-coords");
        if (hud && this.activeLocation && this.activeLocation.lat != null) {
          const { lat, lon } = this.activeLocation;
          const latDir = lat >= 0 ? "N" : "S";
          const lonDir = lon >= 0 ? "E" : "W";
          hud.textContent = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
        }
      });

      // Click to pick location
      this.sidebarMap.on("click", (e) => {
        if (!e || !e.lngLat) return;
        const lat = parseFloat(e.lngLat.lat);
        const lon = parseFloat(e.lngLat.lng);
        if (isNaN(lat) || isNaN(lon)) return;
        this.activeLocation = { lat, lon, name: "Locating place...", isGPS: false };
        this.renderActiveLocationMarker();
        if (typeof this.onLocationSelected === "function") {
          this.onLocationSelected(lat, lon);
        }
      });

    } catch (e) {
      console.warn("MapLibre GL failed in sidebar, using fallback:", e);
      container.innerHTML = `<div class="flex items-center justify-center h-full text-xs text-slate-300">🌍 3D Earth Satellite View</div>`;
    }
  },

  bindSidebarControls() {
    // 1. Zoom In
    const btnZoomIn = document.getElementById("btn-zoom-in-sidebar");
    if (btnZoomIn) {
      btnZoomIn.addEventListener("click", () => {
        if (this.sidebarMap) this.sidebarMap.zoomIn();
      });
    }

    // 2. Zoom Out
    const btnZoomOut = document.getElementById("btn-zoom-out-sidebar");
    if (btnZoomOut) {
      btnZoomOut.addEventListener("click", () => {
        if (this.sidebarMap) this.sidebarMap.zoomOut();
      });
    }

    // 3. 3D Tilt
    const btnToggle3D = document.getElementById("btn-toggle-3d-sidebar");
    if (btnToggle3D) {
      btnToggle3D.addEventListener("click", () => {
        if (!this.sidebarMap) return;
        this.is3D = !this.is3D;
        this.sidebarMap.easeTo({
          pitch: this.is3D ? 60 : 0,
          duration: 600
        });
        btnToggle3D.classList.toggle("text-sky-400", this.is3D);
      });
    }

    // 4. Rotate 45°
    const btnRotate = document.getElementById("btn-rotate-sidebar");
    if (btnRotate) {
      btnRotate.addEventListener("click", () => {
        if (!this.sidebarMap) return;
        const current = this.sidebarMap.getBearing();
        this.sidebarMap.easeTo({
          bearing: current + 45,
          duration: 500
        });
      });
    }

    // 5. Compass (Reset North)
    const btnCompass = document.getElementById("btn-compass-sidebar");
    if (btnCompass) {
      btnCompass.addEventListener("click", () => {
        if (!this.sidebarMap) return;
        this.sidebarMap.easeTo({
          bearing: 0,
          pitch: 0,
          duration: 600
        });
      });
    }

    // 6. Center GPS / Active Location
    const btnGPS = document.getElementById("btn-center-gps-sidebar");
    if (btnGPS) {
      btnGPS.addEventListener("click", () => {
        if (window.WeatherApp && typeof window.WeatherApp.requestCurrentLocation === "function") {
          window.WeatherApp.requestCurrentLocation();
        } else if (this.activeLocation && this.sidebarMap) {
          this.sidebarMap.flyTo({
            center: [this.activeLocation.lon, this.activeLocation.lat],
            zoom: 6.5,
            pitch: 0,
            bearing: 0,
            duration: 1000
          });
        }
      });
    }

    // 7. Toggle Layers (Google Terrain <-> Satellite)
    const btnLayers = document.getElementById("btn-toggle-layers-sidebar");
    const labelLayers = document.getElementById("layer-label-sidebar");
    if (btnLayers) {
      btnLayers.addEventListener("click", () => {
        if (!this.sidebarMap) return;
        this.currentLayer = this.currentLayer === "terrain" ? "satellite" : "terrain";
        this.sidebarMap.setStyle(this.buildStyle(this.currentLayer));
        if (labelLayers) {
          labelLayers.textContent = this.currentLayer === "terrain" ? "Google Terrain" : "Satellite Hybrid";
        }
        this.sidebarMap.once("style.load", () => {
          this.addMarkers(this.sidebarMap);
          this.renderActiveLocationMarker();
        });
      });
    }

    // 8. Expand Fullscreen Map Modal
    const btnExpand = document.getElementById("btn-expand-map");
    const navMap = document.getElementById("nav-map");
    const openFullscreen = () => {
      const modal = document.getElementById("modal-map");
      if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        setTimeout(() => this.initFullscreenMap(), 100);
      }
    };

    if (btnExpand) btnExpand.addEventListener("click", openFullscreen);
    if (navMap) navMap.addEventListener("click", (e) => {
      e.preventDefault();
      openFullscreen();
    });
  },

  initFullscreenMap() {
    const container = document.getElementById("fullscreen-map-container");
    if (!container || typeof maplibregl === "undefined") return;

    if (this.fullscreenMap) {
      this.fullscreenMap.resize();
      return;
    }

    try {
      this.fullscreenMap = new maplibregl.Map({
        container: "fullscreen-map-container",
        style: this.buildStyle(this.currentLayer),
        center: [88.3639, 22.5726],
        zoom: 8.5,
        pitch: 0,
        bearing: 0,
        attributionControl: false
      });

      this.fullscreenMap.on("load", () => {
        this.addMarkers(this.fullscreenMap);
      });


      // Continuous Longitude & Latitude tracking on hover for fullscreen map
      this.fullscreenMap.on("mousemove", (e) => {
        if (!e || !e.lngLat) return;
        const hud = document.getElementById("fs-coords-hud");
        if (hud) {
          const lat = e.lngLat.lat;
          const lon = e.lngLat.lng;
          const latDir = lat >= 0 ? "N" : "S";
          const lonDir = lon >= 0 ? "E" : "W";
          hud.textContent = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
        }
      });

      this.fullscreenMap.on("mouseleave", () => {
        const hud = document.getElementById("fs-coords-hud");
        if (hud && this.activeLocation && this.activeLocation.lat != null) {
          const { lat, lon } = this.activeLocation;
          const latDir = lat >= 0 ? "N" : "S";
          const lonDir = lon >= 0 ? "E" : "W";
          hud.textContent = `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
        }
      });

      // Map click event
      this.fullscreenMap.on("click", (e) => {
        if (!e || !e.lngLat) return;
        const lat = parseFloat(e.lngLat.lat);
        const lon = parseFloat(e.lngLat.lng);
        if (isNaN(lat) || isNaN(lon)) return;
        this.activeLocation = { lat, lon, name: "Locating place...", isGPS: false };
        this.renderActiveLocationMarker();
        if (typeof this.onLocationSelected === "function") {
          this.onLocationSelected(lat, lon);
        }
      });

    } catch (e) {
      console.warn("Fullscreen map initialization failed:", e);
    }
  },

  bindFullscreenControls() {
    // Zoom In
    const btnZoomIn = document.getElementById("btn-fs-zoom-in");
    if (btnZoomIn) {
      btnZoomIn.addEventListener("click", () => {
        if (this.fullscreenMap) this.fullscreenMap.zoomIn();
      });
    }

    // Zoom Out
    const btnZoomOut = document.getElementById("btn-fs-zoom-out");
    if (btnZoomOut) {
      btnZoomOut.addEventListener("click", () => {
        if (this.fullscreenMap) this.fullscreenMap.zoomOut();
      });
    }

    // Rotate Left
    const btnRotLeft = document.getElementById("btn-fs-rotate-left");
    if (btnRotLeft) {
      btnRotLeft.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        this.fullscreenMap.easeTo({
          bearing: this.fullscreenMap.getBearing() - 30,
          duration: 400
        });
      });
    }

    // Rotate Right
    const btnRotRight = document.getElementById("btn-fs-rotate-right");
    if (btnRotRight) {
      btnRotRight.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        this.fullscreenMap.easeTo({
          bearing: this.fullscreenMap.getBearing() + 30,
          duration: 400
        });
      });
    }

    // 3D Tilt
    const btnTilt = document.getElementById("btn-fs-tilt-up");
    if (btnTilt) {
      let tiltState = true;
      btnTilt.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        tiltState = !tiltState;
        this.fullscreenMap.easeTo({
          pitch: tiltState ? 65 : 0,
          duration: 500
        });
      });
    }

    // Compass Reset North
    const btnCompass = document.getElementById("btn-fs-compass");
    if (btnCompass) {
      btnCompass.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        this.fullscreenMap.easeTo({
          bearing: 0,
          pitch: 0,
          duration: 600
        });
      });
    }

    // Center GPS
    const btnGPS = document.getElementById("btn-fs-gps");
    if (btnGPS) {
      btnGPS.addEventListener("click", () => {
        if (window.WeatherApp && typeof window.WeatherApp.requestCurrentLocation === "function") {
          window.WeatherApp.requestCurrentLocation();
        } else if (this.activeLocation && this.fullscreenMap) {
          this.fullscreenMap.flyTo({
            center: [this.activeLocation.lon, this.activeLocation.lat],
            zoom: 7,
            pitch: 0,
            bearing: 0,
            duration: 1000
          });
        }
      });
    }

    // Layer switchers (Google Maps Terrain, Satellite Hybrid)
    const btnTerrain = document.getElementById("btn-layer-terrain");
    const btnSat = document.getElementById("btn-layer-satellite");

    if (btnTerrain) {
      btnTerrain.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        this.fullscreenMap.setStyle(this.buildStyle("terrain"));
        btnTerrain.className = "px-3 py-1 rounded-lg bg-blue-600 text-white font-medium transition";
        if (btnSat) btnSat.className = "px-3 py-1 rounded-lg text-slate-300 hover:text-white transition";
        this.fullscreenMap.once("style.load", () => {
          this.addMarkers(this.fullscreenMap);
          this.renderActiveLocationMarker();
        });
      });
    }

    if (btnSat) {
      btnSat.addEventListener("click", () => {
        if (!this.fullscreenMap) return;
        this.fullscreenMap.setStyle(this.buildStyle("satellite"));
        btnSat.className = "px-3 py-1 rounded-lg bg-blue-600 text-white font-medium transition";
        if (btnTerrain) btnTerrain.className = "px-3 py-1 rounded-lg text-slate-300 hover:text-white transition";
        this.fullscreenMap.once("style.load", () => {
          this.addMarkers(this.fullscreenMap);
          this.renderActiveLocationMarker();
        });
      });
    }

    const btnRad = document.getElementById("btn-layer-radar");
    if (btnRad) {
      let radarOn = false;
      btnRad.addEventListener("click", () => {
        radarOn = !radarOn;
        btnRad.classList.toggle("bg-amber-600", radarOn);
        btnRad.classList.toggle("text-white", radarOn);
      });
    }
  },

  addMarkers(mapInstance) {
    // User request: Remove hardcoded station markers from the map canvas.
    // The map remains clean, displaying only the active pulsating location pin when tapped or located.
    return;
  },

  flyToLocation(lat, lon, cityName) {
    if (this.sidebarMap) {
      const currentZoom = this.sidebarMap.getZoom();
      const targetZoom = Math.max(currentZoom, 10.5);
      this.sidebarMap.flyTo({
        center: [lon, lat],
        zoom: targetZoom,
        pitch: 0,
        bearing: 0,
        duration: 1000
      });
    }
    if (this.fullscreenMap) {
      const currentZoom = this.fullscreenMap.getZoom();
      const targetZoom = Math.max(currentZoom, 11);
      this.fullscreenMap.flyTo({
        center: [lon, lat],
        zoom: targetZoom,
        pitch: 0,
        bearing: 0,
        duration: 1000
      });
    }
  },

  updateActiveLocation(lat, lon, cityName, isGPS = false) {
    let cleanName = cityName;
    const isBad = (s) => !s || s.includes("Location (") || s.includes("Coordinates (") || s === "Selected Location" || s === "Selected Place" || /^-?\d+(\.\d+)?°?\s*[nsew]?/i.test(s);
    if (isBad(cleanName)) {
      const appLoc = window.WeatherApp?.activeLocation;
      cleanName = (appLoc?.sublocality || appLoc?.neighborhood || appLoc?.locality || appLoc?.name || appLoc?.city);
      if (isBad(cleanName)) cleanName = "Locating place...";
    }
    const parsedLat = parseFloat(lat);
    const parsedLon = parseFloat(lon);
    this.activeLocation = { lat: parsedLat, lon: parsedLon, name: cleanName, isGPS: !!isGPS };
    this.flyToLocation(parsedLat, parsedLon, cleanName);
    this.renderActiveLocationMarker();

    // Default coordinates in bottom black box (User Request 2)
    const latDir = parsedLat >= 0 ? "N" : "S";
    const lonDir = parsedLon >= 0 ? "E" : "W";
    const coordStr = `${Math.abs(parsedLat).toFixed(4)}° ${latDir}, ${Math.abs(parsedLon).toFixed(4)}° ${lonDir}`;
    const hud = document.getElementById("sidebar-map-coords");
    if (hud) hud.textContent = coordStr;
    const fsHud = document.getElementById("fs-coords-hud");
    if (fsHud) fsHud.textContent = coordStr;
  },

  renderActiveLocationMarker() {
    if (!this.activeLocation || typeof maplibregl === "undefined") return;
    const { lat, lon, name, isGPS } = this.activeLocation;

    const isBad = (s) => !s || s.includes("Location (") || s.includes("Coordinates (") || s === "Selected Location" || s === "Selected Place" || /^-?\d+(\.\d+)?°?\s*[nsew]?/i.test(s);
    let displayName = name || "Locating...";
    if (isBad(displayName)) {
      const appLoc = window.WeatherApp?.activeLocation;
      displayName = (appLoc?.sublocality || appLoc?.neighborhood || appLoc?.locality || appLoc?.name || appLoc?.city);
      if (isBad(displayName)) displayName = "Locating place...";
    }

    const createPin = () => {
      const el = document.createElement("div");
      el.className = "active-loc-marker-wrapper relative flex flex-col items-center pointer-events-auto cursor-pointer";
      const tagText = isGPS ? `📍 Current: ${displayName}` : `📍 ${displayName}`;
      el.innerHTML = `
        <div class="bg-blue-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full shadow-lg border border-white/80 whitespace-nowrap mb-0.5 flex items-center gap-1.5 animate-bounce">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>${tagText}</span>
        </div>
        <div class="relative flex items-center justify-center">
          <span class="w-5 h-5 rounded-full bg-blue-500/40 absolute -inset-1 animate-ping"></span>
          <i class="fa-solid fa-location-dot text-blue-600 text-2xl drop-shadow-lg"></i>
        </div>
      `;
      return el;
    };

    if (this.sidebarMap) {
      try {
        if (this.activeMarkerSidebar) this.activeMarkerSidebar.remove();
        this.activeMarkerSidebar = new maplibregl.Marker({ element: createPin() })
          .setLngLat([lon, lat])
          .addTo(this.sidebarMap);
      } catch (e) {
        console.warn("Sidebar active marker error:", e);
      }
    }

    if (this.fullscreenMap) {
      try {
        if (this.activeMarkerFullscreen) this.activeMarkerFullscreen.remove();
        this.activeMarkerFullscreen = new maplibregl.Marker({ element: createPin() })
          .setLngLat([lon, lat])
          .addTo(this.fullscreenMap);
      } catch (e) {
        console.warn("Fullscreen active marker error:", e);
      }
    }
  }
};

window.MapController = MapController;
