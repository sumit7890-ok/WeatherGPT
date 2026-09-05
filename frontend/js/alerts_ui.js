/**
 * WeatherGPT - Alerts UI Module
 * Evaluates and renders real-time IMD color-coded hazard alerts (Green, Yellow, Orange, Red)
 * according to actual meteorological conditions.
 */

const AlertsUI = {
  activeAlerts: [],

  renderActiveAlert(alerts) {
    this.activeAlerts = alerts || [];
    const stack = document.getElementById("sidebar-alerts-stack");
    const countBadge = document.getElementById("alerts-count-badge");
    const navDot = document.getElementById("nav-alert-dot");
    if (!stack) return;

    stack.innerHTML = "";

    const nonGreen = this.activeAlerts.filter(a => a.severity !== "GREEN");

    const lang = (window.app && window.app.currentLanguage) ? window.app.currentLanguage : "en";
    const t = {
      en: {
        badge: "Normal",
        active: "Active",
        title: "Normal Synoptic Status",
        desc: "No severe warnings in effect. Safe for outdoor routines.",
        source: "Updated live via IMD synoptic radar"
      },
      hi: {
        badge: "सामान्य",
        active: "सक्रिय",
        title: "सामान्य सिनॉप्टिक स्थिति",
        desc: "कोई गंभीर चेतावनी सक्रिय नहीं। सामान्य गतिविधियों के लिए सुरक्षित।",
        source: "आईएमडी सिनॉप्टिक रडार द्वारा लाइव अद्यतन"
      },
      bn: {
        badge: "স্বাভাবিক",
        active: "সক্রিয়",
        title: "স্বাভাবিক সিনপটিক অবস্থা",
        desc: "কোনো তীব্র সতর্কতা নেই। স্বাভাবিক কাজকর্মের জন্য অনুকূল।",
        source: "আইএমডি সিনপটিক রাডার দ্বারা লাইভ আপডেট"
      }
    }[lang] || {
      badge: "Normal",
      active: "Active",
      title: "Normal Synoptic Status",
      desc: "No severe warnings in effect. Safe for outdoor routines.",
      source: "Updated live via IMD synoptic radar"
    };

    // Update count badge
    if (countBadge) {
      if (nonGreen.length > 0) {
        countBadge.textContent = `${nonGreen.length} ${t.active}`;
        countBadge.className = "text-[10px] bg-rose-100 text-rose-700 font-bold px-1.5 py-0.5 rounded";
        if (navDot) navDot.className = "w-2 h-2 rounded-full bg-rose-500 animate-pulse";
      } else {
        countBadge.textContent = t.badge;
        countBadge.className = "text-[10px] bg-emerald-100 text-emerald-700 font-bold px-1.5 py-0.5 rounded";
        if (navDot) navDot.className = "w-2 h-2 rounded-full bg-emerald-500";
      }
    }

    // If no severe warning, show normal condition card
    if (nonGreen.length === 0) {
      stack.innerHTML = `
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs">
          <div class="flex items-start gap-2.5">
            <div class="w-6 h-6 rounded-lg bg-emerald-500 text-white flex items-center justify-center shrink-0 text-xs">
              <i class="fa-solid fa-check"></i>
            </div>
            <div>
              <h4 class="font-bold text-emerald-950 text-xs">${t.title}</h4>
              <p class="text-[11px] text-emerald-800 mt-0.5 leading-snug">${t.desc}</p>
              <p class="text-[10px] text-slate-400 mt-1 font-medium">${t.source}</p>
            </div>
          </div>
        </div>
      `;
      return;
    }

    // Display non-green alerts (max 2 in sidebar)
    nonGreen.slice(0, 2).forEach(a => {
      const isRed = a.severity === "RED" || a.severity === "ORANGE";
      const bgClass = isRed ? "bg-rose-50 border-rose-200" : "bg-amber-50 border-amber-200";
      const iconBg = isRed ? "bg-rose-500" : "bg-amber-500";
      const titleColor = isRed ? "text-rose-950" : "text-amber-950";
      const subColor = isRed ? "text-rose-800" : "text-amber-800";
      
      let icon = "fa-triangle-exclamation";
      if (a.hazard_type.toLowerCase().includes("cyclone") || a.hazard_type.toLowerCase().includes("wind")) {
        icon = "fa-tornado";
      } else if (a.hazard_type.toLowerCase().includes("rain") || a.hazard_type.toLowerCase().includes("flood")) {
        icon = "fa-cloud-showers-heavy";
      } else if (a.hazard_type.toLowerCase().includes("thunder") || a.hazard_type.toLowerCase().includes("lightning")) {
        icon = "fa-bolt";
      } else if (a.hazard_type.toLowerCase().includes("heat")) {
        icon = "fa-sun";
      }

      const card = document.createElement("div");
      card.className = `${bgClass} border rounded-xl p-3 text-xs shadow-sm transition hover:shadow`;
      card.innerHTML = `
        <div class="flex items-start gap-2.5">
          <div class="w-6 h-6 rounded-lg ${iconBg} text-white flex items-center justify-center shrink-0 text-xs shadow-sm">
            <i class="fa-solid ${icon}"></i>
          </div>
          <div>
            <h4 class="font-bold ${titleColor} text-xs leading-snug">${a.headline}</h4>
            <p class="text-[11px] ${subColor} mt-0.5 leading-snug font-medium">${a.region}</p>
            <p class="text-[10px] text-slate-400 mt-1 font-medium">${a.valid_until ? 'Valid till ' + a.valid_until.split('T')[0] : 'IMD Live Bulletin'}</p>
          </div>
        </div>
      `;
      stack.appendChild(card);
    });
  },

  renderNationalModal(allAlerts) {
    const modalContent = document.getElementById("modal-alerts-content");
    if (!modalContent || !allAlerts) return;

    modalContent.innerHTML = "";
    allAlerts.forEach(a => {
      const isRed = a.severity === "RED" || a.severity === "ORANGE";
      const border = isRed ? "border-rose-200 bg-rose-50/70" : "border-amber-200 bg-amber-50/70";
      const badge = isRed ? "bg-rose-600 text-white" : "bg-amber-600 text-white";

      const item = document.createElement("div");
      item.className = `p-4 rounded-2xl border ${border} text-xs space-y-2`;
      item.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="px-2 py-0.5 rounded-full font-bold text-[10px] uppercase tracking-wider ${badge}">
            ${a.severity} • ${a.hazard_type}
          </span>
          <span class="text-[11px] text-slate-500 font-medium">${a.region}</span>
        </div>
        <h4 class="font-bold text-slate-900 text-sm">${a.headline}</h4>
        <p class="text-slate-700 leading-relaxed">${a.description}</p>
        <div class="pt-2 border-t border-black/5 text-slate-600">
          <strong class="text-slate-800">Advisory:</strong> ${a.advisory}
        </div>
      `;
      modalContent.appendChild(item);
    });
  }
};

window.AlertsUI = AlertsUI;
