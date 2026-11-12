"""
Disease knowledge base + label parsing.

The pretrained model outputs PlantVillage-style labels such as
"Tomato___Early_blight" or "Corn_(maize)___Common_rust_". Spelling differs
between dataset copies, so we match on keywords instead of exact strings.
"""
import re

# Crop names we can recognise inside model labels (matched as whole words).
CROP_KEYWORDS = [
    ("corn", "Corn"), ("maize", "Corn"), ("pepper", "Pepper"), ("chilli", "Pepper"), ("cherry", "Cherry"),
    ("tomato", "Tomato"), ("potato", "Potato"), ("apple", "Apple"), ("grape", "Grape"),
    ("peach", "Peach"), ("strawberry", "Strawberry"), ("orange", "Orange"), ("citrus", "Orange"),
    ("blueberry", "Blueberry"), ("raspberry", "Raspberry"), ("soybean", "Soybean"), ("squash", "Squash"),
    ("rice", "Rice"), ("paddy", "Rice"), ("wheat", "Wheat"), ("cotton", "Cotton"), ("sugarcane", "Sugarcane"),
    ("jute", "Jute"), ("cassava", "Cassava"), ("banana", "Banana"), ("mango", "Mango"),
    ("groundnut", "Groundnut"), ("peanut", "Groundnut"), ("cabbage", "Cabbage"), ("cauliflower", "Cauliflower"),
    ("coffee", "Coffee"), ("mustard", "Mustard"), ("chickpea", "Chickpea"), ("sunflower", "Sunflower"),
    ("brinjal", "Brinjal"), ("eggplant", "Brinjal"), ("okra", "Okra"), ("onion", "Onion"),
]


def find_crop(text):
    """Canonical crop name found in text (whole-word match), or None."""
    low = _clean(text)
    for kw, name in CROP_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return name
    return None


# Crops covered by the built-in pretrained models (PlantVillage MobileNetV2 + crop-leaf ViT).
# Extra models added with AGRI_EXTRA_MODELS extend this automatically at run time.
SUPPORTED_CROPS = sorted({"Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange", "Peach", "Pepper",
                          "Potato", "Raspberry", "Soybean", "Squash", "Strawberry", "Tomato", "Rice", "Wheat"})

