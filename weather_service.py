"""
Live weather + farming advisories for AgriGuide.

Data source: Open-Meteo (https://open-meteo.com) - free, no API key needed.
Place names: Open-Meteo geocoding (search) and OpenStreetMap Nominatim (reverse).

Public functions:
    search_places(query)            -> list of matching places
    reverse_geocode(lat, lon)       -> "Ghatkesar, Telangana, India" (best effort)
    get_weather(lat, lon, name)     -> normalised dict (current, hourly, daily, advisories)
"""
import time
from datetime import datetime

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "AgriGuide/2.0 (student project)"}
TIMEOUT = 10
CACHE_SECONDS = 600  # 10 minutes

_cache = {}


class WeatherError(Exception):
    pass


# --------------------------------------------------------------- weather codes
WMO = {
    0: ("Clear sky", "☀️", "☀️"), 1: ("Mostly clear", "🌤️", "🌙"),
    2: ("Partly cloudy", "⛅", "☁️"), 3: ("Overcast", "☁️", "☁️"),
    45: ("Fog", "🌫️", "🌫️"), 48: ("Rime fog", "🌫️", "🌫️"),
    51: ("Light drizzle", "🌦️", "🌧️"), 53: ("Drizzle", "🌦️", "🌧️"), 55: ("Heavy drizzle", "🌧️", "🌧️"),
    56: ("Freezing drizzle", "🌧️", "🌧️"), 57: ("Freezing drizzle", "🌧️", "🌧️"),
    61: ("Light rain", "🌦️", "🌧️"), 63: ("Rain", "🌧️", "🌧️"), 65: ("Heavy rain", "🌧️", "🌧️"),
    66: ("Freezing rain", "🌧️", "🌧️"), 67: ("Freezing rain", "🌧️", "🌧️"),
    71: ("Light snow", "🌨️", "🌨️"), 73: ("Snow", "🌨️", "🌨️"), 75: ("Heavy snow", "❄️", "❄️"),
    77: ("Snow grains", "🌨️", "🌨️"),
    80: ("Light showers", "🌦️", "🌧️"), 81: ("Showers", "🌧️", "🌧️"), 82: ("Violent showers", "⛈️", "⛈️"),
    85: ("Snow showers", "🌨️", "🌨️"), 86: ("Heavy snow showers", "❄️", "❄️"),
    95: ("Thunderstorm", "⛈️", "⛈️"), 96: ("Thunderstorm, hail", "⛈️", "⛈️"), 99: ("Severe thunderstorm, hail", "⛈️", "⛈️"),
}


def describe(code, is_day=True):
    label, day_icon, night_icon = WMO.get(code, ("Unknown", "🌡️", "🌡️"))
    return label, (day_icon if is_day else night_icon)


def wind_dir(deg):
    if deg is None:
        return ""
    names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return names[int((deg / 22.5) + 0.5) % 16]


