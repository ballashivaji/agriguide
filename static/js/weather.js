// AgriGuide - live weather (full page + dashboard mini card)
(function () {
  const DEFAULT = { lat: 17.385, lon: 78.4867, name: "Hyderabad, Telangana, India", mode: "default" };
  const LS_LOC = "agri_loc", LS_SAVED = "agri_saved";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked */ } };

  async function api(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" } });
    if (r.status === 401) { location.href = "/login"; throw new Error("Please login again."); }
    let data = {};
    try { data = await r.json(); } catch (e) { /* non-JSON error page */ }
    if (!r.ok) throw new Error(data.error || "Weather service error (" + r.status + ").");
    return data;
  }
  const fetchWeather = (loc) =>
    api("/api/weather?lat=" + loc.lat + "&lon=" + loc.lon + (loc.name && loc.mode !== "gps" ? "&name=" + encodeURIComponent(loc.name) : ""));

  function getGps() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) return reject(new Error("This browser has no location support."));
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ lat: +p.coords.latitude.toFixed(4), lon: +p.coords.longitude.toFixed(4), mode: "gps" }),
        (e) => reject(new Error(e.code === 1 ? "Location permission was denied." : "Could not detect your location.")),
        { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 });
    });
  }

  // ----------------------------------------------------------- dashboard mini card
  const mini = $("miniWeather");
  if (mini && !$("wxBody")) {
    const loc = read(LS_LOC, DEFAULT);
    fetchWeather(loc).then((w) => {
      const c = w.current, top = w.advisories.filter((a) => a.level === "alert" || a.level === "warn").slice(0, 2);
      mini.innerHTML =
        '<div class="mini-row"><span class="wx-big-icon">' + c.icon + '</span><div><div class="mini-temp">' + c.temp + '°C</div>' +
        '<div class="sub small">' + esc(c.label) + " · " + esc(w.location.name) + "</div></div></div>" +
        (top.length ? top.map((a) => '<div class="mini-adv adv-' + a.level + '">' + a.icon + " <strong>" + esc(a.title) + "</strong></div>").join("")
                    : '<div class="mini-adv adv-good">✅ No weather warnings</div>') +
        '<a href="/weather" class="btn btn-primary btn-sm" style="margin-top:10px;">Full forecast</a>';
    }).catch((e) => { mini.innerHTML = '<p class="sub">' + esc(e.message) + '</p><a href="/weather" class="btn btn-sm btn-primary">Open weather</a>'; });
    return;
  }
  if (!$("wxBody")) return;

  // --------------------------------------------------------------------- full page
  let current = null, timer = null, pendingNote = null;
  const setStatus = (msg, isErr) => { const s = $("wxStatus"); s.hidden = !msg; s.textContent = msg || ""; s.classList.toggle("wx-error", !!isErr); };

  async function load(loc) {
    current = loc;
    setStatus("Loading weather…");
    try {
      const w = await fetchWeather(loc);
      render(w);
      setStatus(pendingNote || ""); pendingNote = null;
      $("wxBody").hidden = false;
      clearInterval(timer);
      timer = setInterval(() => load(current), 10 * 60 * 1000);
    } catch (e) { setStatus("⚠️ " + e.message + " Use Refresh to try again.", true); }
  }

  function tile(label, value, unit) {
    return '<div class="wx-tile"><span>' + label + '</span><strong>' + (value == null ? "–" : esc(value) + (unit || "")) + "</strong></div>";
  }

  function render(w) {
    const c = w.current, d0 = w.daily[0];
    if (current.mode === "gps") { current.name = w.location.name; }
    $("wxPlace").textContent = "📍 " + w.location.name;
    $("wxIcon").textContent = c.icon;
    $("wxTemp").textContent = c.temp + "°C";
    $("wxLabel").textContent = c.label + " · feels like " + c.feels_like + "°C";
    $("wxUpdated").textContent = "Updated " + c.time.replace("T", " ") + " (local time)";
    $("wxTiles").innerHTML =
      tile("Humidity", c.humidity, "%") + tile("Wind", c.wind + " " + c.wind_dir, " km/h") + tile("Gusts", c.gust, " km/h") +
      tile("Rain now", c.rain_now, " mm") + tile("Rain chance today", d0.rain_prob, "%") + tile("Pressure", c.pressure, " hPa") +
      tile("Cloud cover", c.cloud, "%") + tile("UV index (max)", c.uv) + tile("Soil moisture", c.soil_moisture, "%") +
      tile("Soil temp", c.soil_temp, "°C") + tile("Sunrise", d0.sunrise) + tile("Sunset", d0.sunset);

    $("wxAdvisories").innerHTML = w.advisories.map((a) =>
      '<div class="adv adv-' + a.level + '"><div class="adv-ico">' + a.icon + '</div><div><strong>' + esc(a.title) + "</strong><p>" + esc(a.text) + "</p></div></div>").join("");

    const hrs = w.hourly.slice(0, 24);
    $("wxChart").innerHTML = chart(hrs);
    $("wxHours").innerHTML = hrs.filter((_, i) => i % 3 === 0).map((h) =>
      '<div class="wx-hour"><div>' + (h.hour % 12 || 12) + (h.hour < 12 ? " AM" : " PM") + '</div><div class="icon">' + h.icon + "</div><div><strong>" + Math.round(h.temp) + "°</strong></div><div class=\"sub small\">💧" + (h.rain_prob ?? 0) + "%</div></div>").join("");

    $("wxDays").innerHTML = w.daily.map((d) =>
      '<div class="forecast-day"><div><strong>' + d.weekday + '</strong></div><div class="icon" title="' + esc(d.label) + '">' + d.icon + "</div><div>" + d.high + "° / " + d.low + "°</div>" +
      '<div class="sub small">💧 ' + (d.rain_prob ?? 0) + "% · " + (d.rain ?? 0) + " mm</div><div class=\"sub small\">💨 " + d.wind + " km/h</div></div>").join("");
    $("wxSummary").innerHTML =
      '<span>🌧️ 7-day rain: <strong>' + w.summary.rain7 + ' mm</strong></span><span>💦 Crop water loss (ET₀): <strong>' + w.summary.et0_7 +
      ' mm</strong></span><span>🌱 Growing degree days (base 10°C): <strong>' + w.summary.gdd7 + "</strong></span>";
    renderSaved();
  }

  function chart(hrs) {
    const W = 720, H = 170, pl = 34, pr = 10, pt = 14, pb = 26, n = hrs.length;
    const temps = hrs.map((h) => h.temp), mn = Math.floor(Math.min(...temps) - 1), mx = Math.ceil(Math.max(...temps) + 1);
    const x = (i) => pl + (i * (W - pl - pr)) / (n - 1), y = (t) => pt + ((mx - t) * (H - pt - pb)) / (mx - mn || 1);
    const bw = (W - pl - pr) / n * 0.6;
    let s = '<svg viewBox="0 0 ' + W + " " + H + '" class="wx-svg" role="img" aria-label="Temperature and rain chance for the next 24 hours">';
    hrs.forEach((h, i) => { const bh = ((h.rain_prob || 0) / 100) * (H - pt - pb); s += '<rect x="' + (x(i) - bw / 2) + '" y="' + (H - pb - bh) + '" width="' + bw + '" height="' + bh + '" fill="#93c5fd" opacity="0.55"/>'; });
    s += '<polyline fill="none" stroke="#16a34a" stroke-width="2.5" points="' + hrs.map((h, i) => x(i) + "," + y(h.temp)).join(" ") + '"/>';
    hrs.forEach((h, i) => { if (i % 3 === 0) s += '<text x="' + x(i) + '" y="' + (y(h.temp) - 7) + '" text-anchor="middle" font-size="11" fill="#14532d">' + Math.round(h.temp) + "°</text><text x=\"" + x(i) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="10" fill="#5b6b62">' + String(h.hour).padStart(2, "0") + "h</text>"; });
    return s + '<text x="4" y="12" font-size="10" fill="#5b6b62">°C</text></svg><div class="sub small">Green line: temperature · Blue bars: chance of rain</div>';
  }

  // ------------------------------------------------------------------ saved places
  function renderSaved() {
    const saved = read(LS_SAVED, []), box = $("wxSaved");
    box.innerHTML = saved.length ? "⭐ " + saved.map((p, i) => '<span class="chip" data-i="' + i + '">' + esc(p.name.split(",")[0]) + '<b data-del="' + i + '" title="Remove">×</b></span>').join("") : "";
  }
  $("wxSaved").addEventListener("click", (e) => {
    const saved = read(LS_SAVED, []);
    if (e.target.dataset.del !== undefined) { saved.splice(+e.target.dataset.del, 1); write(LS_SAVED, saved); renderSaved(); return; }
    const chip = e.target.closest(".chip");
    if (chip) { const p = saved[+chip.dataset.i]; const loc = { ...p, mode: "search" }; write(LS_LOC, loc); load(loc); }
  });
  $("wxSave").addEventListener("click", () => {
    if (!current) return;
    const saved = read(LS_SAVED, []);
    const name = $("wxPlace").textContent.replace("📍 ", "");
    if (!saved.some((p) => p.name === name)) { saved.push({ lat: current.lat, lon: current.lon, name }); write(LS_SAVED, saved.slice(-6)); }
    renderSaved();
  });

  // -------------------------------------------------------------------------- search
  let debounce;
  $("wxSearch").addEventListener("input", (e) => {
    clearTimeout(debounce);
    const q = e.target.value.trim(), ul = $("wxResults");
    if (q.length < 2) { ul.hidden = true; return; }
    debounce = setTimeout(async () => {
      try {
        const { results } = await api("/api/geocode?q=" + encodeURIComponent(q));
        ul.innerHTML = results.length ? results.map((r, i) => '<li data-i="' + i + '">' + esc(r.name) + "</li>").join("") : "<li class=\"none\">No places found</li>";
        ul._r = results; ul.hidden = false;
      } catch (err) { ul.innerHTML = '<li class="none">' + esc(err.message) + "</li>"; ul.hidden = false; }
    }, 350);
  });
  $("wxResults").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-i]");
    if (!li) return;
    const r = $("wxResults")._r[+li.dataset.i];
    const loc = { lat: r.lat, lon: r.lon, name: r.name, mode: "search" };
    write(LS_LOC, loc); $("wxResults").hidden = true; $("wxSearch").value = ""; load(loc);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".wx-search")) $("wxResults").hidden = true; });

  // ------------------------------------------------------------------------ buttons
  async function useGps() {
    setStatus("Detecting your location…");
    try { const loc = await getGps(); write(LS_LOC, loc); load(loc); }
    catch (e) {
      const fallback = read(LS_LOC, DEFAULT);
      pendingNote = "📍 " + e.message + " Showing " + fallback.name.split(",")[0] + " instead - search a place above to change it.";
      load(fallback);
    }
  }
  $("wxGps").addEventListener("click", useGps);
  $("wxRefresh").addEventListener("click", () => current && load(current));

  // ------------------------------------------------------------------------- start
  renderSaved();
  const stored = read(LS_LOC, null);
  if (stored && stored.mode === "search") load(stored); else useGps();
})();