# keyword(s) in the label -> info.  First match wins, so order specific before general.
DISEASES = [
    (("early blight",), {
        "name": "Early Blight", "type": "Fungal disease (Alternaria)",
        "symptoms": ["Brown spots with concentric rings (bullseye look) on older leaves", "Yellowing around spots", "Leaves dry and drop"],
        "causes": ["Warm, humid weather", "Infected crop debris in soil", "Overhead watering / water splash"],
        "treatment": ["Remove and destroy affected leaves", "Spray copper-based fungicide or mancozeb as per label", "Avoid wetting foliage when irrigating"],
        "prevention": ["Rotate crops (2-3 years)", "Use disease-free seed/seedlings", "Mulch to stop soil splash", "Keep plants well spaced"]}),
    (("late blight",), {
        "name": "Late Blight", "type": "Oomycete (Phytophthora infestans)",
        "symptoms": ["Large dark, water-soaked patches on leaves", "White fuzzy growth under leaves in humid weather", "Fruit/tuber rot"],
        "causes": ["Cool, wet, humid weather", "Infected seed tubers or volunteers", "Wind-blown spores"],
        "treatment": ["Remove infected plants immediately and bury or burn them", "Spray a protective fungicide (copper / mancozeb / metalaxyl mix) per label", "Stop overhead irrigation"],
        "prevention": ["Plant resistant varieties", "Use certified seed", "Ensure good drainage and airflow", "Scout fields after cool, rainy spells"]}),
    (("bacterial spot",), {
        "name": "Bacterial Spot", "type": "Bacterial disease (Xanthomonas)",
        "symptoms": ["Small dark, greasy-looking spots on leaves and fruit", "Spots may have yellow halo", "Leaves look ragged as spots drop out"],
        "causes": ["Infected seed", "Splashing rain and irrigation", "Warm, wet weather"],
        "treatment": ["Copper-based bactericide sprays (limited effect, start early)", "Remove badly infected plants", "Do not work in wet fields"],
        "prevention": ["Use clean seed", "Rotate with non-host crops", "Disinfect tools", "Drip irrigation instead of sprinklers"]}),
    (("leaf mold",), {
        "name": "Leaf Mold", "type": "Fungal disease (Passalora fulva)",
        "symptoms": ["Pale yellow patches on upper leaf surface", "Olive-green velvety mold underneath", "Leaves curl and wither"],
        "causes": ["Very high humidity (>85%)", "Poor ventilation, esp. in greenhouses"],
        "treatment": ["Improve ventilation and reduce humidity", "Remove infected leaves", "Apply a suitable fungicide per label"],
        "prevention": ["Space and prune plants for airflow", "Water at the base in the morning", "Use resistant varieties"]}),
    (("septoria",), {
        "name": "Septoria Leaf Spot", "type": "Fungal disease (Septoria lycopersici)",
        "symptoms": ["Many small circular spots with grey centres and dark edges", "Starts on lower leaves", "Heavy leaf drop"],
        "causes": ["High humidity", "Water splashing from soil", "Overcrowded planting"],
        "treatment": ["Remove lower infected leaves", "Spray chlorothalonil / copper / mancozeb per label"],
        "prevention": ["Rotate crops yearly", "Avoid overhead watering", "Mulch the soil", "Clean up plant debris after harvest"]}),
    (("spider mite",), {
        "name": "Spider Mites (Two-spotted)", "type": "Pest (mite)",
        "symptoms": ["Fine yellow stippling on leaves", "Fine webbing under leaves", "Leaves turn bronze and dry up"],
        "causes": ["Hot, dry, dusty weather", "Overuse of broad-spectrum insecticides that kill natural enemies"],
        "treatment": ["Spray neem oil or insecticidal soap, covering leaf undersides", "Use a miticide only if severe, as per label", "Wash plants with a strong water jet"],
        "prevention": ["Keep plants well watered", "Avoid dusty conditions", "Encourage predatory mites/ladybirds"]}),
    (("target spot",), {
        "name": "Target Spot", "type": "Fungal disease (Corynespora cassiicola)",
        "symptoms": ["Brown spots with concentric rings and yellow halo", "Spots merge, leaves die", "Fruit spotting"],
        "causes": ["Warm, humid weather", "Dense canopy", "Infected crop residue"],
        "treatment": ["Remove infected leaves", "Spray a recommended fungicide per label"],
        "prevention": ["Prune for airflow", "Rotate crops", "Avoid overhead irrigation"]}),
    (("yellow leaf curl", "yellow_leaf_curl", "curl virus"), {
        "name": "Tomato Yellow Leaf Curl Virus", "type": "Viral disease (spread by whiteflies)",
        "symptoms": ["Leaves curl upward and turn yellow", "Plants stunted", "Flowers drop, little fruit"],
        "causes": ["Whitefly feeding on infected plants", "Infected seedlings"],
        "treatment": ["No cure - uproot and destroy infected plants", "Control whiteflies with yellow sticky traps, neem oil, or recommended insecticide"],
        "prevention": ["Use virus-resistant varieties", "Grow seedlings under insect-proof net", "Remove weeds that host whiteflies"]}),
    (("mosaic virus", "mosaic"), {
        "name": "Mosaic Virus", "type": "Viral disease",
        "symptoms": ["Mottled light/dark green pattern on leaves", "Distorted, stunted leaves", "Poor fruit"],
        "causes": ["Spread by contaminated hands/tools, aphids or infected seed"],
        "treatment": ["No cure - remove and destroy infected plants", "Wash hands and disinfect tools"],
        "prevention": ["Use certified virus-free seed", "Control aphids", "Do not handle plants after tobacco"]}),
    (("powdery mildew",), {
        "name": "Powdery Mildew", "type": "Fungal disease",
        "symptoms": ["White powdery coating on leaves", "Leaves curl, yellow and dry", "Reduced growth/yield"],
        "causes": ["Warm days with cool nights", "Dense foliage", "Moderate humidity (it does not need wet leaves)"],
        "treatment": ["Spray sulphur-based fungicide or a recommended systemic fungicide", "Remove heavily infected leaves", "Neem oil or potassium bicarbonate spray for mild cases"],
        "prevention": ["Plant resistant varieties", "Give plants space and sun", "Avoid excess nitrogen"]}),
    (("common rust",), {
        "name": "Common Rust", "type": "Fungal disease (Puccinia sorghi)",
        "symptoms": ["Small reddish-brown pustules on both leaf surfaces", "Pustules turn dark as the crop matures"],
        "causes": ["Cool, humid weather", "Wind-blown spores"],
        "treatment": ["Fungicide (e.g. propiconazole/azoxystrobin) if infection is early and severe, per label"],
        "prevention": ["Plant resistant hybrids", "Sow early", "Monitor fields from knee-high stage"]}),
    (("northern leaf blight",), {
        "name": "Northern Leaf Blight", "type": "Fungal disease (Exserohilum turcicum)",
        "symptoms": ["Long grey-green cigar-shaped lesions (3-15 cm)", "Lesions turn tan and merge", "Leaves die early"],
        "causes": ["Moderate temperature with long wet/dew periods", "Corn residue in field"],
        "treatment": ["Foliar fungicide at early tasseling if disease is spreading, per label"],
        "prevention": ["Resistant hybrids", "Crop rotation", "Deep ploughing of residue"]}),
    (("gray leaf spot", "grey leaf spot", "cercospora"), {
        "name": "Gray Leaf Spot", "type": "Fungal disease (Cercospora)",
        "symptoms": ["Rectangular grey-tan lesions running between leaf veins", "Leaves die from the bottom up"],
        "causes": ["Warm, humid weather", "Maize residue", "Continuous maize cropping"],
        "treatment": ["Foliar fungicide if disease reaches upper leaves before grain fill"],
        "prevention": ["Rotate crops", "Plant tolerant hybrids", "Bury crop residue"]}),
    (("black rot",), {
        "name": "Black Rot", "type": "Fungal disease",
        "symptoms": ["Tan to brown leaf spots with dark border", "Shrivelled black 'mummified' fruit", "Cankers on shoots (apple)"],
        "causes": ["Warm, wet weather", "Infected fruit/wood left on plant"],
        "treatment": ["Prune and destroy infected shoots and mummified fruit", "Protective fungicide sprays from early season, per label"],
        "prevention": ["Remove dead wood and mummies in winter", "Keep canopy open", "Plant resistant varieties"]}),
    (("esca", "black measles"), {
        "name": "Esca (Black Measles)", "type": "Fungal disease complex of wood",
        "symptoms": ["Yellow/red 'tiger-stripe' patterns between veins", "Dark spots on berries", "Sudden vine collapse in summer"],
        "causes": ["Wood-rotting fungi entering through pruning wounds"],
        "treatment": ["No effective cure - prune out infected wood in dry weather", "Seal large pruning wounds"],
        "prevention": ["Prune in dry weather", "Disinfect pruning tools", "Remove dead vines"]}),
    (("isariopsis", "leaf blight (isariopsis"), {
        "name": "Grape Leaf Blight", "type": "Fungal disease (Isariopsis)",
        "symptoms": ["Irregular dark brown patches on leaves", "Premature leaf fall"],
        "causes": ["Humid weather", "Dense canopy"],
        "treatment": ["Spray copper fungicide / Bordeaux mixture per label", "Remove affected leaves"],
        "prevention": ["Good canopy management", "Avoid overhead irrigation"]}),
    (("citrus greening", "haunglongbing", "huanglongbing"), {
        "name": "Citrus Greening (Huanglongbing)", "type": "Bacterial disease (spread by psyllids)",
        "symptoms": ["Yellow blotchy mottling of leaves", "Small, lopsided, bitter fruit that stays green at the base", "Branch dieback"],
        "causes": ["Asian citrus psyllid insect spreads the bacterium", "Infected nursery plants"],
        "treatment": ["No cure - remove infected trees", "Control psyllids with recommended insecticides"],
        "prevention": ["Buy certified disease-free plants", "Scout for psyllids", "Report suspected cases to the horticulture department"]}),
    (("cedar apple rust",), {
        "name": "Cedar Apple Rust", "type": "Fungal disease",
        "symptoms": ["Bright yellow-orange spots on leaves", "Tiny tube-like growths under leaves"],
        "causes": ["Needs nearby juniper/cedar trees to complete its life cycle", "Wet spring weather"],
        "treatment": ["Fungicide at pink-bud to petal-fall stage, per label"],
        "prevention": ["Remove nearby junipers", "Plant resistant apple varieties"]}),
    (("apple scab", "scab"), {
        "name": "Apple Scab", "type": "Fungal disease (Venturia)",
        "symptoms": ["Olive-green to black velvety spots on leaves and fruit", "Scabby, cracked fruit", "Leaves yellow and drop"],
        "causes": ["Cool, wet spring weather", "Fallen infected leaves"],
        "treatment": ["Protective fungicide sprays in spring, per label", "Rake and destroy fallen leaves"],
        "prevention": ["Plant scab-resistant varieties", "Prune for airflow"]}),
    (("leaf scorch",), {
        "name": "Leaf Scorch", "type": "Fungal disease",
        "symptoms": ["Purple-brown blotches that merge", "Leaf edges dry and curl as if burnt"],
        "causes": ["Wet, humid weather", "Infected old leaves"],
        "treatment": ["Remove infected leaves", "Apply recommended fungicide per label"],
        "prevention": ["Use resistant varieties", "Water at the base", "Space plants well"]}),
]

