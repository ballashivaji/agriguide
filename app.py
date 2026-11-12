"""
AgriGuide - Smart Agriculture Information System
--------------------------------------------------
A Flask + SQLite web application (rule-based, no AI/ML).

NOTE ON DATABASE:
This app uses SQLite (agriguide.db, created automatically on first run) so it
runs anywhere without extra setup. The file database/agriguide.sql contains
the equivalent MySQL schema + seed data if you'd rather run it on MySQL/XAMPP
for your college project/deployment. See README.md for how to switch.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import base64
import io
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agriguide.db")

app = Flask(__name__)
app.secret_key = "agriguide-secret-key-change-this-in-production"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB photo limit

import weather_service
from ml.predictor import analyze as analyze_leaf, covered_crops, models_status


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables (if they don't exist) and seed sample data."""
    first_time = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'Farmer',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS crops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        soil_type TEXT NOT NULL,
        season TEXT NOT NULL,
        water_requirement TEXT NOT NULL,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS irrigation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        soil_condition TEXT NOT NULL,
        rainfall TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        tips TEXT
    );

    CREATE TABLE IF NOT EXISTS fertilizer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        soil_type TEXT NOT NULL,
        nitrogen TEXT,
        phosphorus TEXT,
        potassium TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS diseases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        symptom TEXT NOT NULL,
        disease_name TEXT NOT NULL,
        disease_type TEXT,
        causes TEXT,
        prevention TEXT
    );

    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        crop TEXT,
        result TEXT NOT NULL,
        confidence REAL,
        healthy INTEGER DEFAULT 0,
        mode TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    db.commit()

    if first_time:
        # ---- Seed crops ----
        cur.executemany(
            "INSERT INTO crops (crop_name, soil_type, season, water_requirement, notes) VALUES (?, ?, ?, ?, ?)",
            [
                ("Cotton", "Black Soil", "Kharif", "Medium", "High yield in black soil, good for Kharif season."),
                ("Soybean", "Black Soil", "Kharif", "Medium", "Suitable for medium water availability."),
                ("Groundnut", "Black Soil", "Kharif", "Low", "Grows well in black soil with moderate water."),
                ("Wheat", "Loamy Soil", "Rabi", "Medium", "Best suited for cool weather and loamy soil."),
                ("Rice", "Clay Soil", "Kharif", "High", "Requires standing water, ideal for clay soil."),
                ("Sugarcane", "Loamy Soil", "Kharif", "High", "Long duration crop needing high water."),
                ("Mustard", "Sandy Soil", "Rabi", "Low", "Drought-tolerant, grows in sandy soil."),
                ("Maize", "Red Soil", "Kharif", "Medium", "Adapts well to red soil with moderate rainfall."),
                ("Chickpea", "Sandy Soil", "Rabi", "Low", "Needs little irrigation, ideal for dry regions."),
                ("Sunflower", "Red Soil", "Rabi", "Medium", "Tolerates moderate drought, good oilseed crop."),
            ],
        )

        # ---- Seed irrigation rules ----
        cur.executemany(
            "INSERT INTO irrigation (crop_name, soil_condition, rainfall, recommendation, tips) VALUES (?, ?, ?, ?, ?)",
            [
                ("Rice", "Dry", "No Rain", "Watering is Recommended",
                 "Avoid overwatering.|Use drip or sprinkler if possible.|Check soil moisture regularly."),
                ("Rice", "Normal", "Moderate Rain", "Moderate Watering Advised",
                 "Water every alternate day.|Monitor field for waterlogging."),
                ("Rice", "Wet", "Heavy Rain", "No Watering Required",
                 "Ensure proper drainage.|Avoid irrigation until soil dries."),
                ("Wheat", "Dry", "No Rain", "Watering is Recommended",
                 "Irrigate early morning or evening.|Use mulching to retain moisture."),
                ("Cotton", "Dry", "No Rain", "Watering is Recommended",
                 "Deep watering once a week.|Check for pest activity during dry spells."),
                ("Cotton", "Normal", "Moderate Rain", "Moderate Watering Advised",
                 "Water once every 5-7 days.|Watch for signs of stress."),
                ("Maize", "Dry", "No Rain", "Watering is Recommended",
                 "Irrigate at critical growth stages.|Mulch to conserve moisture."),
            ],
        )

        # ---- Seed fertilizer info ----
        cur.executemany(
            "INSERT INTO fertilizer (crop_name, soil_type, nitrogen, phosphorus, potassium, notes) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("Cotton", "Black Soil", "60-80 kg/ha", "40-60 kg/ha", "40-50 kg/ha",
                 "Apply fertilizer based on soil test results.|Use organic matter for better soil health."),
                ("Rice", "Clay Soil", "80-100 kg/ha", "30-40 kg/ha", "30-40 kg/ha",
                 "Split nitrogen application into 3 doses.|Add organic manure before transplanting."),
                ("Wheat", "Loamy Soil", "100-120 kg/ha", "50-60 kg/ha", "40-50 kg/ha",
                 "Apply full phosphorus and potassium at sowing.|Top-dress nitrogen after first irrigation."),
                ("Maize", "Red Soil", "70-90 kg/ha", "35-45 kg/ha", "30-40 kg/ha",
                 "Apply nitrogen in split doses.|Ensure adequate potassium for grain filling."),
                ("Sugarcane", "Loamy Soil", "150-180 kg/ha", "60-80 kg/ha", "60-80 kg/ha",
                 "Apply farmyard manure before planting.|Irrigate immediately after fertilizer application."),
            ],
        )

        # ---- Seed disease info ----
        cur.executemany(
            "INSERT INTO diseases (crop_name, symptom, disease_name, disease_type, causes, prevention) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("Tomato", "Yellow Leaves", "Early Blight", "Fungal Disease",
                 "Excess moisture|Poor air circulation|Fungal infection",
                 "Remove affected leaves|Maintain proper spacing|Use disease-free seeds"),
                ("Tomato", "Brown Spots", "Septoria Leaf Spot", "Fungal Disease",
                 "High humidity|Overcrowded planting|Water splashing on leaves",
                 "Rotate crops yearly|Avoid overhead watering|Apply fungicide if needed"),
                ("Tomato", "Leaf Drop", "Bacterial Wilt", "Bacterial Disease",
                 "Soil-borne bacteria|Warm humid weather|Contaminated tools",
                 "Use resistant varieties|Sterilize tools|Practice crop rotation"),
                ("Cotton", "Wilting", "Fusarium Wilt", "Fungal Disease",
                 "Soil-borne fungus|Poor drainage|Continuous cropping",
                 "Use resistant varieties|Practice crop rotation|Improve field drainage"),
                ("Rice", "Leaf Blast Spots", "Rice Blast", "Fungal Disease",
                 "High nitrogen use|Humid weather|Dense planting",
                 "Use resistant varieties|Avoid excess nitrogen|Ensure good field drainage"),
                ("Wheat", "Yellow Stripes", "Yellow Rust", "Fungal Disease",
                 "Cool humid weather|Susceptible varieties|Wind-spread spores",
                 "Use resistant varieties|Timely sowing|Apply fungicide at early stage"),
            ],
        )

        # ---- Default admin account ----
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@agriguide.com", generate_password_hash("admin123"), "Admin"),
        )

        db.commit()

    db.close()