# ------------------------------------------------------------------ geocoding
def search_places(query, count=6):
    query = (query or "").strip()
    if len(query) < 2:
        return []
    try:
        r = requests.get(GEOCODE_URL, params={"name": query, "count": count, "language": "en", "format": "json"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        raise WeatherError("Place search is unavailable right now. Check your internet connection.") from e
    out = []
    for p in r.json().get("results", []) or []:
        parts = [p.get("name"), p.get("admin1"), p.get("country")]
        out.append({
            "name": ", ".join(x for x in parts if x),
            "lat": p["latitude"], "lon": p["longitude"],
        })
    return out


def reverse_geocode(lat, lon):
    """Best-effort place name for GPS coordinates. Never raises."""
    key = ("rev", round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 86400:
        return hit[1]
    name = f"{lat:.2f}, {lon:.2f}"
    try:
        r = requests.get(REVERSE_URL, params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 12},
                         headers=HEADERS, timeout=6)
        if r.ok:
            a = r.json().get("address", {})
            local = (a.get("suburb") or a.get("village") or a.get("town") or a.get("city")
                     or a.get("county") or a.get("state_district"))
            parts = [local, a.get("state"), a.get("country")]
            parts = [p for p in parts if p]
            if parts:
                name = ", ".join(parts)
    except requests.RequestException:
        pass
    _cache[key] = (time.time(), name)
    return name


# ------------------------------------------------------------------- forecast
def _fetch_raw(lat, lon):
    params = {
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation",
            "weather_code", "cloud_cover", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
            "wind_gusts_10m"]),
        "hourly": ",".join([
            "temperature_2m", "relative_humidity_2m", "precipitation_probability", "precipitation",
            "weather_code", "wind_speed_10m", "is_day", "soil_moisture_1_to_3cm", "soil_temperature_6cm",
            "et0_fao_evapotranspiration"]),
        "daily": ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset",
            "uv_index_max", "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max",
            "wind_gusts_10m_max", "et0_fao_evapotranspiration"]),
    }
    try:
        r = requests.get(FORECAST_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise WeatherError("Could not reach the weather service. Check your internet connection and try again.") from e


def _num(v, nd=1):
    return None if v is None else round(float(v), nd)


def normalise(raw, name):
    """Turn Open-Meteo's response into the compact structure the page uses."""
    cur, hr, dy = raw["current"], raw["hourly"], raw["daily"]
    is_day = bool(cur.get("is_day", 1))
    label, icon = describe(cur.get("weather_code"), is_day)

    # Index of the current hour inside the hourly arrays
    now_key = cur["time"][:13]  # "2026-11-05T14"
    start = next((i for i, t in enumerate(hr["time"]) if t[:13] >= now_key), 0)
    sl = slice(start, start + 48)

    def h(field):
        return (hr.get(field) or [None] * len(hr["time"]))[sl]

    hourly = []
    for i, t in enumerate(hr["time"][sl]):
        lab, ic = describe(h("weather_code")[i], bool(h("is_day")[i]))
        hourly.append({
            "time": t, "hour": int(t[11:13]), "temp": _num(h("temperature_2m")[i]),
            "humidity": _num(h("relative_humidity_2m")[i], 0), "rain_prob": _num(h("precipitation_probability")[i], 0),
            "rain": _num(h("precipitation")[i]), "wind": _num(h("wind_speed_10m")[i]),
            "icon": ic, "label": lab,
        })

    soil_m = next((v for v in h("soil_moisture_1_to_3cm")[:3] if v is not None), None)
    soil_t = next((v for v in h("soil_temperature_6cm")[:3] if v is not None), None)

    daily = []
    for i, d in enumerate(dy["time"]):
        lab, ic = describe(dy["weather_code"][i])
        daily.append({
            "date": d, "weekday": datetime.strptime(d, "%Y-%m-%d").strftime("%a"),
            "high": _num(dy["temperature_2m_max"][i], 0), "low": _num(dy["temperature_2m_min"][i], 0),
            "rain": _num(dy["precipitation_sum"][i]), "rain_prob": _num(dy["precipitation_probability_max"][i], 0),
            "wind": _num(dy["wind_speed_10m_max"][i], 0), "gust": _num(dy["wind_gusts_10m_max"][i], 0),
            "uv": _num(dy["uv_index_max"][i], 0), "et0": _num(dy["et0_fao_evapotranspiration"][i]),
            "sunrise": dy["sunrise"][i][11:16], "sunset": dy["sunset"][i][11:16],
            "icon": ic, "label": lab,
        })
    daily[0]["weekday"] = "Today"

    # Growing degree days (base 10 C) - a standard crop-development measure
    gdd = [max(0.0, ((d["high"] + d["low"]) / 2) - 10) for d in daily if d["high"] is not None]

    data = {
        "location": {"name": name, "lat": raw["latitude"], "lon": raw["longitude"],
                     "timezone": raw.get("timezone", "")},
        "current": {
            "temp": _num(cur["temperature_2m"]), "feels_like": _num(cur["apparent_temperature"]),
            "humidity": _num(cur["relative_humidity_2m"], 0), "wind": _num(cur["wind_speed_10m"]),
            "wind_dir": wind_dir(cur.get("wind_direction_10m")), "gust": _num(cur.get("wind_gusts_10m")),
            "pressure": _num(cur.get("pressure_msl"), 0), "cloud": _num(cur.get("cloud_cover"), 0),
            "rain_now": _num(cur.get("precipitation")), "label": label, "icon": icon, "is_day": is_day,
            "soil_moisture": None if soil_m is None else round(soil_m * 100, 0),  # % by volume
            "soil_temp": _num(soil_t), "uv": daily[0]["uv"], "time": cur["time"],
        },
        "hourly": hourly, "daily": daily,
        "summary": {"gdd7": round(sum(gdd), 0), "rain7": round(sum(d["rain"] or 0 for d in daily), 1),
                    "et0_7": round(sum(d["et0"] or 0 for d in daily), 1)},
    }
    data["advisories"] = build_advisories(data)
    return data


# ---------------------------------------------------------- farming advisories
def _ranges(hours):
    """[6,7,8,15,16] -> ['6:00-9:00', '15:00-17:00']"""
    out, run = [], []
    for x in hours:
        if run and x == run[-1] + 1:
            run.append(x)
        else:
            if run:
                out.append(run)
            run = [x]
    if run:
        out.append(run)
    return [f"{r[0]:02d}:00-{r[-1] + 1:02d}:00" for r in out]


def build_advisories(w):
    cur, hourly, daily = w["current"], w["hourly"], w["daily"]
    adv = []

    # 1. Spraying window (next 24 h, daylight 05-19): calm wind, no rain
    good = [x["hour"] for x in hourly[:24]
            if 5 <= x["hour"] < 19 and (x["wind"] or 0) <= 15 and (x["rain_prob"] or 0) <= 30 and (x["rain"] or 0) < 0.1]
    if good:
        adv.append({"level": "good", "icon": "🧴", "title": "Spray window",
                    "text": "Best time for pesticide/fungicide spraying (wind under 15 km/h, little rain chance): "
                            + ", ".join(_ranges(good)[:3]) + "."})
    else:
        adv.append({"level": "warn", "icon": "🧴", "title": "Avoid spraying",
                    "text": "Wind or rain in the next 24 hours would wash off or drift spray. Wait for a calmer, drier window."})

    # 2. Irrigation advice from rain forecast + soil moisture + evapotranspiration
    rain48 = sum(d["rain"] or 0 for d in daily[:2])
    et_today = daily[0]["et0"] or 0
    sm = cur["soil_moisture"]
    sm_txt = f" Topsoil moisture is about {int(sm)}%." if sm is not None else ""
    if rain48 >= 10:
        adv.append({"level": "good", "icon": "💧", "title": "Skip irrigation",
                    "text": f"About {rain48:.0f} mm of rain is expected in the next 2 days. Save water and check drainage.{sm_txt}"})
    elif sm is not None and sm < 15 and rain48 < 3:
        adv.append({"level": "alert", "icon": "💧", "title": "Irrigate soon",
                    "text": f"Soil is dry and little rain is coming.{sm_txt} Crops lose roughly {et_today:.1f} mm of water per day - "
                            "irrigate early morning or evening."})
    elif rain48 >= 3:
        adv.append({"level": "info", "icon": "💧", "title": "Light irrigation only",
                    "text": f"Some rain ({rain48:.0f} mm) is likely in 2 days. Hold off unless the crop shows stress.{sm_txt}"})
    else:
        adv.append({"level": "info", "icon": "💧", "title": "Normal irrigation",
                    "text": f"No significant rain expected. Daily crop water loss is about {et_today:.1f} mm.{sm_txt}"})

    # 3. Temperature stress
    hi, lo = daily[0]["high"], daily[0]["low"]
    if hi is not None and hi >= 38:
        adv.append({"level": "alert", "icon": "🔥", "title": "Heat stress",
                    "text": f"High of {hi:.0f}°C today. Irrigate in the evening, mulch the soil and avoid midday field work."})
    elif hi is not None and hi >= 35:
        adv.append({"level": "warn", "icon": "🌡️", "title": "Hot day",
                    "text": f"High of {hi:.0f}°C. Watch for wilting, especially in flowering crops."})
    if lo is not None and lo <= 2:
        adv.append({"level": "alert", "icon": "❄️", "title": "Frost risk",
                    "text": f"Low of {lo:.0f}°C tonight. Cover young plants or irrigate lightly in the evening."})
    elif lo is not None and lo <= 8:
        adv.append({"level": "warn", "icon": "🥶", "title": "Cold night",
                    "text": f"Low of {lo:.0f}°C. Growth of warm-season crops may slow down."})

    # 4. Fungal / blight risk: warm + humid + wet leaves
    humid_hrs = sum(1 for x in hourly[:48] if (x["humidity"] or 0) >= 85 and 15 <= (x["temp"] or 0) <= 30)
    wet_days = sum(1 for d in daily[:3] if (d["rain"] or 0) >= 2)
    score = humid_hrs / 48 * 100 + wet_days * 15
    if score >= 55:
        adv.append({"level": "alert", "icon": "🍄", "title": "High disease risk",
                    "text": "Warm, humid and wet conditions favour blight, blast and leaf-spot fungi. Scout fields daily and "
                            "keep protective fungicide ready (follow local agriculture officer advice)."})
    elif score >= 30:
        adv.append({"level": "warn", "icon": "🍄", "title": "Moderate disease risk",
                    "text": "Humidity is high enough for fungal diseases to spread. Avoid evening irrigation and keep plants well spaced."})
    else:
        adv.append({"level": "good", "icon": "🍃", "title": "Low disease risk",
                    "text": "Conditions are not especially favourable for fungal diseases."})

    # 5. Storms / wind
    worst = max(daily[:3], key=lambda d: d["rain"] or 0)
    if (worst["rain"] or 0) >= 50:
        adv.append({"level": "alert", "icon": "⛈️", "title": "Very heavy rain",
                    "text": f"{worst['rain']:.0f} mm expected on {worst['weekday']}. Open drainage channels, delay fertiliser and harvest ripe produce early."})
    elif (worst["rain"] or 0) >= 20:
        adv.append({"level": "warn", "icon": "🌧️", "title": "Heavy rain ahead",
                    "text": f"{worst['rain']:.0f} mm expected on {worst['weekday']}. Postpone fertiliser and spraying."})
    gust = max((d["gust"] or 0) for d in daily[:2])
    if gust >= 40:
        adv.append({"level": "warn", "icon": "💨", "title": "Strong winds",
                    "text": f"Gusts up to {gust:.0f} km/h. Stake tall crops (maize, banana, sugarcane) and avoid spraying."})

    # 6. UV / field-work comfort
    if (cur["uv"] or 0) >= 8:
        adv.append({"level": "warn", "icon": "😎", "title": "Very high UV",
                    "text": "Do field work before 10:00 or after 16:00 and wear a hat."})

    # 7. Best day for field work (harvest, sowing, ploughing)
    dry_days = [d["weekday"] for d in daily[:5] if (d["rain"] or 0) < 1 and (d["rain_prob"] or 0) < 30]
    if dry_days:
        adv.append({"level": "info", "icon": "🚜", "title": "Field-work days",
                    "text": "Dry days good for sowing, harvesting or ploughing: " + ", ".join(dry_days) + "."})
    return adv


# --------------------------------------------------------------------- public
def get_weather(lat, lon, name=None):
    key = ("wx", round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        data = dict(hit[1])
        if name:
            data["location"] = {**data["location"], "name": name}
        return data
    raw = _fetch_raw(lat, lon)
    data = normalise(raw, name or reverse_geocode(lat, lon))
    _cache[key] = (time.time(), data)
    return data
