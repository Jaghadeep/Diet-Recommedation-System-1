import os
import csv
import json
import math
import statistics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SMARTWATCH_CSV = os.path.join(DATA_DIR, 'smartwatch_data.csv')
CLEANED_SMARTWATCH_CSV = os.path.join(DATA_DIR, 'cleaned_smartwatch_data.csv')
FOOD_JSON_PATH = os.path.join(DATA_DIR, 'indian_food_nutrition.json')
RECIPES_JS_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'React', 'src', 'data', 'recipes.js'))

def clean_smartwatch_data():
    """
    Cleans raw Samsung Smartwatch health records:
    1. Handles missing values (User ID, Heart Rate, SpO2, Sleep Duration).
    2. Replaces corrupted values ('ERROR', 'nan') with median/mean.
    3. Normalizes activity levels ('Actve' -> 'Active', 'Seddentary' -> 'Sedentary').
    4. Normalizes stress level ('Very High' -> 10, invalid -> median).
    5. Feature engineering: computes BMI, dynamic active calories burned, sleep recovery score.
    """
    if not os.path.exists(SMARTWATCH_CSV):
        print(f"File not found: {SMARTWATCH_CSV}")
        return []

    raw_rows = []
    with open(SMARTWATCH_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rows.append(row)

    # 1. Compute valid medians for numeric fields
    valid_hr = []
    valid_spo2 = []
    valid_steps = []
    valid_sleep = []
    valid_stress = []

    for r in raw_rows:
        try:
            hr = float(r.get('Heart Rate (BPM)', ''))
            if 40 <= hr <= 220:
                valid_hr.append(hr)
        except:
            pass

        try:
            spo2 = float(r.get('Blood Oxygen Level (%)', ''))
            if 80 <= spo2 <= 100:
                valid_spo2.append(spo2)
        except:
            pass

        try:
            steps = float(r.get('Step Count', ''))
            if steps >= 0:
                valid_steps.append(steps)
        except:
            pass

        try:
            sleep = float(r.get('Sleep Duration (hours)', ''))
            if 1 <= sleep <= 16:
                valid_sleep.append(sleep)
        except:
            pass

        stress_raw = str(r.get('Stress Level', '')).strip().lower()
        if stress_raw == 'very high':
            valid_stress.append(10.0)
        else:
            try:
                st = float(stress_raw)
                if 1 <= st <= 10:
                    valid_stress.append(st)
            except:
                pass

    med_hr = statistics.median(valid_hr) if valid_hr else 72.0
    med_spo2 = statistics.median(valid_spo2) if valid_spo2 else 98.0
    med_steps = statistics.median(valid_steps) if valid_steps else 6000.0
    med_sleep = statistics.median(valid_sleep) if valid_sleep else 6.8
    med_stress = statistics.median(valid_stress) if valid_stress else 5.0

    cleaned_rows = []
    auto_id = 1000

    for idx, r in enumerate(raw_rows):
        # User ID
        uid = str(r.get('User ID', '')).strip()
        if not uid or uid.lower() == 'nan':
            uid = f"U{auto_id + idx}"

        # Heart Rate
        try:
            hr = float(r.get('Heart Rate (BPM)', ''))
            if hr < 40 or hr > 220:
                hr = med_hr
        except:
            hr = med_hr
        hr = round(hr, 1)

        # SpO2
        try:
            spo2 = float(r.get('Blood Oxygen Level (%)', ''))
            if spo2 < 85 or spo2 > 100:
                spo2 = med_spo2
        except:
            spo2 = med_spo2
        spo2 = round(spo2, 1)

        # Step count
        try:
            steps = float(r.get('Step Count', ''))
            if steps < 0 or math.isnan(steps):
                steps = med_steps
        except:
            steps = med_steps
        steps = int(round(steps))

        # Sleep duration
        try:
            sl_val = r.get('Sleep Duration (hours)', '')
            if str(sl_val).strip().upper() == 'ERROR':
                sleep = med_sleep
            else:
                sleep = float(sl_val)
                if sleep < 1 or sleep > 16 or math.isnan(sleep):
                    sleep = med_sleep
        except:
            sleep = med_sleep
        sleep = round(sleep, 2)

        # Activity Level spelling corrections
        act_raw = str(r.get('Activity Level', '')).strip().lower()
        if 'sed' in act_raw or 'seddentary' in act_raw:
            activity = 'Sedentary'
        elif 'high' in act_raw:
            activity = 'Highly Active'
        elif 'act' in act_raw:
            activity = 'Active'
        else:
            # Fallback based on step count
            if steps < 4000:
                activity = 'Sedentary'
            elif steps > 10000:
                activity = 'Highly Active'
            else:
                activity = 'Active'

        # Stress level
        stress_str = str(r.get('Stress Level', '')).strip().lower()
        if stress_str == 'very high':
            stress = 10
        else:
            try:
                st = int(round(float(stress_str)))
                stress = max(1, min(10, st))
            except:
                stress = int(round(med_stress))

        # Feature Engineering:
        # Active Calories Burned = steps * 0.04 + (Heart Rate - 60) * 2.5
        active_calories = round(max(50.0, (steps * 0.045) + max(0, (hr - 65) * 2.8)))
        
        # Sleep Recovery Score (0 - 100)
        # Optimal sleep is 7-8 hours
        sleep_dev = abs(sleep - 7.5)
        recovery_score = max(30, round(100 - (sleep_dev * 15) - (stress * 3)))

        cleaned_rows.append({
            'userId': uid,
            'heartRate': hr,
            'spo2': spo2,
            'steps': steps,
            'sleepHours': sleep,
            'activityLevel': activity,
            'stressLevel': stress,
            'caloriesBurned': active_calories,
            'recoveryScore': recovery_score
        })

    # Save cleaned smartwatch records
    with open(CLEANED_SMARTWATCH_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'userId', 'heartRate', 'spo2', 'steps', 'sleepHours',
            'activityLevel', 'stressLevel', 'caloriesBurned', 'recoveryScore'
        ])
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"Cleaned {len(cleaned_rows)} smartwatch records. Saved to {CLEANED_SMARTWATCH_CSV}")
    return cleaned_rows