# ----------------------------------------------------------------------
# Auth helpers
# ----------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


def api_login_required(f):
    """Like login_required but answers JSON 401 (for fetch() calls)."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Please login again."), 401
        return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "error")
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            flash("Admin access only.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {
        "current_user_name": session.get("name"),
        "current_user_role": session.get("role"),
        "logged_in": "user_id" in session,
    }


# ----------------------------------------------------------------------
# Public routes
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "Farmer")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role),
        )
        db.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ? OR name = ?", (identifier, identifier)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            if user["role"] == "Admin":
                return redirect(url_for("admin"))
            return redirect(url_for("dashboard"))

        flash("Invalid credentials. Please try again.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ----------------------------------------------------------------------
# Farmer-facing routes
# ----------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    recent = db.execute(
        "SELECT * FROM scan_history WHERE user_id = ? ORDER BY id DESC LIMIT 3", (session["user_id"],)
    ).fetchall()
    return render_template("dashboard.html", recent=recent)


@app.route("/crop", methods=["GET", "POST"])
@login_required
def crop():
    db = get_db()
    soil_types = [r["soil_type"] for r in db.execute("SELECT DISTINCT soil_type FROM crops").fetchall()]
    seasons = [r["season"] for r in db.execute("SELECT DISTINCT season FROM crops").fetchall()]
    water_levels = [r["water_requirement"] for r in db.execute("SELECT DISTINCT water_requirement FROM crops").fetchall()]

    results = None
    if request.method == "POST":
        soil_type = request.form.get("soil_type")
        season = request.form.get("season")
        water = request.form.get("water")

        # Rule-based lookup (exact match first, then relaxed match on soil+season)
        results = db.execute(
            "SELECT * FROM crops WHERE soil_type = ? AND season = ? AND water_requirement = ?",
            (soil_type, season, water),
        ).fetchall()

        if not results:
            results = db.execute(
                "SELECT * FROM crops WHERE soil_type = ? AND season = ?",
                (soil_type, season),
            ).fetchall()

    return render_template(
        "crop.html", soil_types=soil_types, seasons=seasons,
        water_levels=water_levels, results=results
    )


@app.route("/irrigation", methods=["GET", "POST"])
@login_required
def irrigation():
    db = get_db()
    crop_names = [r["crop_name"] for r in db.execute("SELECT DISTINCT crop_name FROM irrigation").fetchall()]

    result = None
    tips = []
    if request.method == "POST":
        crop_name = request.form.get("crop_name")
        soil_condition = request.form.get("soil_condition")
        rainfall = request.form.get("rainfall")

        row = db.execute(
            "SELECT * FROM irrigation WHERE crop_name = ? AND soil_condition = ?",
            (crop_name, soil_condition),
        ).fetchone()

        if row:
            result = row["recommendation"]
            tips = row["tips"].split("|") if row["tips"] else []
        else:
            # Fallback simple rule engine (Step 8 logic) if no exact DB match
            if soil_condition == "Dry":
                result = "Watering is Recommended"
                tips = ["Water early morning or evening.", "Check soil moisture before irrigating."]
            elif soil_condition == "Normal":
                result = "Moderate Watering Advised"
                tips = ["Water every alternate day.", "Monitor crop for stress signs."]
            else:  # Wet
                result = "No Watering Required"
                tips = ["Ensure proper field drainage.", "Avoid irrigation until soil dries out."]

    return render_template(
        "irrigation.html", crop_names=crop_names, result=result, tips=tips
    )


@app.route("/fertilizer", methods=["GET", "POST"])
@login_required
def fertilizer():
    db = get_db()
    crop_names = [r["crop_name"] for r in db.execute("SELECT DISTINCT crop_name FROM fertilizer").fetchall()]
    soil_types = [r["soil_type"] for r in db.execute("SELECT DISTINCT soil_type FROM fertilizer").fetchall()]

    result = None
    notes = []
    searched = False
    if request.method == "POST":
        searched = True
        crop_name = request.form.get("crop_name")
        soil_type = request.form.get("soil_type")

        result = db.execute(
            "SELECT * FROM fertilizer WHERE crop_name = ? AND soil_type = ?",
            (crop_name, soil_type),
        ).fetchone()

        if not result:
            result = db.execute(
                "SELECT * FROM fertilizer WHERE crop_name = ?", (crop_name,)
            ).fetchone()

        if result and result["notes"]:
            notes = result["notes"].split("|")

    return render_template(
        "fertilizer.html", crop_names=crop_names, soil_types=soil_types,
        result=result, notes=notes, searched=searched
    )


@app.route("/disease", methods=["GET", "POST"])
@login_required
def disease():
    db = get_db()
    crop_names = [r["crop_name"] for r in db.execute("SELECT DISTINCT crop_name FROM diseases").fetchall()]
    symptoms = [r["symptom"] for r in db.execute("SELECT DISTINCT symptom FROM diseases").fetchall()]

    result = None
    causes = []
    prevention = []
    searched = False
    photo = None  # photo-prediction details for the template
    if request.method == "POST" and request.form.get("mode") == "photo":
        photo = analyze_photo(db, request.files.get("leaf_photo"), request.form.get("photo_crop", ""))
    elif request.method == "POST":
        searched = True
        crop_name = request.form.get("crop_name")
        symptom = request.form.get("symptom")

        result = db.execute(
            "SELECT * FROM diseases WHERE crop_name = ? AND symptom = ?",
            (crop_name, symptom),
        ).fetchone()

        if result:
            causes = result["causes"].split("|") if result["causes"] else []
            prevention = result["prevention"].split("|") if result["prevention"] else []

    supported = covered_crops()
    photo_crops = sorted(set(supported) | set(crop_names))
    return render_template(
        "disease.html", crop_names=crop_names, symptoms=symptoms, photo_crops=photo_crops,
        supported_crops=supported,
        result=result, causes=causes, prevention=prevention, searched=searched,
        photo=photo,
    )


def analyze_photo(db, file, crop):
    """Run the leaf-photo pipeline and match its output to a diseases record."""
    out = {"error": None, "record": None, "crop": crop, "info": None, "status": "ok"}
    if not file or not file.filename:
        out["error"] = "Please choose a leaf photo first."
        return out
    data = file.read()
    pred = analyze_leaf(data, crop)
    out["pred"] = pred
    out["status"] = pred["status"]
    mime = file.mimetype if (file.mimetype or "").startswith("image/") else "image/jpeg"
    out["preview"] = f"data:{mime};base64," + base64.b64encode(data).decode()

    if pred["status"] in ("error", "not_leaf", "unsupported_crop", "crop_mismatch"):
        out["error"] = pred["message"]
        return out
    if pred["status"] == "uncertain":
        out["error"] = pred["message"]
        return out

    parsed = pred.get("parsed")
    if parsed:                                   # pretrained / trained model
        out["healthy"] = parsed["healthy"]
        out["display"] = parsed["display"]
        info = dict(parsed["info"])
        info["source"] = "AgriGuide knowledge base"
        if not parsed["healthy"] and parsed["crop"]:
            row = db.execute(
                "SELECT * FROM diseases WHERE LOWER(crop_name) = LOWER(?) AND LOWER(disease_name) LIKE ?",
                (parsed["crop"], f"%{parsed['disease'].lower().split(' (')[0]}%"),
            ).fetchone()
            if row:                              # admin-entered record wins for causes/prevention
                out["record"] = row
                if row["causes"]:
                    info["causes"] = row["causes"].split("|")
                if row["prevention"]:
                    info["prevention"] = row["prevention"].split("|")
                info["type"] = row["disease_type"] or info["type"]
                info["source"] = "AgriGuide database + knowledge base"
        out["info"] = info
        out["crop_name"] = parsed["crop"]
        out["disease_name"] = parsed["disease"]
    else:                                        # rough colour scan fallback
        label = pred.get("symptom")
        out["healthy"] = label == "Healthy"
        out["display"] = "Leaf looks healthy" if out["healthy"] else f"Symptom detected: {label}"
        if not out["healthy"]:
            if crop:
                row = db.execute("SELECT * FROM diseases WHERE crop_name = ? AND symptom = ?", (crop, label)).fetchone()
            else:
                row = db.execute("SELECT * FROM diseases WHERE symptom = ?", (label,)).fetchone()
            out["record"] = row
            if row:
                out["info"] = {"name": row["disease_name"], "type": row["disease_type"], "symptoms": [row["symptom"]],
                               "causes": (row["causes"] or "").split("|"), "treatment": [],
                               "prevention": (row["prevention"] or "").split("|"), "source": "AgriGuide database"}
        out["crop_name"] = crop
        out["disease_name"] = label

    # save to the user's scan history
    db.execute(
        "INSERT INTO scan_history (user_id, crop, result, confidence, healthy, mode) VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], out.get("crop_name") or crop or "", out.get("display") or "", pred["confidence"],
         1 if out["healthy"] else 0, pred["mode"]),
    )
    db.commit()
    return out


@app.errorhandler(413)
def too_large(_e):
    flash("Photo is too large (max 8 MB).", "error")
    return redirect(url_for("disease"))


@app.route("/history")
@login_required
def history():
    db = get_db()
    rows = db.execute("SELECT * FROM scan_history WHERE user_id = ? ORDER BY id DESC LIMIT 100",
                      (session["user_id"],)).fetchall()
    return render_template("history.html", rows=rows)


@app.route("/history/clear")
@login_required
def history_clear():
    db = get_db()
    db.execute("DELETE FROM scan_history WHERE user_id = ?", (session["user_id"],))
    db.commit()
    flash("Scan history cleared.", "success")
    return redirect(url_for("history"))


# ----------------------------------------------------------------------
# Weather (live data from Open-Meteo, no API key needed)
# ----------------------------------------------------------------------
@app.route("/weather")
@login_required
def weather():
    return render_template("weather.html")


@app.route("/api/weather")
@api_login_required
def api_weather():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
    except (KeyError, ValueError):
        return jsonify(error="Invalid location."), 400
    try:
        return jsonify(weather_service.get_weather(lat, lon, request.args.get("name") or None))
    except weather_service.WeatherError as e:
        return jsonify(error=str(e)), 502
    except Exception:
        app.logger.exception("weather failure")
        return jsonify(error="Weather data could not be processed. Please try again."), 500


@app.route("/api/geocode")
@api_login_required
def api_geocode():
    try:
        return jsonify(results=weather_service.search_places(request.args.get("q", "")))
    except weather_service.WeatherError as e:
        return jsonify(error=str(e)), 502


@app.route("/api/model-status")
@api_login_required
def api_model_status():
    return jsonify(models_status())


@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)


# ----------------------------------------------------------------------
# Admin routes
# ----------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    counts = {
        "crops": db.execute("SELECT COUNT(*) c FROM crops").fetchone()["c"],
        "diseases": db.execute("SELECT COUNT(*) c FROM diseases").fetchone()["c"],
        "fertilizer": db.execute("SELECT COUNT(*) c FROM fertilizer").fetchone()["c"],
        "irrigation": db.execute("SELECT COUNT(*) c FROM irrigation").fetchone()["c"],
        "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
    }
    return render_template("admin.html", counts=counts)


@app.route("/admin/crops", methods=["GET", "POST"])
@admin_required
def admin_crops():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO crops (crop_name, soil_type, season, water_requirement, notes) VALUES (?, ?, ?, ?, ?)",
            (
                request.form["crop_name"], request.form["soil_type"],
                request.form["season"], request.form["water_requirement"],
                request.form.get("notes", ""),
            ),
        )
        db.commit()
        flash("Crop added successfully.", "success")
        return redirect(url_for("admin_crops"))

    rows = db.execute("SELECT * FROM crops ORDER BY id DESC").fetchall()
    return render_template("admin_list.html", title="Manage Crops", rows=rows,
                            columns=["id", "crop_name", "soil_type", "season", "water_requirement", "notes"],
                            add_endpoint="admin_crops", delete_endpoint="admin_crops_delete",
                            fields=[
                                {"name": "crop_name", "label": "Crop Name", "type": "text"},
                                {"name": "soil_type", "label": "Soil Type", "type": "text"},
                                {"name": "season", "label": "Season", "type": "text"},
                                {"name": "water_requirement", "label": "Water Requirement", "type": "text"},
                                {"name": "notes", "label": "Notes", "type": "text"},
                            ])


@app.route("/admin/crops/delete/<int:item_id>")
@admin_required
def admin_crops_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM crops WHERE id = ?", (item_id,))
    db.commit()
    flash("Crop deleted.", "success")
    return redirect(url_for("admin_crops"))


@app.route("/admin/fertilizer", methods=["GET", "POST"])
@admin_required
def admin_fertilizer():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO fertilizer (crop_name, soil_type, nitrogen, phosphorus, potassium, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form["crop_name"], request.form["soil_type"],
                request.form.get("nitrogen", ""), request.form.get("phosphorus", ""),
                request.form.get("potassium", ""), request.form.get("notes", ""),
            ),
        )
        db.commit()
        flash("Fertilizer info added.", "success")
        return redirect(url_for("admin_fertilizer"))

    rows = db.execute("SELECT * FROM fertilizer ORDER BY id DESC").fetchall()
    return render_template("admin_list.html", title="Manage Fertilizer Info", rows=rows,
                            columns=["id", "crop_name", "soil_type", "nitrogen", "phosphorus", "potassium", "notes"],
                            add_endpoint="admin_fertilizer", delete_endpoint="admin_fertilizer_delete",
                            fields=[
                                {"name": "crop_name", "label": "Crop Name", "type": "text"},
                                {"name": "soil_type", "label": "Soil Type", "type": "text"},
                                {"name": "nitrogen", "label": "Nitrogen (N)", "type": "text"},
                                {"name": "phosphorus", "label": "Phosphorus (P)", "type": "text"},
                                {"name": "potassium", "label": "Potassium (K)", "type": "text"},
                                {"name": "notes", "label": "Notes", "type": "text"},
                            ])


@app.route("/admin/fertilizer/delete/<int:item_id>")
@admin_required
def admin_fertilizer_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM fertilizer WHERE id = ?", (item_id,))
    db.commit()
    flash("Fertilizer entry deleted.", "success")
    return redirect(url_for("admin_fertilizer"))


@app.route("/admin/diseases", methods=["GET", "POST"])
@admin_required
def admin_diseases():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO diseases (crop_name, symptom, disease_name, disease_type, causes, prevention) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form["crop_name"], request.form["symptom"],
                request.form["disease_name"], request.form.get("disease_type", ""),
                request.form.get("causes", ""), request.form.get("prevention", ""),
            ),
        )
        db.commit()
        flash("Disease info added.", "success")
        return redirect(url_for("admin_diseases"))

    rows = db.execute("SELECT * FROM diseases ORDER BY id DESC").fetchall()
    return render_template("admin_list.html", title="Manage Diseases", rows=rows,
                            columns=["id", "crop_name", "symptom", "disease_name", "disease_type", "causes", "prevention"],
                            add_endpoint="admin_diseases", delete_endpoint="admin_diseases_delete",
                            fields=[
                                {"name": "crop_name", "label": "Crop Name", "type": "text"},
                                {"name": "symptom", "label": "Symptom", "type": "text"},
                                {"name": "disease_name", "label": "Disease Name", "type": "text"},
                                {"name": "disease_type", "label": "Disease Type", "type": "text"},
                                {"name": "causes", "label": "Causes (use | to separate)", "type": "text"},
                                {"name": "prevention", "label": "Prevention (use | to separate)", "type": "text"},
                            ])


@app.route("/admin/diseases/delete/<int:item_id>")
@admin_required
def admin_diseases_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM diseases WHERE id = ?", (item_id,))
    db.commit()
    flash("Disease entry deleted.", "success")
    return redirect(url_for("admin_diseases"))


@app.route("/admin/soil", methods=["GET", "POST"])
@admin_required
def admin_soil():
    """Manage Soil = handled as soil-related irrigation rules."""
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO irrigation (crop_name, soil_condition, rainfall, recommendation, tips) VALUES (?, ?, ?, ?, ?)",
            (
                request.form["crop_name"], request.form["soil_condition"],
                request.form["rainfall"], request.form["recommendation"],
                request.form.get("tips", ""),
            ),
        )
        db.commit()
        flash("Irrigation/soil rule added.", "success")
        return redirect(url_for("admin_soil"))

    rows = db.execute("SELECT * FROM irrigation ORDER BY id DESC").fetchall()
    return render_template("admin_list.html", title="Manage Soil & Irrigation Rules", rows=rows,
                            columns=["id", "crop_name", "soil_condition", "rainfall", "recommendation", "tips"],
                            add_endpoint="admin_soil", delete_endpoint="admin_soil_delete",
                            fields=[
                                {"name": "crop_name", "label": "Crop Name", "type": "text"},
                                {"name": "soil_condition", "label": "Soil Condition", "type": "text"},
                                {"name": "rainfall", "label": "Rainfall", "type": "text"},
                                {"name": "recommendation", "label": "Recommendation", "type": "text"},
                                {"name": "tips", "label": "Tips (use | to separate)", "type": "text"},
                            ])


@app.route("/admin/soil/delete/<int:item_id>")
@admin_required
def admin_soil_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM irrigation WHERE id = ?", (item_id,))
    db.commit()
    flash("Rule deleted.", "success")
    return redirect(url_for("admin_soil"))


@app.route("/admin/users")
@admin_required
def admin_users():
    db = get_db()
    rows = db.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC").fetchall()
    return render_template("admin_users.html", rows=rows)


@app.route("/admin/users/delete/<int:item_id>")
@admin_required
def admin_users_delete(item_id):
    if item_id == session.get("user_id"):
        flash("You cannot delete your own account while logged in.", "error")
        return redirect(url_for("admin_users"))
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (item_id,))
    db.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))


# ----------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
else:
    # Ensure DB exists when imported by a WSGI server too.
    init_db()
