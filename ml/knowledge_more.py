"""Extra disease/pest entries for rice, wheat, maize, sugarcane, cotton and general crops."""

MORE_DISEASES = [
    (("brown spot",), {
        "name": "Brown Spot", "type": "Fungal disease (Bipolaris / Cochliobolus)",
        "symptoms": ["Oval brown spots with grey centres on leaves", "Spots on grains reduce quality", "Seedlings may die"],
        "causes": ["Nutrient-poor or potassium-deficient soil", "Water stress", "Infected seed"],
        "treatment": ["Spray recommended fungicide (e.g. mancozeb / propiconazole) per label", "Correct nutrient deficiency, especially potash"],
        "prevention": ["Use certified, treated seed", "Balanced fertilisation", "Avoid drought stress", "Clean field bunds"]}),
    (("leaf blast", "rice blast", "neck blast", "blast"), {
        "name": "Leaf Blast", "type": "Fungal disease (Magnaporthe oryzae)",
        "symptoms": ["Diamond/spindle-shaped spots with grey centre and brown edge", "Spots merge and leaves dry", "Neck blast makes panicles break and gives empty grains"],
        "causes": ["High humidity and cool nights", "Excess nitrogen", "Dense planting", "Infected seed or stubble"],
        "treatment": ["Spray tricyclazole or another recommended fungicide per label", "Stop extra nitrogen top-dressing until it is controlled"],
        "prevention": ["Grow resistant varieties", "Treat seed", "Split nitrogen doses", "Avoid very late planting"]}),
    (("hispa",), {
        "name": "Rice Hispa", "type": "Pest (beetle)",
        "symptoms": ["White parallel streaks where the leaf surface is scraped", "Leaf tips dry and curl"],
        "causes": ["Adult beetles and grubs feeding on leaves", "Dense nitrogen-rich crop"],
        "treatment": ["Clip leaf tips of seedlings before transplanting", "Spray a recommended insecticide per label if damage is heavy"],
        "prevention": ["Remove grassy weeds", "Avoid excess nitrogen", "Hand-collect beetles / light traps"]}),
    (("tungro",), {
        "name": "Rice Tungro", "type": "Viral disease (spread by green leafhoppers)",
        "symptoms": ["Orange-yellow leaves", "Stunted plants with few tillers"],
        "causes": ["Green leafhoppers carry the virus from infected plants"],
        "treatment": ["Uproot and destroy infected plants", "Control leafhoppers with a recommended insecticide"],
        "prevention": ["Plant tolerant varieties", "Synchronise planting in the area", "Remove volunteer rice and weeds"]}),
    (("bacterial blight", "bacterial leaf blight"), {
        "name": "Bacterial Blight", "type": "Bacterial disease (Xanthomonas)",
        "symptoms": ["Water-soaked angular spots/streaks turning yellow to brown", "Leaves wilt and dry from the tips"],
        "causes": ["Infected seed and crop residue", "Rain and wind spread", "Excess nitrogen"],
        "treatment": ["Avoid extra nitrogen", "Drain standing water where possible", "Copper-based sprays may slow spread (follow local advice)"],
        "prevention": ["Use resistant varieties and healthy seed", "Burn or bury infected residue", "Disinfect tools"]}),
    (("brown rust", "leaf rust"), {
        "name": "Brown (Leaf) Rust", "type": "Fungal disease (Puccinia triticina)",
        "symptoms": ["Small round orange-brown pustules scattered on leaves", "Leaves yellow and dry early"],
        "causes": ["Mild temperatures with dew or rain", "Wind-borne spores", "Susceptible varieties"],
        "treatment": ["Spray propiconazole or tebuconazole per label at first signs"],
        "prevention": ["Grow resistant varieties", "Sow on time", "Destroy volunteer wheat"]}),
    (("yellow rust", "stripe rust"), {
        "name": "Yellow (Stripe) Rust", "type": "Fungal disease (Puccinia striiformis)",
        "symptoms": ["Yellow powdery stripes along the leaf veins", "Leaves dry up, grain shrivels"],
        "causes": ["Cool (10-15 C), humid weather", "Wind-borne spores", "Susceptible varieties"],
        "treatment": ["Spray propiconazole or tebuconazole at the first stripes, per label"],
        "prevention": ["Resistant varieties", "Timely sowing", "Avoid excess nitrogen", "Scout from tillering stage"]}),
    (("red rot", "redrot"), {
        "name": "Red Rot", "type": "Fungal disease (Colletotrichum falcatum)",
        "symptoms": ["Red stalk interior with white cross-bands", "Drying of top leaves", "Sour smell from cut cane"],
        "causes": ["Infected seed cane", "Waterlogging", "Ratooning a diseased crop"],
        "treatment": ["Uproot and destroy infected clumps", "Do not use affected canes as seed"],
        "prevention": ["Resistant varieties", "Healthy, treated setts", "Crop rotation with paddy"]}),
    (("aphid",), {
        "name": "Aphid Infestation", "type": "Pest (sap-sucking insect)",
        "symptoms": ["Clusters of small insects under leaves", "Curled, sticky leaves with sooty mould"],
        "causes": ["Warm weather and soft nitrogen-rich growth", "Few natural enemies"],
        "treatment": ["Spray neem oil or soap solution", "Use a recommended systemic insecticide only if heavy, per label"],
        "prevention": ["Encourage ladybirds", "Avoid excess nitrogen", "Yellow sticky traps"]}),
    (("anthracnose",), {
        "name": "Anthracnose", "type": "Fungal disease (Colletotrichum)",
        "symptoms": ["Dark sunken spots on leaves, stems or fruit", "Pink spore masses in humid weather"],
        "causes": ["Warm wet weather", "Infected seed or residue"],
        "treatment": ["Remove infected parts", "Spray carbendazim or a copper fungicide per label"],
        "prevention": ["Use clean seed", "Crop rotation", "Avoid overhead irrigation"]}),
    (("downy mildew",), {
        "name": "Downy Mildew", "type": "Oomycete disease",
        "symptoms": ["Yellow patches on top of the leaf", "Greyish fuzzy growth underneath", "Stunted plants"],
        "causes": ["Cool, wet weather", "Infected seed or residue"],
        "treatment": ["Spray metalaxyl + mancozeb or a copper fungicide per label"],
        "prevention": ["Resistant varieties", "Good drainage", "Wider spacing"]}),
    (("leaf blight", "blight"), {
        "name": "Leaf Blight", "type": "Fungal disease",
        "symptoms": ["Large tan to brown lesions on leaves", "Leaves dry out from the tips", "Lower yield"],
        "causes": ["Warm humid weather", "Infected crop residue", "Susceptible varieties"],
        "treatment": ["Spray a recommended fungicide (e.g. mancozeb) per label", "Remove badly infected leaves"],
        "prevention": ["Resistant hybrids/varieties", "Crop rotation", "Plough in residue after harvest"]}),
    (("rust",), {
        "name": "Rust", "type": "Fungal disease",
        "symptoms": ["Orange, brown or reddish pustules on leaves"],
        "causes": ["Humid weather", "Wind-borne spores"],
        "treatment": ["Spray a recommended fungicide per label at an early stage"],
        "prevention": ["Resistant varieties", "Timely sowing"]}),
]