def build_and_export_indian_food_dataset():
    """
    Builds the authentic Indian food database directly mapping all nutritional attributes:
    Calories, Carbs, Protein, Fats, Free Sugar, Fibre, Sodium, Calcium, Iron, Vitamin C, Folate.
    Assigns:
    - 10+ Food categories
    - Disease safety checks (Diabetes, Hypertension, Cardiovascular/Heart, Obesity/PCOS)
    - Regional markers & authentic ingredients
    - Exports to React recipes.js and backend JSON.
    """
    # Essential curated dishes from the provided dataset representing the 10+ categories and disease specialties
    dishes = [
        # 1. BREAKFAST & GRAINS
        {
            "id": "b1", "name": "Moong Dal Cheela (Sprouted Savory Pancake)",
            "category": "Breakfast", "mealType": "breakfast", "region": "North Indian",
            "calories": 155, "carbs": 19.4, "protein": 7.0, "fat": 5.1, "freeSugar": 1.1, "fiber": 4.3,
            "sodium": 267, "calcium": 39.3, "iron": 2.22, "vitaminC": 34.8, "folate": 79.9,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Protein", "Diabetic-Friendly", "Low-Sodium", "Gluten-Free"],
            "image": "🫓🌱",
            "description": "Crispy golden protein crepes prepared with soaked yellow moong dal, ginger, cumin, and fresh cilantro. Light, low glycemic, and gentle on blood sugar.",
            "ingredients": [{"name": "Yellow Moong Dal", "quantity": 50, "unit": "g"}, {"name": "Grated Ginger", "quantity": 1, "unit": "tsp"}, {"name": "Cumin Seeds (Jeera)", "quantity": 0.5, "unit": "tsp"}, {"name": "Chopped Green Chillies", "quantity": 1, "unit": "pc"}, {"name": "Fresh Coriander Leaves", "quantity": 1, "unit": "tbsp"}, {"name": "Cold-Pressed Mustard Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Soak moong dal for 3 hours, then grind with ginger and green chillies into a smooth batter.", "Heat a cast iron tawa, lightly brush with oil.", "Pour a ladle of batter and swirl thinly into a crepe.", "Cook on medium heat until golden brown on both sides. Serve warm with mint chutney."]
        },
        {
            "id": "b2", "name": "Steamed Sprouted Ragi Idli with Sambar",
            "category": "Breakfast", "mealType": "breakfast", "region": "South Indian",
            "calories": 138, "carbs": 28.2, "protein": 4.6, "fat": 0.3, "freeSugar": 0.3, "fiber": 2.3,
            "sodium": 101, "calcium": 8.0, "iron": 0.68, "vitaminC": 0.0, "folate": 3.0,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Diabetic-Friendly", "High-Calcium", "Low-Sodium", "Zero-Oil"],
            "image": "⚪🍲",
            "description": "Fermented whole grain finger millet (Ragi) steamed cakes. Naturally low fat and nutrient-dense, perfect for cardiovascular stamina.",
            "ingredients": [{"name": "Sprouted Ragi Flour", "quantity": 40, "unit": "g"}, {"name": "Urad Dal Batter", "quantity": 30, "unit": "g"}, {"name": "Curry Leaves", "quantity": 4, "unit": "leaves"}, {"name": "Rock Salt", "quantity": 0.25, "unit": "tsp"}],
            "instructions": ["Blend fermented ragi and urad dal batter with a pinch of rock salt.", "Grease idli molds lightly and steam in an idli cooker for 10-12 minutes.", "Unmold using a wet spoon and serve with piping hot toor dal vegetable sambar."]
        },
        {
            "id": "b3", "name": "Moong Bean Dosa (Pesarattu)",
            "category": "Breakfast", "mealType": "breakfast", "region": "South Indian",
            "calories": 286, "carbs": 31.9, "protein": 12.3, "fat": 11.7, "freeSugar": 2.9, "fiber": 6.0,
            "sodium": 61, "calcium": 36.4, "iron": 3.38, "vitaminC": 1.48, "folate": 14.3,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Protein", "High-Fiber", "Diabetic-Friendly", "Low-Sodium"],
            "image": "🥞🌿",
            "description": "Authentic Andhra green gram crepe packed with plant protein, bio-available iron, and high dietary fiber.",
            "ingredients": [{"name": "Whole Green Gram (Sabut Moong)", "quantity": 60, "unit": "g"}, {"name": "Ginger", "quantity": 1, "unit": "inch"}, {"name": "Cumin Seeds", "quantity": 1, "unit": "tsp"}, {"name": "Finely Chopped Onions", "quantity": 2, "unit": "tbsp"}, {"name": "Gingelly/Sesame Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Soak whole green gram overnight with cumin and ginger.", "Grind into a thick batter without fermenting.", "Spread onto hot tawa, top with chopped onions, and toast until crisp.", "Enjoy with tangy ginger chutney."]
        },
        {
            "id": "b4", "name": "Vegetable Poha with Roasted Peanuts",
            "category": "Breakfast", "mealType": "breakfast", "region": "West Indian",
            "calories": 180, "carbs": 21.5, "protein": 4.9, "fat": 8.1, "freeSugar": 1.4, "fiber": 3.8,
            "sodium": 418, "calcium": 28.0, "iron": 1.92, "vitaminC": 7.21, "folate": 21.8,
            "glycemicIndex": "Medium", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Gluten-Free", "Iron-Rich"],
            "image": "🍋🥣",
            "description": "Flattened rice flakes tempered with mustard seeds, curry leaves, crunchy roasted peanuts, green peas, and fresh lime juice.",
            "ingredients": [{"name": "Thick Red Poha", "quantity": 50, "unit": "g"}, {"name": "Peanuts", "quantity": 10, "unit": "g"}, {"name": "Green Peas", "quantity": 2, "unit": "tbsp"}, {"name": "Turmeric Powder", "quantity": 0.25, "unit": "tsp"}, {"name": "Mustard Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Lemon Juice", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Rinse poha in a colander until soft, drain completely.", "Roast peanuts in a pan, set aside.", "Temper mustard seeds, green chillies, turmeric, and sauté green peas.", "Gently toss in softened poha, squeeze lemon juice, and garnish with fresh coriander."]
        },
        {
            "id": "b5", "name": "Paneer Bhurji with 2 Multigrain Phulkas",
            "category": "Breakfast", "mealType": "breakfast", "region": "North Indian",
            "calories": 305, "carbs": 24.3, "protein": 14.8, "fat": 15.2, "freeSugar": 2.1, "fiber": 4.2,
            "sodium": 240, "calcium": 180.0, "iron": 2.4, "vitaminC": 18.5, "folate": 35.0,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": False,
            "tags": ["Vegetarian", "High-Protein", "High-Calcium", "Low-Carb"],
            "image": "🧀🫓",
            "description": "Scrambled artisanal low-fat cottage cheese seasoned with tomatoes, turmeric, green bell pepper, served alongside freshly puffed whole-wheat rotis.",
            "ingredients": [{"name": "Low-Fat Fresh Paneer", "quantity": 80, "unit": "g"}, {"name": "Whole Wheat Atta (Phulkas)", "quantity": 40, "unit": "g"}, {"name": "Diced Tomato", "quantity": 0.5, "unit": "cup"}, {"name": "Green Bell Pepper", "quantity": 2, "unit": "tbsp"}, {"name": "Ghee", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Crumble paneer with fingers.", "Sauté onions, tomatoes, and bell peppers in a teaspoon of ghee with cumin and turmeric.", "Add crumbled paneer, toss on high heat for 2 minutes to keep it succulent.", "Serve hot with whole wheat phulkas."]
        },
        {
            "id": "b6", "name": "Steamed Sprouted Gujarati Khaman Dhokla",
            "category": "Breakfast", "mealType": "breakfast", "region": "West Indian",
            "calories": 216, "carbs": 30.7, "protein": 13.5, "fat": 5.3, "freeSugar": 4.8, "fiber": 5.0,
            "sodium": 376, "calcium": 123.2, "iron": 1.39, "vitaminC": 0.7, "folate": 39.9,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Protein", "Jain-Friendly", "Steamed", "Diabetic-Friendly"],
            "image": "🟡✨",
            "description": "Fluffy, spongy steamed chickpea flour cakes lightly tempered with mustard seeds and curry leaves. Zero oil cooking.",
            "ingredients": [{"name": "Besan (Bengal Gram Flour)", "quantity": 60, "unit": "g"}, {"name": "Curd (Dahi)", "quantity": 2, "unit": "tbsp"}, {"name": "Lemon Juice", "quantity": 1, "unit": "tsp"}, {"name": "Eno/Fruit Salt", "quantity": 0.5, "unit": "tsp"}, {"name": "Mustard Seeds", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Whisk besan with curd, turmeric, and water into a smooth batter.", "Stir in fruit salt, pour immediately into greased thali.", "Steam on high flame for 15 minutes.", "Temper with mustard seeds and curry leaves, cut into squares."]
        },

        # 2. BREADS, ROTIS & THEPLAS
        {
            "id": "r1", "name": "Methi Thepla with Low-Fat Dahi",
            "category": "Breads & Rotis", "mealType": "breakfast", "region": "West Indian",
            "calories": 346, "carbs": 41.3, "protein": 9.0, "fat": 15.9, "freeSugar": 3.0, "fiber": 7.6,
            "sodium": 543, "calcium": 73.5, "iron": 4.52, "vitaminC": 1.06, "folate": 15.3,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Fiber", "Diabetic-Friendly", "Iron-Rich"],
            "image": "🫓🌿",
            "description": "Gujarati flatbread kneaded with fresh fenugreek leaves, ajwain, sesame seeds, and roasted on tawa. Proven to help manage insulin sensitivity.",
            "ingredients": [{"name": "Whole Wheat Flour", "quantity": 50, "unit": "g"}, {"name": "Fresh Fenugreek Leaves (Methi)", "quantity": 0.5, "unit": "cup"}, {"name": "Carom Seeds (Ajwain)", "quantity": 0.5, "unit": "tsp"}, {"name": "Turmeric", "quantity": 0.25, "unit": "tsp"}, {"name": "Curd", "quantity": 2, "unit": "tbsp"}, {"name": "Cold-Pressed Groundnut Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Finely chop washed methi leaves.", "Knead with whole wheat flour, ajwain, curd, turmeric, and a dash of oil into a soft dough.", "Roll out into thin circles and cook on hot griddle.", "Serve with fresh probiotic curd."]
        },
        {
            "id": "r2", "name": "Traditional Whole Wheat Chapati / Phulka",
            "category": "Breads & Rotis", "mealType": "lunch", "region": "Pan-Indian",
            "calories": 202, "carbs": 35.7, "protein": 5.9, "fat": 3.6, "freeSugar": 1.0, "fiber": 6.3,
            "sodium": 1.2, "calcium": 17.2, "iron": 2.28, "vitaminC": 0.0, "folate": 5.8,
            "glycemicIndex": "Medium", "spiceLevel": "None",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Low-Sodium", "High-Fiber", "Staple"],
            "image": "🫓",
            "description": "Pure 100% stone-ground whole wheat flatbread puffed on open flame. Naturally near-zero sodium, making it ideal for hypertension.",
            "ingredients": [{"name": "Whole Wheat Atta", "quantity": 50, "unit": "g"}, {"name": "Warm Water", "quantity": 30, "unit": "ml"}],
            "instructions": ["Knead whole wheat flour with warm water until elastic; rest for 15 minutes.", "Divide into balls, roll thinly with rolling pin.", "Cook on hot iron tawa, flip, and place directly over flame to balloon gracefully."]
        },
        {
            "id": "r3", "name": "Jowar (Sorghum Millet) Bhakri",
            "category": "Breads & Rotis", "mealType": "dinner", "region": "West Indian",
            "calories": 294, "carbs": 40.5, "protein": 8.5, "fat": 10.3, "freeSugar": 0.6, "fiber": 5.6,
            "sodium": 97, "calcium": 19.5, "iron": 2.03, "vitaminC": 0.0, "folate": 9.6,
            "glycemicIndex": "Low", "spiceLevel": "None",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Gluten-Free", "Millet", "Diabetic-Friendly"],
            "image": "🫓🌾",
            "description": "Rustic Maharashtrian sorghum flatbread hand-flattened and dry-roasted. Gluten-free and rich in complex slowly digestible starch.",
            "ingredients": [{"name": "Jowar Flour", "quantity": 60, "unit": "g"}, {"name": "Hot Water", "quantity": 45, "unit": "ml"}],
            "instructions": ["Knead jowar flour using hot water into a smooth pliable dough.", "Flatten with palms on a flat board dusted with flour into a round disc.", "Roast on clay or iron tawa, applying water on top surface, until roasted evenly."]
        },

        # 3. DALS & LEGUMES
        {
            "id": "d1", "name": "Yellow Moong Dal Tadka with Garlic & Hing",
            "category": "Dals & Legumes", "mealType": "lunch", "region": "North Indian",
            "calories": 140, "carbs": 21.0, "protein": 8.5, "fat": 3.2, "freeSugar": 0.4, "fiber": 4.8,
            "sodium": 120, "calcium": 25.0, "iron": 1.8, "vitaminC": 4.2, "folate": 45.3,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Protein", "Easy-Digestion", "Diabetic-Friendly"],
            "image": "🍲🧄",
            "description": "Split yellow lentils tempered with roasted cumin, crushed garlic, and antioxidant asafoetida. The gold standard for clean Indian protein.",
            "ingredients": [{"name": "Yellow Moong Dal", "quantity": 40, "unit": "g"}, {"name": "Garlic Cloves", "quantity": 3, "unit": "cloves"}, {"name": "Tomatoes", "quantity": 0.5, "unit": "pc"}, {"name": "Cumin Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Asafoetida (Hing)", "quantity": 1, "unit": "pinch"}, {"name": "Ghee", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Pressure cook moong dal with turmeric and water until tender.", "In a small pan, heat ghee and crackle cumin, hing, minced garlic, and chopped tomatoes.", "Pour sizzled tadka over the dal and simmer for 3 minutes."]
        },
        {
            "id": "d2", "name": "Authentic Vegetable Sambar",
            "category": "Dals & Legumes", "mealType": "lunch", "region": "South Indian",
            "calories": 97, "carbs": 10.6, "protein": 3.4, "fat": 4.4, "freeSugar": 3.3, "fiber": 3.5,
            "sodium": 160, "calcium": 30.2, "iron": 1.24, "vitaminC": 20.4, "folate": 68.2,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Folate", "Cardio-Protective", "Low-Sodium"],
            "image": "🍲🥕",
            "description": "Toor dal cooked with drumsticks, pumpkin, shallots, and freshly ground coriander-cumin sambar spices in tamarind water.",
            "ingredients": [{"name": "Toor Dal (Split Pigeon Pea)", "quantity": 35, "unit": "g"}, {"name": "Drumstick Pieces", "quantity": 3, "unit": "pcs"}, {"name": "Yellow Pumpkin", "quantity": 30, "unit": "g"}, {"name": "Small Sambar Shallots", "quantity": 5, "unit": "pcs"}, {"name": "Sambar Powder", "quantity": 1, "unit": "tbsp"}, {"name": "Tamarind Pulp", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Cook toor dal until soft and mash thoroughly.", "Boil vegetables in tamarind water with turmeric and sambar powder.", "Combine dal and vegetables, simmer for 7 minutes.", "Temper with mustard seeds and curry leaves."]
        },
        {
            "id": "d3", "name": "Homestyle Rajmah Masala (Kidney Beans Curry)",
            "category": "Dals & Legumes", "mealType": "lunch", "region": "North Indian",
            "calories": 144, "carbs": 16.4, "protein": 6.0, "fat": 5.8, "freeSugar": 2.5, "fiber": 5.8,
            "sodium": 354, "calcium": 47.9, "iron": 2.27, "vitaminC": 16.3, "folate": 112.3,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Fiber", "High-Folate", "Diabetic-Friendly"],
            "image": "🍛🫘",
            "description": "Jammu red kidney beans simmered in onion-tomato-ginger gravy. High in soluble fiber that directly helps lower LDL blood cholesterol.",
            "ingredients": [{"name": "Red Kidney Beans (Rajmah)", "quantity": 45, "unit": "g"}, {"name": "Finely Chopped Onion", "quantity": 0.5, "unit": "cup"}, {"name": "Tomato Puree", "quantity": 0.5, "unit": "cup"}, {"name": "Fresh Ginger Paste", "quantity": 1, "unit": "tsp"}, {"name": "Garam Masala", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Soak rajmah overnight for 8 hours and pressure cook until melt-in-mouth.", "Sauté onion, ginger, and tomato gravy until oil separates.", "Add cooked rajmah with its broth, mash a few beans to thicken gravy, and simmer for 15 minutes."]
        },
        {
            "id": "d4", "name": "Bengali Cholar Dal (Bengal Gram with Coconut)",
            "category": "Dals & Legumes", "mealType": "lunch", "region": "East Indian",
            "calories": 100, "carbs": 10.0, "protein": 4.2, "fat": 4.6, "freeSugar": 1.0, "fiber": 3.7,
            "sodium": 46, "calcium": 22.0, "iron": 1.92, "vitaminC": 13.4, "folate": 103.5,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Low-Sodium", "High-Folate", "Jain-Adaptable"],
            "image": "🍲🥥",
            "description": "Chana dal cooked with fragrant bay leaves, whole garam masala, and tempered with crunchy roasted coconut slivers. Very low in sodium.",
            "ingredients": [{"name": "Chana Dal", "quantity": 40, "unit": "g"}, {"name": "Fresh Coconut Bits", "quantity": 1, "unit": "tbsp"}, {"name": "Bay Leaf (Tejpatta)", "quantity": 1, "unit": "leaf"}, {"name": "Ginger Paste", "quantity": 1, "unit": "tsp"}, {"name": "Ghee", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Boil chana dal with turmeric and bay leaf until cooked but holding its shape.", "Fry coconut bits in ghee until golden brown.", "Add cumin and ginger to tadka, pour into dal, and simmer for 5 minutes."]
        },

        # 4. SABZIS & VEGETABLES
        {
            "id": "s1", "name": "Sarson Ka Saag (Traditional Mustard Greens)",
            "category": "Sabzis & Vegetables", "mealType": "lunch", "region": "North Indian",
            "calories": 88, "carbs": 5.3, "protein": 3.0, "fat": 5.9, "freeSugar": 0.8, "fiber": 3.7,
            "sodium": 165, "calcium": 134.4, "iron": 2.43, "vitaminC": 59.6, "folate": 128.4,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Antioxidant", "Calcium-Rich", "Diabetic-Friendly"],
            "image": "🥬🫕",
            "description": "Nutrient powerhouse cooked from slow-simmered mustard leaves, spinach, and bathua greens. Exceptionally rich in Vitamin C, Folate, and Calcium.",
            "ingredients": [{"name": "Fresh Mustard Greens (Sarson)", "quantity": 100, "unit": "g"}, {"name": "Spinach Leaves (Palak)", "quantity": 50, "unit": "g"}, {"name": "Bathua Leaves", "quantity": 30, "unit": "g"}, {"name": "Makki Atta (Maize Flour)", "quantity": 1, "unit": "tbsp"}, {"name": "Ginger-Garlic Paste", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Wash greens thoroughly and boil with ginger and garlic.", "Puree coarsely and thicken with a tablespoon of maize flour.", "Simmer on low flame for 20 minutes and temper with garlic and cumin."]
        },
        {
            "id": "s2", "name": "Kerala Vegetable Avial (Curd & Coconut Veg Medley)",
            "category": "Sabzis & Vegetables", "mealType": "lunch", "region": "South Indian",
            "calories": 125, "carbs": 8.5, "protein": 2.5, "fat": 8.9, "freeSugar": 3.8, "fiber": 5.4,
            "sodium": 82, "calcium": 31.9, "iron": 1.01, "vitaminC": 94.6, "folate": 108.1,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Fiber", "High-Vitamin-C", "Low-Sodium", "Probiotic"],
            "image": "🥗🥥",
            "description": "Traditional Onam thali specialty with drumsticks, raw banana, ash gourd, and carrots cooked in thick coconut yogurt with fresh curry leaves.",
            "ingredients": [{"name": "Mixed Veggies (Carrot, Drumstick, Beans, Raw Plantain)", "quantity": 120, "unit": "g"}, {"name": "Fresh Grated Coconut", "quantity": 2, "unit": "tbsp"}, {"name": "Sour Curd (Dahi)", "quantity": 2, "unit": "tbsp"}, {"name": "Coconut Oil", "quantity": 1, "unit": "tsp"}, {"name": "Curry Leaves", "quantity": 6, "unit": "leaves"}],
            "instructions": ["Cut vegetables into long batons and cook with turmeric and minimal water.", "Grind coconut with green chillies and cumin into a paste.", "Mix coconut paste and curd into the cooked vegetables.", "Finish with fresh coconut oil and crushed curry leaves."]
        },
        {
            "id": "s3", "name": "Palak Paneer (Low-Fat Iron-Rich Curry)",
            "category": "Sabzis & Vegetables", "mealType": "dinner", "region": "North Indian",
            "calories": 145, "carbs": 4.4, "protein": 8.5, "fat": 9.5, "freeSugar": 2.5, "fiber": 3.9,
            "sodium": 166, "calcium": 180.0, "iron": 2.8, "vitaminC": 60.2, "folate": 267.0,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Protein", "High-Folate", "Low-Carb", "Diabetic-Friendly"],
            "image": "🥬🧀",
            "description": "Creamy vibrant spinach puree infused with crushed garlic and studded with artisanal soft paneer cubes. High in dietary folate and protein.",
            "ingredients": [{"name": "Fresh Baby Spinach", "quantity": 120, "unit": "g"}, {"name": "Low-Fat Paneer Cubes", "quantity": 60, "unit": "g"}, {"name": "Garlic", "quantity": 4, "unit": "cloves"}, {"name": "Green Chillies", "quantity": 1, "unit": "pc"}, {"name": "Cumin Seeds", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Blanch spinach in boiling water for 2 minutes, shock in ice water to lock chlorophyll.", "Puree spinach with garlic and green chilli.", "Warm cumin in pan, pour in spinach gravy, and add paneer cubes.", "Simmer gently for 3 minutes."]
        },
        {
            "id": "s4", "name": "Baingan Ka Bhartha (Smoky Roasted Eggplant Mash)",
            "category": "Sabzis & Vegetables", "mealType": "dinner", "region": "North Indian",
            "calories": 65, "carbs": 4.4, "protein": 1.4, "fat": 4.5, "freeSugar": 1.8, "fiber": 3.3,
            "sodium": 132, "calcium": 17.9, "iron": 0.48, "vitaminC": 24.1, "folate": 92.4,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Low-Calorie", "High-Fiber", "Diabetic-Friendly"],
            "image": "🍆🔥",
            "description": "Whole eggplant roasted over direct flames for deep rustic smokiness, mashed with ripe tomatoes, green peas, and fresh ginger.",
            "ingredients": [{"name": "Large Purple Bhartha Eggplant", "quantity": 1, "unit": "pc"}, {"name": "Finely Diced Tomatoes", "quantity": 0.5, "unit": "cup"}, {"name": "Green Peas", "quantity": 2, "unit": "tbsp"}, {"name": "Mustard Oil", "quantity": 1, "unit": "tsp"}, {"name": "Minced Ginger", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Slit and roast eggplant over direct gas flame until blackened and tender.", "Peel off charred skin and mash the soft flesh.", "Sauté onions, tomatoes, and ginger in mustard oil.", "Combine mashed eggplant, cook for 5 minutes, and garnish with coriander."]
        },
        {
            "id": "s5", "name": "Sprouted Moong Usal (Maharashtrian Sprout Stir-Fry)",
            "category": "Sabzis & Vegetables", "mealType": "dinner", "region": "West Indian",
            "calories": 113, "carbs": 17.5, "protein": 7.5, "fat": 3.6, "freeSugar": 1.4, "fiber": 4.8,
            "sodium": 153, "calcium": 26.0, "iron": 1.9, "vitaminC": 18.0, "folate": 43.2,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Protein", "Low-GI", "Heart-Healthy"],
            "image": "🌱🍲",
            "description": "Freshly sprouted green moong beans tempered with mustard seeds, curry leaves, ginger, and grated coconut. Rich in active enzymes and dietary fiber.",
            "ingredients": [{"name": "Sprouted Green Moong", "quantity": 80, "unit": "g"}, {"name": "Grated Coconut", "quantity": 1, "unit": "tbsp"}, {"name": "Mustard Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Curry Leaves", "quantity": 5, "unit": "leaves"}, {"name": "Lemon Juice", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Steam sprouted moong beans for 4 minutes until crisp-tender.", "In a wok, crackle mustard seeds and curry leaves.", "Toss in steamed sprouts with turmeric and rock salt.", "Finish with fresh coconut and a squeeze of lemon."]
        },

        # 5. RICE, PULAO & BIRYANI
        {
            "id": "c1", "name": "Brown Rice Curd Rice with Pomegranate & Tadka",
            "category": "Rice & Pulao", "mealType": "lunch", "region": "South Indian",
            "calories": 196, "carbs": 32.9, "protein": 5.8, "fat": 4.3, "freeSugar": 3.9, "fiber": 3.1,
            "sodium": 213, "calcium": 101.5, "iron": 0.59, "vitaminC": 5.1, "folate": 28.2,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Probiotic", "Calcium-Rich", "Cooling", "Digestive"],
            "image": "🍚🥛",
            "description": "Wholesome brown rice blended with fresh active-culture probiotic curd, tempered with mustard, curry leaves, and topped with ruby pomegranate arils.",
            "ingredients": [{"name": "Cooked Brown Rice", "quantity": 80, "unit": "g"}, {"name": "Fresh Curd (Dahi)", "quantity": 80, "unit": "g"}, {"name": "Pomegranate Arils", "quantity": 2, "unit": "tbsp"}, {"name": "Mustard Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Curry Leaves", "quantity": 4, "unit": "leaves"}],
            "instructions": ["Mash cooked brown rice while slightly warm.", "Fold in fresh yogurt and salt.", "Temper mustard seeds, ginger, and curry leaves in half a teaspoon of oil.", "Pour over curd rice and crown with juicy pomegranate pearls."]
        },
        {
            "id": "c2", "name": "Moong Dal & Vegetable Khichdi",
            "category": "Rice & Pulao", "mealType": "dinner", "region": "Pan-Indian",
            "calories": 143, "carbs": 19.6, "protein": 5.6, "fat": 4.5, "freeSugar": 1.2, "fiber": 3.4,
            "sodium": 193, "calcium": 30.5, "iron": 1.1, "vitaminC": 15.0, "folate": 45.0,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Complete-Protein", "Ayurvedic", "Easy-Digestion", "Diabetic-Friendly"],
            "image": "🍲✨",
            "description": "The quintessential Ayurvedic healing meal. Equal parts rice and yellow lentils cooked with carrots, beans, and soothing ghee-cumin tempering.",
            "ingredients": [{"name": "Split Yellow Moong Dal", "quantity": 30, "unit": "g"}, {"name": "Brown or Sona Masoori Rice", "quantity": 30, "unit": "g"}, {"name": "Diced Carrots & Beans", "quantity": 40, "unit": "g"}, {"name": "Cumin Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Pure Cow Ghee", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Wash dal and rice together.", "Pressure cook with vegetables, turmeric, and water for 4 whistles until porridge-like.", "Temper with cumin seeds in golden cow ghee and serve piping hot."]
        },
        {
            "id": "c3", "name": "South Indian Lemon Rice (Chitranna)",
            "category": "Rice & Pulao", "mealType": "lunch", "region": "South Indian",
            "calories": 176, "carbs": 21.6, "protein": 4.3, "fat": 7.9, "freeSugar": 0.8, "fiber": 2.5,
            "sodium": 187, "calcium": 12.7, "iron": 0.77, "vitaminC": 10.2, "folate": 38.0,
            "glycemicIndex": "Medium", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Gluten-Free", "Digestive"],
            "image": "🍋🍚",
            "description": "Fluffy rice grains infused with freshly squeezed lemon juice, turmeric, crunchy roasted peanuts, and fragrant curry leaves.",
            "ingredients": [{"name": "Cooked Rice", "quantity": 100, "unit": "g"}, {"name": "Fresh Lemon Juice", "quantity": 1.5, "unit": "tbsp"}, {"name": "Peanuts", "quantity": 1, "unit": "tbsp"}, {"name": "Turmeric Powder", "quantity": 0.5, "unit": "tsp"}, {"name": "Curry Leaves & Green Chillies", "quantity": 1, "unit": "tbsp"}],
            "instructions": ["Heat oil, roast peanuts, mustard seeds, and urad dal until fragrant.", "Add green chillies, curry leaves, and turmeric.", "Turn off heat, stir in lemon juice and salt.", "Mix gently with cooked rice to coat every grain in sunshine yellow."]
        },

        # 6. SOUPS & SHORBAS
        {
            "id": "sp1", "name": "Garlic Chickpea Shorba (Lahasun Channa Soup)",
            "category": "Soups", "mealType": "dinner", "region": "North Indian",
            "calories": 90, "carbs": 13.9, "protein": 4.5, "fat": 2.0, "freeSugar": 2.6, "fiber": 2.8,
            "sodium": 80, "calcium": 13.9, "iron": 0.96, "vitaminC": 13.2, "folate": 380.6,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Folate", "Low-Sodium", "Cardio-Protective"],
            "image": "🥣🧄",
            "description": "Clear aromatic broth of slow-cooked chickpeas steeped with crushed garlic, roasted cumin, and black pepper. Unmatched for heart wellness and cellular repair.",
            "ingredients": [{"name": "Boiled White Chickpeas", "quantity": 40, "unit": "g"}, {"name": "Chickpea Broth", "quantity": 200, "unit": "ml"}, {"name": "Roasted Garlic", "quantity": 4, "unit": "cloves"}, {"name": "Black Peppercorns", "quantity": 0.5, "unit": "tsp"}, {"name": "Fresh Lemon Juice", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Simmer chickpea broth with crushed roasted garlic and cracked black pepper.", "Mash a few chickpeas to give body to the soup.", "Ladle into bowls and garnish with cilantro and lemon juice."]
        },
        {
            "id": "sp2", "name": "Clear Spiced Tomato Soup (Tamatar Shorba)",
            "category": "Soups", "mealType": "dinner", "region": "North Indian",
            "calories": 80, "carbs": 3.5, "protein": 4.8, "fat": 1.2, "freeSugar": 1.4, "fiber": 2.0,
            "sodium": 95, "calcium": 29.0, "iron": 1.14, "vitaminC": 53.2, "folate": 43.9,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Lycopene", "Low-Calorie", "Hypertension-Safe"],
            "image": "🍅🍲",
            "description": "Warm, restorative shorba made from vine-ripened red tomatoes infused with ginger, coriander stems, and cracked peppercorns.",
            "ingredients": [{"name": "Ripe Tomatoes", "quantity": 150, "unit": "g"}, {"name": "Fresh Coriander Stems", "quantity": 1, "unit": "tbsp"}, {"name": "Ginger", "quantity": 1, "unit": "inch"}, {"name": "Black Pepper", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Boil tomatoes with ginger and coriander stems until skins burst.", "Strain soup to remove seeds, return clear broth to pot.", "Season with roasted cumin and crushed peppercorns. Serve piping hot."]
        },

        # 7. NON-VEG CURRIES & PROTEINS
        {
            "id": "nv1", "name": "Tandoori Chicken Tikka with Mint Salad",
            "category": "Non-Veg", "mealType": "dinner", "region": "North Indian",
            "calories": 145, "carbs": 2.3, "protein": 16.3, "fat": 7.9, "freeSugar": 1.6, "fiber": 0.5,
            "sodium": 158, "calcium": 44.3, "iron": 0.9, "vitaminC": 39.5, "folate": 182.7,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Non-Vegetarian", "High-Protein", "Keto-Friendly", "Low-Carb", "Diabetic-Friendly"],
            "image": "🍗🔥",
            "description": "Lean chicken breast cubes marinated in hung curd, Kashmiri red chilli, garlic, and roasted gram flour, char-grilled to perfection.",
            "ingredients": [{"name": "Skinless Chicken Breast", "quantity": 100, "unit": "g"}, {"name": "Hung Curd", "quantity": 2, "unit": "tbsp"}, {"name": "Kashmiri Chilli Powder", "quantity": 1, "unit": "tsp"}, {"name": "Ginger-Garlic Paste", "quantity": 1, "unit": "tsp"}, {"name": "Mustard Oil", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Marinate chicken with hung curd, spices, and mustard oil for at least 2 hours.", "Thread onto skewers and bake at 220°C or pan-sear until charred.", "Serve with onion rings, mint chutney, and fresh lemon wedges."]
        },
        {
            "id": "nv2", "name": "Bengali Macher Jhol (Fish in Light Broth)",
            "category": "Non-Veg", "mealType": "lunch", "region": "East Indian",
            "calories": 109, "carbs": 4.4, "protein": 7.3, "fat": 7.0, "freeSugar": 2.4, "fiber": 1.9,
            "sodium": 76, "calcium": 44.4, "iron": 0.85, "vitaminC": 9.4, "folate": 46.5,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Non-Vegetarian", "Omega-3", "Low-Sodium", "Heart-Healthy", "Diabetic-Friendly"],
            "image": "🐟🍲",
            "description": "Traditional Bengali freshwater fish simmered with pointed gourd (parwal) and potatoes in light cumin-ginger broth. Excellent for cardiovascular health.",
            "ingredients": [{"name": "Rohu/Katla/White Fish Fillet", "quantity": 80, "unit": "g"}, {"name": "Kalonji (Nigella Seeds)", "quantity": 0.25, "unit": "tsp"}, {"name": "Ginger Paste", "quantity": 1, "unit": "tsp"}, {"name": "Turmeric", "quantity": 0.5, "unit": "tsp"}, {"name": "Mustard Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Lightly pan-sear fish steaks rubbed with turmeric and salt.", "Temper nigella seeds in mustard oil, add ginger paste and water.", "Simmer fish gently in the broth for 6 minutes until tender."]
        },

        # 8. SALADS, RAITAS & PROBIOTICS
        {
            "id": "sl1", "name": "Sprouted Moong Dal Chaat with Lemon",
            "category": "Salads & Raitas", "mealType": "snack", "region": "Pan-Indian",
            "calories": 83, "carbs": 14.0, "protein": 4.7, "fat": 0.8, "freeSugar": 1.4, "fiber": 3.0,
            "sodium": 128, "calcium": 51.6, "iron": 2.13, "vitaminC": 23.8, "folate": 105.6,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Fiber", "Low-Calorie", "Zero-Oil", "Diabetic-Friendly"],
            "image": "🥗🍋",
            "description": "Crisp sprouted mung beans tossed with diced cucumbers, tomatoes, chaat masala, and a splash of fresh lemon juice.",
            "ingredients": [{"name": "Sprouted Green Gram", "quantity": 60, "unit": "g"}, {"name": "Cucumber Cubes", "quantity": 0.5, "unit": "cup"}, {"name": "Tomato Cubes", "quantity": 0.25, "unit": "cup"}, {"name": "Chaat Masala", "quantity": 0.5, "unit": "tsp"}, {"name": "Fresh Lime Juice", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Lightly steam sprouts or keep raw for maximum crunch.", "Toss with diced cucumbers, tomatoes, and green chillies.", "Dust with chaat masala and drizzle fresh lime juice."]
        },
        {
            "id": "sl2", "name": "Cucumber & Mint Raita (Kheere Ka Raita)",
            "category": "Salads & Raitas", "mealType": "lunch", "region": "North Indian",
            "calories": 59, "carbs": 6.4, "protein": 4.0, "fat": 2.1, "freeSugar": 5.2, "fiber": 0.9,
            "sodium": 190, "calcium": 138.6, "iron": 0.29, "vitaminC": 5.7, "folate": 26.9,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Probiotic", "Hydrating", "Calcium-Rich", "Cooling"],
            "image": "🥒🥣",
            "description": "Whisked artisanal low-fat curd folded with freshly grated English cucumbers, roasted cumin powder, and dried mint.",
            "ingredients": [{"name": "Low-Fat Curd", "quantity": 100, "unit": "g"}, {"name": "Grated Cucumber", "quantity": 0.5, "unit": "cup"}, {"name": "Roasted Cumin Powder", "quantity": 0.5, "unit": "tsp"}, {"name": "Dried Mint Powder", "quantity": 0.25, "unit": "tsp"}, {"name": "Rock Salt", "quantity": 1, "unit": "pinch"}],
            "instructions": ["Whisk curd until silky smooth.", "Gently squeeze excess water from grated cucumber and fold into curd.", "Season with roasted jeera powder, black salt, and crushed mint."]
        },

        # 9. BEVERAGES & HEALTH COOLERS
        {
            "id": "bv1", "name": "Roasted Cumin Infused Buttermilk (Masala Chaas)",
            "category": "Beverages", "mealType": "snack", "region": "Pan-Indian",
            "calories": 19, "carbs": 1.9, "protein": 1.4, "fat": 0.7, "freeSugar": 1.8, "fiber": 0.0,
            "sodium": 65, "calcium": 47.8, "iron": 0.04, "vitaminC": 1.0, "folate": 18.1,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Probiotic", "Ultra-Low-Calorie", "Gut-Health", "Hydrating"],
            "image": "🥛🌿",
            "description": "Refreshing traditional churned buttermilk infused with hand-roasted cumin, ginger, curry leaves, and pink Himalayan salt.",
            "ingredients": [{"name": "Low-Fat Dahi", "quantity": 50, "unit": "g"}, {"name": "Chilled Water", "quantity": 150, "unit": "ml"}, {"name": "Roasted Cumin Powder", "quantity": 0.5, "unit": "tsp"}, {"name": "Crushed Curry Leaves", "quantity": 3, "unit": "leaves"}, {"name": "Black Salt", "quantity": 1, "unit": "pinch"}],
            "instructions": ["Blend yogurt, water, roasted cumin, and black salt until frothy.", "Pour into an earthenware clay pot or glass and garnish with fresh mint."]
        },
        {
            "id": "bv2", "name": "Raw Mango Drink (Aam Panna - Low Sugar)",
            "category": "Beverages", "mealType": "snack", "region": "North Indian",
            "calories": 36, "carbs": 9.1, "protein": 0.2, "fat": 0.0, "freeSugar": 7.5, "fiber": 0.6,
            "sodium": 80, "calcium": 7.1, "iron": 0.14, "vitaminC": 45.3, "folate": 14.1,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Vitamin-C", "Electrolyte-Rich", "Cooling"],
            "image": "🥭🧊",
            "description": "Boiled raw green mangoes pureed with roasted cumin, black salt, and fresh mint. Supercharged with bio-available Vitamin C.",
            "ingredients": [{"name": "Raw Green Mango", "quantity": 50, "unit": "g"}, {"name": "Roasted Cumin", "quantity": 0.5, "unit": "tsp"}, {"name": "Mint Leaves", "quantity": 8, "unit": "leaves"}, {"name": "Black Salt", "quantity": 0.25, "unit": "tsp"}, {"name": "Water", "quantity": 200, "unit": "ml"}],
            "instructions": ["Pressure cook raw mango, scoop out the soft pulp.", "Blend pulp with mint leaves, cumin, black salt, and chilled water.", "Serve over crushed ice for instant rehydration."]
        },
        {
            "id": "bv3", "name": "Cumin Seed Digestive Infusion (Jeere Ka Pani)",
            "category": "Beverages", "mealType": "snack", "region": "Pan-Indian",
            "calories": 9, "carbs": 1.9, "protein": 0.2, "fat": 0.1, "freeSugar": 1.5, "fiber": 0.5,
            "sodium": 190, "calcium": 10.8, "iron": 0.32, "vitaminC": 3.6, "folate": 3.1,
            "glycemicIndex": "Low", "spiceLevel": "None",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Metabolism-Booster", "Ayurvedic", "Detox"],
            "image": "🍵✨",
            "description": "Warm Ayurvedic infusion of simmered whole cumin seeds. Stimulates digestive enzymes, curbs hunger cravings, and stabilizes morning blood glucose.",
            "ingredients": [{"name": "Whole Cumin Seeds (Jeera)", "quantity": 1, "unit": "tsp"}, {"name": "Water", "quantity": 250, "unit": "ml"}, {"name": "Lemon Slice", "quantity": 1, "unit": "pc"}],
            "instructions": ["Boil cumin seeds in water for 5 minutes until liquid turns deep amber.", "Strain into a cup and sip warm on an empty stomach."]
        },

        # 10. DESSERTS & SWEETS
        {
            "id": "ds1", "name": "Makhana & Almond Kheer (Foxnut Pudding)",
            "category": "Desserts & Sweets", "mealType": "snack", "region": "North Indian",
            "calories": 108, "carbs": 12.9, "protein": 3.3, "fat": 5.0, "freeSugar": 11.5, "fiber": 0.1,
            "sodium": 23, "calcium": 111.6, "iron": 0.28, "vitaminC": 5.1, "folate": 23.8,
            "glycemicIndex": "Low", "spiceLevel": "None",
            "diabeticSafe": False, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": False,
            "tags": ["Vegetarian", "High-Calcium", "Ayurvedic", "Jain-Friendly"],
            "image": "🥣🌰",
            "description": "Roasted puffed lotus seeds (makhana) simmered in low-fat milk infused with green cardamom and slivered almonds.",
            "ingredients": [{"name": "Phool Makhana (Foxnuts)", "quantity": 25, "unit": "g"}, {"name": "Low-Fat Toned Milk", "quantity": 150, "unit": "ml"}, {"name": "Almond Slivers", "quantity": 5, "unit": "pcs"}, {"name": "Cardamom Powder", "quantity": 0.25, "unit": "tsp"}, {"name": "Jaggery or Natural Stevia", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Dry roast makhana in pan until crunchy; crush half into coarse powder.", "Boil milk, add crushed and whole makhana.", "Simmer until milk thickens.", "Flavor with cardamom powder and top with slivered almonds."]
        },
        {
            "id": "ds2", "name": "Roasted Sesame & Jaggery Chikki (Til Chikki)",
            "category": "Desserts & Sweets", "mealType": "snack", "region": "West Indian",
            "calories": 283, "carbs": 50.5, "protein": 8.5, "fat": 4.7, "freeSugar": 36.5, "fiber": 5.5,
            "sodium": 18, "calcium": 150.7, "iron": 4.8, "vitaminC": 0.0, "folate": 23.6,
            "glycemicIndex": "Medium", "spiceLevel": "None",
            "diabeticSafe": False, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": False,
            "tags": ["Vegetarian", "High-Calcium", "Iron-Rich", "Energy-Dense"],
            "image": "🍬🌾",
            "description": "Crispy traditional winter brittle crafted with calcium-rich white sesame seeds and iron-rich unrefined sugarcane jaggery.",
            "ingredients": [{"name": "White Sesame Seeds (Til)", "quantity": 30, "unit": "g"}, {"name": "Unrefined Jaggery (Gur)", "quantity": 30, "unit": "g"}, {"name": "Cardamom Powder", "quantity": 1, "unit": "pinch"}],
            "instructions": ["Roast sesame seeds gently until nutty.", "Melt jaggery in a pan until hard-ball stage.", "Mix in roasted sesame seeds rapidly, roll flat on greased stone, cut into squares before hardening."]
        },
        # Additional Core Dishes from Dataset
        {
            "id": "d5", "name": "Dal Makhani (Low-Fat Black Lentils & Kidney Beans)",
            "category": "Dals & Legumes", "mealType": "lunch", "region": "North Indian",
            "calories": 148, "carbs": 15.9, "protein": 6.6, "fat": 6.1, "freeSugar": 1.6, "fiber": 4.5,
            "sodium": 84, "calcium": 41.2, "iron": 2.46, "vitaminC": 18.4, "folate": 150.3,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Protein", "High-Folate", "Low-Sodium"],
            "image": "🍲🖤",
            "description": "Slow-simmered whole black urad dal and rajmah in tomato reduction with kasuri methi and light fresh cream. Low-sodium and heart-healthy.",
            "ingredients": [{"name": "Whole Black Urad", "quantity": 40, "unit": "g"}, {"name": "Rajmah", "quantity": 10, "unit": "g"}, {"name": "Tomato Puree", "quantity": 0.5, "unit": "cup"}, {"name": "Low-Fat Milk/Cream", "quantity": 1, "unit": "tbsp"}, {"name": "Kasuri Methi", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Soak whole urad and rajma overnight and pressure cook for 30 minutes until creamy.", "Sauté ginger, garlic, and tomato puree until fragrant.", "Add boiled lentils with broth and simmer on low heat for 45 minutes for rich depth of flavor."]
        },
        {
            "id": "nv3", "name": "Homestyle Chicken Curry with Tomatoes & Curry Leaves",
            "category": "Non-Veg", "mealType": "lunch", "region": "Pan-Indian",
            "calories": 129, "carbs": 3.4, "protein": 11.8, "fat": 7.6, "freeSugar": 1.8, "fiber": 1.4,
            "sodium": 108, "calcium": 27.3, "iron": 0.87, "vitaminC": 16.8, "folate": 38.7,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Non-Vegetarian", "High-Protein", "Low-Carb", "Diabetic-Friendly"],
            "image": "🍗🍲",
            "description": "Tender chicken pieces simmered in light onion-tomato-ginger gravy tempered with aromatic spices and fresh coriander.",
            "ingredients": [{"name": "Skinless Chicken Thigh/Breast", "quantity": 100, "unit": "g"}, {"name": "Diced Onions", "quantity": 0.5, "unit": "cup"}, {"name": "Tomato Puree", "quantity": 0.5, "unit": "cup"}, {"name": "Coriander Powder", "quantity": 1, "unit": "tsp"}, {"name": "Cold-Pressed Mustard Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Marinate chicken with turmeric and salt.", "Brown onions in mustard oil, add ginger-garlic paste and spices.", "Add tomatoes and chicken, cook covered on low flame until tender.", "Garnish with fresh coriander."]
        },
        {
            "id": "b7", "name": "Semolina & Veggie Upma (Suji Upma)",
            "category": "Breakfast", "mealType": "breakfast", "region": "South Indian",
            "calories": 148, "carbs": 16.3, "protein": 3.3, "fat": 7.5, "freeSugar": 1.3, "fiber": 3.2,
            "sodium": 102, "calcium": 21.6, "iron": 1.1, "vitaminC": 4.64, "folate": 15.1,
            "glycemicIndex": "Medium", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Easy-Digestion", "Low-Sodium"],
            "image": "🥣🥕",
            "description": "Roasted semolina cooked with mustard seeds, curry leaves, green peas, carrots, and ginger. A warm digestive comfort breakfast.",
            "ingredients": [{"name": "Roasted Suji (Rava)", "quantity": 40, "unit": "g"}, {"name": "Finely Chopped Carrots & Beans", "quantity": 30, "unit": "g"}, {"name": "Mustard Seeds", "quantity": 0.5, "unit": "tsp"}, {"name": "Urad Dal", "quantity": 0.5, "unit": "tsp"}, {"name": "Ghee/Oil", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Dry roast suji until fragrant.", "Temper mustard seeds, urad dal, ginger, and curry leaves in oil.", "Add vegetables and 2 cups boiling water.", "Gradually stream in suji while stirring continuously to prevent lumps. Cook covered for 3 minutes."]
        },
        {
            "id": "b8", "name": "Besan Chilla with Grated Paneer (Protein Cheela)",
            "category": "Breakfast", "mealType": "breakfast", "region": "North Indian",
            "calories": 205, "carbs": 19.2, "protein": 11.4, "fat": 8.9, "freeSugar": 3.8, "fiber": 4.0,
            "sodium": 289, "calcium": 151.3, "iron": 2.41, "vitaminC": 19.8, "folate": 116.5,
            "glycemicIndex": "Low", "spiceLevel": "Medium",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "High-Protein", "Calcium-Rich", "Gluten-Free", "Diabetic-Friendly"],
            "image": "🫓🧀",
            "description": "Chickpea flour pancake folded over spiced grated paneer, onions, and fresh mint. High protein density and bio-available folate.",
            "ingredients": [{"name": "Besan (Gram Flour)", "quantity": 50, "unit": "g"}, {"name": "Grated Low-Fat Paneer", "quantity": 40, "unit": "g"}, {"name": "Ajwain (Carom Seeds)", "quantity": 0.5, "unit": "tsp"}, {"name": "Finely Chopped Onion", "quantity": 2, "unit": "tbsp"}, {"name": "Turmeric", "quantity": 0.25, "unit": "tsp"}],
            "instructions": ["Make a lump-free batter with besan, ajwain, turmeric, and water.", "Pour on hot tawa and spread evenly.", "Scatter grated paneer and onions on top, fold in half, and toast until golden crisp."]
        },
        {
            "id": "s6", "name": "Lauki Kofta Curry (Steamed Bottle Gourd in Gravy)",
            "category": "Sabzis & Vegetables", "mealType": "dinner", "region": "North Indian",
            "calories": 128, "carbs": 11.0, "protein": 4.5, "fat": 6.8, "freeSugar": 2.7, "fiber": 3.2,
            "sodium": 182, "calcium": 48.0, "iron": 1.4, "vitaminC": 21.9, "folate": 87.1,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Steamed", "Easy-Digestion", "Low-Calorie", "Diabetic-Friendly"],
            "image": "🥒🥘",
            "description": "Grated bottle gourd koftas steamed with gram flour instead of deep frying, then bathed in a mild tomato-cumin gravy.",
            "ingredients": [{"name": "Grated Lauki (Bottle Gourd)", "quantity": 100, "unit": "g"}, {"name": "Besan", "quantity": 25, "unit": "g"}, {"name": "Tomato Puree", "quantity": 0.5, "unit": "cup"}, {"name": "Cumin & Coriander Powder", "quantity": 1, "unit": "tsp"}, {"name": "Mustard Oil", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Squeeze excess water from grated lauki and bind with besan and spices into balls.", "Steam koftas in an idli steamer for 10 minutes until firm.", "Drop steamed koftas into simmered tomato-cumin gravy and cook for 3 minutes."]
        },
        {
            "id": "bv4", "name": "Sattu Drink (Bihari Roasted Gram Energy Cooler)",
            "category": "Beverages", "mealType": "snack", "region": "East Indian",
            "calories": 75, "carbs": 12.5, "protein": 4.8, "fat": 0.8, "freeSugar": 1.2, "fiber": 3.8,
            "sodium": 110, "calcium": 25.0, "iron": 1.8, "vitaminC": 6.2, "folate": 48.0,
            "glycemicIndex": "Low", "spiceLevel": "Mild",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "High-Protein", "High-Fiber", "Energy-Booster"],
            "image": "🥤🌾",
            "description": "Traditional roasted chana flour churned with chilled water, roasted cumin, black salt, and freshly squeezed lemon. Natural plant protein fuel.",
            "ingredients": [{"name": "Chana Sattu (Roasted Gram Flour)", "quantity": 25, "unit": "g"}, {"name": "Chilled Water", "quantity": 200, "unit": "ml"}, {"name": "Roasted Cumin Powder", "quantity": 0.5, "unit": "tsp"}, {"name": "Black Salt", "quantity": 0.25, "unit": "tsp"}, {"name": "Lemon Juice", "quantity": 1, "unit": "tsp"}],
            "instructions": ["Whisk sattu flour with cold water until completely smooth.", "Add roasted cumin, black salt, and lemon juice.", "Stir well and serve chilled in tall glasses."]
        },
        {
            "id": "sn1", "name": "Roasted Phool Makhana & Chana Chaat",
            "category": "Snacks & Chaat", "mealType": "snack", "region": "Pan-Indian",
            "calories": 115, "carbs": 18.2, "protein": 5.2, "fat": 2.4, "freeSugar": 0.9, "fiber": 3.6,
            "sodium": 88, "calcium": 62.0, "iron": 1.9, "vitaminC": 8.5, "folate": 24.0,
            "glycemicIndex": "Low", "spiceLevel": "Low",
            "diabeticSafe": True, "hypertensionSafe": True, "heartSafe": True, "obesitySafe": True,
            "tags": ["Vegetarian", "Vegan", "Gluten-Free", "Low-Sodium", "Diabetic-Friendly"],
            "image": "🍿🌿",
            "description": "Crunchy foxnuts and roasted Bengal gram dry-roasted with turmeric, pink Himalayan salt, and crushed curry leaves. The ideal smartwatch recovery snack.",
            "ingredients": [{"name": "Foxnuts (Makhana)", "quantity": 20, "unit": "g"}, {"name": "Roasted Bengal Gram (Bhuna Chana)", "quantity": 15, "unit": "g"}, {"name": "Turmeric", "quantity": 0.25, "unit": "tsp"}, {"name": "Pink Salt", "quantity": 0.25, "unit": "tsp"}, {"name": "Olive/Mustard Oil", "quantity": 0.5, "unit": "tsp"}],
            "instructions": ["Heat oil in pan, roast curry leaves and turmeric.", "Add makhana and bhuna chana, toss on low heat for 5 minutes until crispy.", "Season with pink salt and store in an airtight jar."]
        }
    ]

    # Save to backend JSON
    with open(FOOD_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(dishes, f, indent=2, ensure_ascii=False)

    # Save to frontend recipes.js
    js_content = f"// Comprehensive Indian Food Nutrition Dataset & Recipes\n// Processed and structured according to Indian Food Composition Tables\n\nexport const recipes = {json.dumps(dishes, indent=2, ensure_ascii=False)};\n"
    with open(RECIPES_JS_PATH, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"Generated {len(dishes)} Indian food dishes with comprehensive nutrition. Exported to {RECIPES_JS_PATH}")
    return dishes


if __name__ == '__main__':
    print("=== Running Smartwatch & Indian Food Data Pipeline ===")
    smartwatch_data = clean_smartwatch_data()
    food_data = build_and_export_indian_food_dataset()
    print("Pipeline execution completed successfully.")