from .knowledge_more import MORE_DISEASES  # noqa: E402
DISEASES += MORE_DISEASES

GENERIC = {
    "name": "Unrecognised problem", "type": "Unknown",
    "symptoms": [], "causes": ["Not in the knowledge base yet"],
    "treatment": ["Contact your local agriculture officer or KVK with a sample"],
    "prevention": ["Keep fields clean and well drained", "Scout your crop regularly"],
}

HEALTHY_INFO = {
    "name": "Healthy", "type": "No disease detected",
    "symptoms": [], "causes": [], "treatment": [],
    "prevention": ["Keep scouting every few days", "Maintain balanced fertiliser and irrigation", "Keep field free of weeds and crop debris"],
}


def _clean(label):
    return re.sub(r"[^a-z0-9 ()]", " ", label.lower().replace("_", " ")).strip()


def parse_label(label):
    """'Corn_(maize)___Common_rust_' -> dict(crop, disease, healthy, info, display)"""
    low = _clean(label)
    crop = find_crop(label)
    healthy = "healthy" in low
    disease_part = label.split("___", 1)[1] if "___" in label else label
    disease_part = re.sub(r"\s+", " ", disease_part.replace("_", " ")).strip()
    info = HEALTHY_INFO if healthy else None
    if not healthy:
        for keys, data in DISEASES:
            if any(k in low for k in keys):
                info = data
                break
        info = info or {**GENERIC, "name": disease_part or GENERIC["name"]}
    display_disease = "Healthy" if healthy else info["name"]
    display = f"{crop or 'Plant'} - {display_disease}"
    return {"crop": crop, "disease": display_disease, "healthy": healthy, "info": info,
            "display": display, "raw": label}
