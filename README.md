# 🌾 AgriGuide – Smart Agriculture Information System

A complete Flask web application that helps farmers get crop recommendations,
irrigation guidance, fertilizer information, and plant disease information —
using simple rule-based logic, plus a photo-based disease predictor on the Disease page.

## Tech Stack
- **Frontend:** HTML, CSS (custom, no framework needed), JavaScript
- **Backend:** Python + Flask
- **Database:** SQLite (built-in, zero setup) — a MySQL schema is also provided
  in `database/agriguide.sql` if you'd rather run it on MySQL/XAMPP

## Folder Structure
```
AgriGuide/
│
├── app.py                     ← Flask app: all routes + logic
├── requirements.txt
├── agriguide.db                ← auto-created SQLite database (on first run)
│
├── templates/
│   ├── base_public.html        ← layout for Home/Login/Register
│   ├── base_app.html           ← layout for logged-in pages (sidebar)
│   ├── index.html               (Home)
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── crop.html                (Crop Recommendation)
│   ├── irrigation.html          (Irrigation Guidance)
│   ├── fertilizer.html          (Fertilizer Information)
│   ├── disease.html             (Plant Disease Information)
│   ├── weather.html
│   ├── profile.html
│   ├── admin.html               (Admin dashboard)
│   ├── admin_list.html          (generic add/list/delete UI, reused)
│   └── admin_users.html
│
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
│
└── database/
    └── agriguide.sql            ← MySQL schema + seed data (reference)
```

## Setup & Run

1. Install Python 3.9+ if you don't already have it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open your browser at **http://127.0.0.1:5000**

The SQLite database (`agriguide.db`) is created automatically the first time
you run the app, and it's pre-loaded with sample crops, irrigation rules,
fertilizer info, and disease records so you can test everything immediately.

### Demo Login
- **Admin:** `admin@agriguide.com` / `admin123`
- **Farmer:** register your own account from the Register page.

## Switching to MySQL (optional)
If your course requires MySQL specifically (e.g. via XAMPP):
1. Import `database/agriguide.sql` into MySQL.
2. Replace the `sqlite3` calls in `app.py` with `mysql-connector-python` or
   `PyMySQL`, updating `get_db()` to connect to your MySQL server instead.
   The table/column names are identical, so route logic won't need to change.

## How the "Smart" Logic Works (Rule-Based, No AI)
- **Crop Recommendation:** looks up the `crops` table for rows matching the
  selected Soil Type + Season + Water Availability (falls back to Soil +
  Season if there's no exact match).
- **Irrigation Guidance:** looks up a `soil_condition` + `crop` rule in the
  `irrigation` table; if no exact rule exists, falls back to the simple
  Dry/Normal/Wet logic described in the project plan.
- **Fertilizer Information:** looks up `fertilizer` table by Crop + Soil Type.
- **Plant Disease Information:** looks up `diseases` table by Crop + Symptom.
- **Weather:** live data from Open-Meteo (no API key) - see "Weather" below.

## Admin Panel
Log in with the admin account to:
- Add/delete Crops
- Add/delete Soil & Irrigation rules
- Add/delete Fertilizer records
- Add/delete Disease records
- View/delete Users

## Next Steps / Ideas to Extend
- Add "Edit" (not just Add/Delete) to the admin panel
- Add crop images and disease photos
- Add search/filter on the admin tables
- Deploy to a host like PythonAnywhere, Render, or Railway for your presentation


## 🌦️ Weather (live, no API key)
Code: `weather_service.py`, `static/js/weather.js`, routes `/weather`, `/api/weather`, `/api/geocode`.
- **📍 Use my location** (browser GPS) or search any village/town/city; save favourite places.
- Current conditions, next-24-hour chart, 7-day forecast, soil moisture/temperature, UV, sunrise/sunset.
- **Farm advisory:** spray window, irrigate/skip irrigation, heat & frost alerts, fungal-disease risk,
  heavy-rain/wind warnings, best field-work days, 7-day rain, crop water loss (ET0) and growing degree days.
- The dashboard shows a mini weather card for your last location.
- Needs internet. Data: Open-Meteo.com. Browsers only allow GPS on `localhost` or HTTPS.

## 📷 Disease Prediction from a Leaf Photo
Code: `ml/predictor.py` (pipeline), `ml/knowledge.py` (disease info), `download_models.py`.

Pipeline: **leaf check -> pre-trained model zoo -> advice**
1. *Colour check* - rejects images with no plant colours (e.g. a red/white logo).
2. *CLIP check* (OpenAI CLIP, pre-trained) - rejects logos, screenshots, people, objects.
3. *Classifiers* (all small enough for a normal laptop CPU):
   | Model | Covers |
   |---|---|
   | `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification` (MobileNetV2, 38 classes) | Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato |
   | `wambugu71/crop_leaf_diseases_vit` (ViT-tiny, 5.5 M params, ~98% reported) | **Rice** (brown spot, leaf blast, healthy), **Wheat** (brown rust, yellow rust, healthy), Corn, Potato |
   | anything in `AGRI_EXTRA_MODELS` | whatever its labels name (e.g. a cotton model) |

   If you pick the crop, only models that know that crop are used. With no crop selected, the most
   confident model wins. When two models agree the result shows "2 models agree". Low confidence shows
   "not sure, retake photo" instead of guessing.
4. Causes / treatment / prevention come from `ml/knowledge.py` + `ml/knowledge_more.py`, overridden by matching records in your `diseases` table.
5. Every successful scan is saved in **Scan History**.

**No single pretrained model covers "all plants".** Cotton, sugarcane, groundnut, mustard, chickpea etc. have
no verified plug-in model bundled. To add one, find an image-classification model on huggingface.co whose
labels name the crop (for example "Cotton_Bacterial blight"), then:
```bash
set AGRI_EXTRA_MODELS=owner/model-name      # Windows   (export ... on Mac/Linux)
python download_models.py
python app.py
```
The crop list and disease matching update automatically. For crops with no model, use the symptom checker or
train your own with `train_model.py` (datasets with rice, wheat, cotton and sugarcane classes exist on Hugging Face).

First-time setup (needs internet once):
```bash
pip install -r requirements.txt
python download_models.py      # two small classifiers (~10 MB + ~25 MB) + ~600 MB CLIP checker
python app.py
```
Low on disk/RAM? `set AGRI_USE_CLIP=0` (Windows) / `export AGRI_USE_CLIP=0` skips CLIP and uses the
colour check only (weaker at rejecting non-leaf photos). If the AI libraries are missing, the page
falls back to the old rough colour scan and says so.

Accuracy note: PlantVillage photos are single leaves on plain backgrounds. Real field photos
are harder - use a close, well-lit shot of one leaf, and confirm serious outbreaks with a
local agriculture officer / KVK.
"# agriguide" 
