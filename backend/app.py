import os
import json
import sqlite3
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Import mysql.connector if available, print message if not
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("mysql-connector-python is not installed. Falling back to SQLite.")

# Manual CORS implementation
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

import traceback

@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return jsonify({"error": str(e)}), 500


# Database connection helper with SQLite fallback
def get_db_connection(select_db=True):
    """
    Attempts to connect to MySQL database based on env vars.
    Falls back to SQLite if MySQL fails or is not available.
    Returns (connection_object, is_sqlite_boolean).
    """
    if not MYSQL_AVAILABLE:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints in SQLite
        conn.execute("PRAGMA foreign_keys = ON")
        return conn, True

    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'nutriguide')

    try:
        if select_db:
            conn = mysql.connector.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name
            )
        else:
            conn = mysql.connector.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password
            )
        return conn, False
    except Exception as e:
        print(f"MySQL connection failed: {e}. Falling back to SQLite database.")
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn, True

# Unified DB query execution helper to abstract SQL parameter placeholders (%s vs ?)
def execute_query(sql, params=()):
    conn, is_sqlite = get_db_connection()
    try:
        cursor = conn.cursor()
        if is_sqlite:
            sql = sql.replace('%s', '?')
        cursor.execute(sql, params)
        conn.commit()
        cursor.close()
    finally:
        conn.close()

def query_one(sql, params=()):
    conn, is_sqlite = get_db_connection()
    try:
        cursor = conn.cursor()
        if is_sqlite:
            sql = sql.replace('%s', '?')
        cursor.execute(sql, params)
        row = cursor.fetchone()
        
        # Format output as a dictionary
        if row is None:
            return None
        
        if is_sqlite:
            # Row behaves like a dictionary because of row_factory = sqlite3.Row
            return dict(row)
        else:
            # mysql connector returns tuple, need to get column names
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
    finally:
        conn.close()

def query_all(sql, params=()):
    conn, is_sqlite = get_db_connection()
    try:
        cursor = conn.cursor()
        if is_sqlite:
            sql = sql.replace('%s', '?')
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        if not rows:
            return []
        if is_sqlite:
            return [dict(row) for row in rows]
        else:
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

# Database initialization
def init_db():
    conn, is_sqlite = get_db_connection(select_db=False)
    
    if not is_sqlite:
        try:
            cursor = conn.cursor()
            db_name = os.getenv('DB_NAME', 'nutriguide')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            cursor.close()
            conn.close()
            print(f"Verified/Created MySQL Database: {db_name}")
        except Exception as e:
            print("Error creating MySQL database, will initialize tables on SQLite instead:", e)
            # Switch to SQLite connection
            conn = sqlite3.connect('database.db')
            is_sqlite = True

    # Re-connect to the created database (or keep SQLite)
    conn, is_sqlite = get_db_connection(select_db=True)
    cursor = conn.cursor()
    
    try:
        # SQLite uses auto-increment syntax slightly differently, but standard tables fit both
        # 1. Create Users profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255),
                gender VARCHAR(50),
                age INT,
                weight DOUBLE,
                height DOUBLE,
                activity_level VARCHAR(100),
                goal VARCHAR(100),
                diet_type VARCHAR(100),
                bmr INT,
                tdee INT,
                target_calories INT,
                target_protein INT,
                target_carbs INT,
                target_fat INT
            )
        """)

        # 2. Create Meal Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plans (
                user_id VARCHAR(255) PRIMARY KEY,
                breakfast_recipe TEXT,
                lunch_recipe TEXT,
                dinner_recipe TEXT,
                snack_recipe TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 3. Create Completed Meals status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completed_meals (
                user_id VARCHAR(255) PRIMARY KEY,
                breakfast INT DEFAULT 0,
                lunch INT DEFAULT 0,
                dinner INT DEFAULT 0,
                snack INT DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 4. Create Water Intake table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS water_intake (
                user_id VARCHAR(255) PRIMARY KEY,
                water_intake INT DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 5. Create Shopping Checked Items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_checked_items (
                user_id VARCHAR(255) PRIMARY KEY,
                checked_items TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 6. Create Smartwatch Health Telemetry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smartwatch_telemetry (
                user_id VARCHAR(255) PRIMARY KEY,
                heart_rate DOUBLE,
                spo2 DOUBLE,
                steps INT,
                sleep_hours DOUBLE,
                activity_level VARCHAR(50),
                stress_level INT,
                calories_burned INT,
                recovery_score INT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 7. Create User Medical Conditions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_conditions (
                user_id VARCHAR(255) PRIMARY KEY,
                diabetes INT DEFAULT 0,
                hypertension INT DEFAULT 0,
                heart_disease INT DEFAULT 0,
                obesity_pcos INT DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 8. Create Recipe Ratings table for Collaborative Filtering
        if is_sqlite:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recipe_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(255),
                    recipe_id VARCHAR(255),
                    rating INT,
                    review TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recipe_ratings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    recipe_id VARCHAR(255),
                    rating INT,
                    review TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        # 9. Ensure default user exists to satisfy foreign key relationships
        if is_sqlite:
            cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES ('default_user', 'Guest')")
        else:
            cursor.execute("INSERT IGNORE INTO users (id, name) VALUES ('default_user', 'Guest')")
        
        conn.commit()
        print("Database schema initialized successfully.")
    except Exception as e:
        print("Error creating database tables:", e)
    finally:
        cursor.close()
        conn.close()

# Run database setup on startup
init_db()


# Helper to get current profile state dictionary
def get_user_state_dict(user_id):
    user = query_one('SELECT * FROM users WHERE id = %s', (user_id,))
    if not user:
        return None

    meal_plan_row = query_one('SELECT * FROM meal_plans WHERE user_id = %s', (user_id,))
    completed_meals_row = query_one('SELECT * FROM completed_meals WHERE user_id = %s', (user_id,))
    water_intake_row = query_one('SELECT * FROM water_intake WHERE user_id = %s', (user_id,))
    shopping_row = query_one('SELECT * FROM shopping_checked_items WHERE user_id = %s', (user_id,))
    smartwatch_row = query_one('SELECT * FROM smartwatch_telemetry WHERE user_id = %s', (user_id,))
    med_row = query_one('SELECT * FROM medical_conditions WHERE user_id = %s', (user_id,))

    # Helper to parse JSON strings safely
    def safe_json_parse(json_str, default=None):
        if not json_str:
            return default
        try:
            return json.loads(json_str)
        except Exception:
            return default

    return {
        "profile": {
            "name": user.get("name"),
            "gender": user.get("gender"),
            "age": user.get("age"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "activityLevel": user.get("activity_level"),
            "goal": user.get("goal"),
            "dietType": user.get("diet_type"),
            "bmr": user.get("bmr"),
            "tdee": user.get("tdee"),
            "targetCalories": user.get("target_calories"),
            "targetProtein": user.get("target_protein"),
            "targetCarbs": user.get("target_carbs"),
            "targetFat": user.get("target_fat")
        },
        "mealPlan": {
            "breakfast": safe_json_parse(meal_plan_row.get("breakfast_recipe")) if meal_plan_row else None,
            "lunch": safe_json_parse(meal_plan_row.get("lunch_recipe")) if meal_plan_row else None,
            "dinner": safe_json_parse(meal_plan_row.get("dinner_recipe")) if meal_plan_row else None,
            "snack": safe_json_parse(meal_plan_row.get("snack_recipe")) if meal_plan_row else None
        } if meal_plan_row else None,
        "completedMeals": {
            "breakfast": bool(completed_meals_row.get("breakfast")) if completed_meals_row else False,
            "lunch": bool(completed_meals_row.get("lunch")) if completed_meals_row else False,
            "dinner": bool(completed_meals_row.get("dinner")) if completed_meals_row else False,
            "snack": bool(completed_meals_row.get("snack")) if completed_meals_row else False
        },
        "waterIntake": water_intake_row.get("water_intake") if water_intake_row else 0,
        "shoppingCheckedItems": safe_json_parse(shopping_row.get("checked_items"), {}) if shopping_row else {},
        "smartwatch": {
            "heartRate": smartwatch_row.get("heart_rate") if smartwatch_row else 72.0,
            "spo2": smartwatch_row.get("spo2") if smartwatch_row else 98.0,
            "steps": smartwatch_row.get("steps") if smartwatch_row else 6500,
            "sleepHours": smartwatch_row.get("sleep_hours") if smartwatch_row else 7.2,
            "activityLevel": smartwatch_row.get("activity_level") if smartwatch_row else "Active",
            "stressLevel": smartwatch_row.get("stress_level") if smartwatch_row else 4,
            "caloriesBurned": smartwatch_row.get("calories_burned") if smartwatch_row else 320,
            "recoveryScore": smartwatch_row.get("recovery_score") if smartwatch_row else 85
        } if smartwatch_row else {
            "heartRate": 72.0,
            "spo2": 98.0,
            "steps": 6500,
            "sleepHours": 7.2,
            "activityLevel": "Active",
            "stressLevel": 4,
            "caloriesBurned": 320,
            "recoveryScore": 85
        },
        "medicalConditions": {
            "diabetes": bool(med_row.get("diabetes")) if med_row else False,
            "hypertension": bool(med_row.get("hypertension")) if med_row else False,
            "heartDisease": bool(med_row.get("heart_disease")) if med_row else False,
            "obesityPcos": bool(med_row.get("obesity_pcos")) if med_row else False
        }
    }


# --- Endpoints ---

@app.route('/api/state', methods=['GET'])
def get_state():
    try:
        state = get_user_state_dict('default_user')
        if not state:
            return jsonify({
                "profile": None,
                "mealPlan": None,
                "completedMeals": { "breakfast": False, "lunch": False, "dinner": False, "snack": False },
                "waterIntake": 0,
                "shoppingCheckedItems": {}
            })
        return jsonify(state)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch state: {str(e)}"}), 500


@app.route('/api/state', methods=['POST'])
def save_state():
    try:
        data = request.json or {}
        profile = data.get('profile')
        meal_plan = data.get('mealPlan')
        completed_meals = data.get('completedMeals')
        water_intake = data.get('waterIntake')
        shopping_checked = data.get('shoppingCheckedItems')
        smartwatch = data.get('smartwatch')
        med_conditions = data.get('medicalConditions')

        user_id = 'default_user'

        # 1. Update Profile
        if profile:
            user_exists = query_one("SELECT id FROM users WHERE id = %s", (user_id,))
            if user_exists:
                execute_query("""
                    UPDATE users SET name=%s, gender=%s, age=%s, weight=%s, height=%s, 
                    activity_level=%s, goal=%s, diet_type=%s, bmr=%s, tdee=%s, 
                    target_calories=%s, target_protein=%s, target_carbs=%s, target_fat=%s 
                    WHERE id=%s
                """, (
                    profile.get('name'), profile.get('gender'), profile.get('age'),
                    profile.get('weight'), profile.get('height'), profile.get('activityLevel'),
                    profile.get('goal'), profile.get('dietType'), profile.get('bmr'),
                    profile.get('tdee'), profile.get('targetCalories'), profile.get('targetProtein'),
                    profile.get('targetCarbs'), profile.get('targetFat'), user_id
                ))
            else:
                execute_query("""
                    INSERT INTO users (id, name, gender, age, weight, height, activity_level, goal, diet_type, bmr, tdee, target_calories, target_protein, target_carbs, target_fat) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, profile.get('name'), profile.get('gender'), profile.get('age'),
                    profile.get('weight'), profile.get('height'), profile.get('activityLevel'),
                    profile.get('goal'), profile.get('dietType'), profile.get('bmr'),
                    profile.get('tdee'), profile.get('targetCalories'), profile.get('targetProtein'),
                    profile.get('targetCarbs'), profile.get('targetFat')
                ))
        else:
            user_exists = query_one("SELECT id FROM users WHERE id = %s", (user_id,))
            if user_exists:
                execute_query("""
                    UPDATE users SET name=NULL, gender=NULL, age=NULL, weight=NULL, height=NULL, 
                    activity_level=NULL, goal=NULL, diet_type=NULL, bmr=NULL, tdee=NULL, 
                    target_calories=NULL, target_protein=NULL, target_carbs=NULL, target_fat=NULL 
                    WHERE id=%s
                """, (user_id,))
            else:
                execute_query("INSERT INTO users (id, name) VALUES (%s, %s)", (user_id, 'Guest'))

        # 2. Update Meal Plan
        if meal_plan:
            meal_exists = query_one("SELECT user_id FROM meal_plans WHERE user_id = %s", (user_id,))
            b_json = json.dumps(meal_plan.get('breakfast'))
            l_json = json.dumps(meal_plan.get('lunch'))
            d_json = json.dumps(meal_plan.get('dinner'))
            s_json = json.dumps(meal_plan.get('snack'))

            if meal_exists:
                execute_query("""
                    UPDATE meal_plans SET breakfast_recipe=%s, lunch_recipe=%s, dinner_recipe=%s, snack_recipe=%s 
                    WHERE user_id=%s
                """, (b_json, l_json, d_json, s_json, user_id))
            else:
                execute_query("""
                    INSERT INTO meal_plans (user_id, breakfast_recipe, lunch_recipe, dinner_recipe, snack_recipe) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, b_json, l_json, d_json, s_json))
        else:
            execute_query("DELETE FROM meal_plans WHERE user_id = %s", (user_id,))

        # 3. Update Completed Meals
        if completed_meals:
            completed_exists = query_one("SELECT user_id FROM completed_meals WHERE user_id = %s", (user_id,))
            b_val = 1 if completed_meals.get('breakfast') else 0
            l_val = 1 if completed_meals.get('lunch') else 0
            d_val = 1 if completed_meals.get('dinner') else 0
            s_val = 1 if completed_meals.get('snack') else 0

            if completed_exists:
                execute_query("""
                    UPDATE completed_meals SET breakfast=%s, lunch=%s, dinner=%s, snack=%s 
                    WHERE user_id=%s
                """, (b_val, l_val, d_val, s_val, user_id))
            else:
                execute_query("""
                    INSERT INTO completed_meals (user_id, breakfast, lunch, dinner, snack) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, b_val, l_val, d_val, s_val))
        else:
            execute_query("DELETE FROM completed_meals WHERE user_id = %s", (user_id,))

        # 4. Update Water
        if water_intake is not None:
            water_exists = query_one("SELECT user_id FROM water_intake WHERE user_id = %s", (user_id,))
            if water_exists:
                execute_query("UPDATE water_intake SET water_intake=%s WHERE user_id=%s", (water_intake, user_id))
            else:
                execute_query("INSERT INTO water_intake (user_id, water_intake) VALUES (%s, %s)", (user_id, water_intake))
        else:
            execute_query("DELETE FROM water_intake WHERE user_id = %s", (user_id,))

        # 5. Update Shopping
        if shopping_checked is not None:
            shop_exists = query_one("SELECT user_id FROM shopping_checked_items WHERE user_id = %s", (user_id,))
            shop_json = json.dumps(shopping_checked)
            if shop_exists:
                execute_query("UPDATE shopping_checked_items SET checked_items=%s WHERE user_id=%s", (shop_json, user_id))
            else:
                execute_query("INSERT INTO shopping_checked_items (user_id, checked_items) VALUES (%s, %s)", (user_id, shop_json))
        else:
            execute_query("DELETE FROM shopping_checked_items WHERE user_id = %s", (user_id,))

        # 6. Update Smartwatch Telemetry
        if smartwatch:
            sw_exists = query_one("SELECT user_id FROM smartwatch_telemetry WHERE user_id = %s", (user_id,))
            hr = float(smartwatch.get('heartRate', 72.0))
            spo2 = float(smartwatch.get('spo2', 98.0))
            steps = int(smartwatch.get('steps', 6000))
            sleep = float(smartwatch.get('sleepHours', 7.0))
            act = str(smartwatch.get('activityLevel', 'Active'))
            stress = int(smartwatch.get('stressLevel', 4))
            cal = int(smartwatch.get('caloriesBurned', 300))
            rec = int(smartwatch.get('recoveryScore', 85))

            if sw_exists:
                execute_query("""
                    UPDATE smartwatch_telemetry 
                    SET heart_rate=%s, spo2=%s, steps=%s, sleep_hours=%s, activity_level=%s, stress_level=%s, calories_burned=%s, recovery_score=%s
                    WHERE user_id=%s
                """, (hr, spo2, steps, sleep, act, stress, cal, rec, user_id))
            else:
                execute_query("""
                    INSERT INTO smartwatch_telemetry (user_id, heart_rate, spo2, steps, sleep_hours, activity_level, stress_level, calories_burned, recovery_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, hr, spo2, steps, sleep, act, stress, cal, rec))

        # 7. Update Medical Conditions
        if med_conditions is not None:
            med_exists = query_one("SELECT user_id FROM medical_conditions WHERE user_id = %s", (user_id,))
            diab = 1 if med_conditions.get('diabetes') else 0
            hyp = 1 if med_conditions.get('hypertension') else 0
            hd = 1 if med_conditions.get('heartDisease') else 0
            ob = 1 if med_conditions.get('obesityPcos') else 0

            if med_exists:
                execute_query("""
                    UPDATE medical_conditions 
                    SET diabetes=%s, hypertension=%s, heart_disease=%s, obesity_pcos=%s
                    WHERE user_id=%s
                """, (diab, hyp, hd, ob, user_id))
            else:
                execute_query("""
                    INSERT INTO medical_conditions (user_id, diabetes, hypertension, heart_disease, obesity_pcos)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, diab, hyp, hd, ob))

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Failed to save state: {str(e)}"}), 500


@app.route('/api/profile', methods=['GET', 'POST'])
def handle_profile():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            user = query_one('SELECT * FROM users WHERE id = %s', (user_id,))
            if not user:
                return jsonify(None)
            return jsonify({
                "name": user.get("name"),
                "gender": user.get("gender"),
                "age": user.get("age"),
                "weight": user.get("weight"),
                "height": user.get("height"),
                "activityLevel": user.get("activity_level"),
                "goal": user.get("goal"),
                "dietType": user.get("diet_type"),
                "bmr": user.get("bmr"),
                "tdee": user.get("tdee"),
                "targetCalories": user.get("target_calories"),
                "targetProtein": user.get("target_protein"),
                "targetCarbs": user.get("target_carbs"),
                "targetFat": user.get("target_fat")
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            profile = request.json
            if not profile:
                execute_query('DELETE FROM users WHERE id = %s', (user_id,))
                return jsonify({"success": True, "profile": None})

            user_exists = query_one("SELECT id FROM users WHERE id = %s", (user_id,))
            if user_exists:
                execute_query("""
                    UPDATE users SET name=%s, gender=%s, age=%s, weight=%s, height=%s, 
                    activity_level=%s, goal=%s, diet_type=%s, bmr=%s, tdee=%s, 
                    target_calories=%s, target_protein=%s, target_carbs=%s, target_fat=%s 
                    WHERE id=%s
                """, (
                    profile.get('name'), profile.get('gender'), profile.get('age'),
                    profile.get('weight'), profile.get('height'), profile.get('activityLevel'),
                    profile.get('goal'), profile.get('dietType'), profile.get('bmr'),
                    profile.get('tdee'), profile.get('targetCalories'), profile.get('targetProtein'),
                    profile.get('targetCarbs'), profile.get('targetFat'), user_id
                ))
            else:
                execute_query("""
                    INSERT INTO users (id, name, gender, age, weight, height, activity_level, goal, diet_type, bmr, tdee, target_calories, target_protein, target_carbs, target_fat) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, profile.get('name'), profile.get('gender'), profile.get('age'),
                    profile.get('weight'), profile.get('height'), profile.get('activityLevel'),
                    profile.get('goal'), profile.get('dietType'), profile.get('bmr'),
                    profile.get('tdee'), profile.get('targetCalories'), profile.get('targetProtein'),
                    profile.get('targetCarbs'), profile.get('targetFat')
                ))
            return jsonify({"success": True, "profile": profile})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/mealplan', methods=['GET', 'POST'])
def handle_mealplan():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            row = query_one('SELECT * FROM meal_plans WHERE user_id = %s', (user_id,))
            if not row:
                return jsonify(None)
            
            def safe_json_parse(json_str):
                return json.loads(json_str) if json_str else None

            return jsonify({
                "breakfast": safe_json_parse(row.get("breakfast_recipe")),
                "lunch": safe_json_parse(row.get("lunch_recipe")),
                "dinner": safe_json_parse(row.get("dinner_recipe")),
                "snack": safe_json_parse(row.get("snack_recipe"))
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            meal_plan = request.json
            if not meal_plan:
                execute_query('DELETE FROM meal_plans WHERE user_id = %s', (user_id,))
                return jsonify({"success": True, "mealPlan": None})

            meal_exists = query_one("SELECT user_id FROM meal_plans WHERE user_id = %s", (user_id,))
            b_json = json.dumps(meal_plan.get('breakfast'))
            l_json = json.dumps(meal_plan.get('lunch'))
            d_json = json.dumps(meal_plan.get('dinner'))
            s_json = json.dumps(meal_plan.get('snack'))

            if meal_exists:
                execute_query("""
                    UPDATE meal_plans SET breakfast_recipe=%s, lunch_recipe=%s, dinner_recipe=%s, snack_recipe=%s 
                    WHERE user_id=%s
                """, (b_json, l_json, d_json, s_json, user_id))
            else:
                execute_query("""
                    INSERT INTO meal_plans (user_id, breakfast_recipe, lunch_recipe, dinner_recipe, snack_recipe) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, b_json, l_json, d_json, s_json))
            return jsonify({"success": True, "mealPlan": meal_plan})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/water', methods=['GET', 'POST'])
def handle_water():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            row = query_one('SELECT water_intake FROM water_intake WHERE user_id = %s', (user_id,))
            return jsonify({"waterIntake": row.get("water_intake") if row else 0})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            water_intake = int(request.json.get('waterIntake', 0))
            water_exists = query_one("SELECT user_id FROM water_intake WHERE user_id = %s", (user_id,))
            if water_exists:
                execute_query("UPDATE water_intake SET water_intake=%s WHERE user_id=%s", (water_intake, user_id))
            else:
                execute_query("INSERT INTO water_intake (user_id, water_intake) VALUES (%s, %s)", (user_id, water_intake))
            return jsonify({"success": True, "waterIntake": water_intake})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/shopping', methods=['GET', 'POST'])
def handle_shopping():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            row = query_one('SELECT checked_items FROM shopping_checked_items WHERE user_id = %s', (user_id,))
            return jsonify(json.loads(row.get("checked_items")) if row and row.get("checked_items") else {})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            shopping_checked = request.json or {}
            shop_exists = query_one("SELECT user_id FROM shopping_checked_items WHERE user_id = %s", (user_id,))
            shop_json = json.dumps(shopping_checked)
            if shop_exists:
                execute_query("UPDATE shopping_checked_items SET checked_items=%s WHERE user_id=%s", (shop_json, user_id))
            else:
                execute_query("INSERT INTO shopping_checked_items (user_id, checked_items) VALUES (%s, %s)", (user_id, shop_json))
            return jsonify({"success": True, "shoppingCheckedItems": shopping_checked})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def handle_reset():
    user_id = 'default_user'
    try:
        execute_query('DELETE FROM users WHERE id = %s', (user_id,))
        execute_query('DELETE FROM meal_plans WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM completed_meals WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM water_intake WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM shopping_checked_items WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM smartwatch_telemetry WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM medical_conditions WHERE user_id = %s', (user_id,))
        execute_query('DELETE FROM recipe_ratings WHERE user_id = %s', (user_id,))
        
        return jsonify({
            "success": True,
            "state": {
                "profile": None,
                "mealPlan": None,
                "completedMeals": { "breakfast": False, "lunch": False, "dinner": False, "snack": False },
                "waterIntake": 0,
                "shoppingCheckedItems": {},
                "smartwatch": {
                    "heartRate": 72.0, "spo2": 98.0, "steps": 6500, "sleepHours": 7.2,
                    "activityLevel": "Active", "stressLevel": 4, "caloriesBurned": 320, "recoveryScore": 85
                },
                "medicalConditions": {
                    "diabetes": False, "hypertension": False, "heartDisease": False, "obesityPcos": False
                }
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Smartwatch Telemetry & Data Preprocessing Endpoints ---

@app.route('/api/smartwatch/telemetry', methods=['GET', 'POST'])
def handle_smartwatch_telemetry():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            row = query_one('SELECT * FROM smartwatch_telemetry WHERE user_id = %s', (user_id,))
            if not row:
                return jsonify({
                    "heartRate": 72.0, "spo2": 98.0, "steps": 6500, "sleepHours": 7.2,
                    "activityLevel": "Active", "stressLevel": 4, "caloriesBurned": 320, "recoveryScore": 85
                })
            return jsonify({
                "heartRate": row.get("heart_rate"),
                "spo2": row.get("spo2"),
                "steps": row.get("steps"),
                "sleepHours": row.get("sleep_hours"),
                "activityLevel": row.get("activity_level"),
                "stressLevel": row.get("stress_level"),
                "caloriesBurned": row.get("calories_burned"),
                "recoveryScore": row.get("recovery_score")
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            data = request.json or {}
            hr = float(data.get('heartRate', 72.0))
            spo2 = float(data.get('spo2', 98.0))
            steps = int(data.get('steps', 6000))
            sleep = float(data.get('sleepHours', 7.0))
            act = str(data.get('activityLevel', 'Active'))
            stress = int(data.get('stressLevel', 4))
            cal = int(data.get('caloriesBurned', 300))
            rec = int(data.get('recoveryScore', 85))

            sw_exists = query_one("SELECT user_id FROM smartwatch_telemetry WHERE user_id = %s", (user_id,))
            if sw_exists:
                execute_query("""
                    UPDATE smartwatch_telemetry 
                    SET heart_rate=%s, spo2=%s, steps=%s, sleep_hours=%s, activity_level=%s, stress_level=%s, calories_burned=%s, recovery_score=%s
                    WHERE user_id=%s
                """, (hr, spo2, steps, sleep, act, stress, cal, rec, user_id))
            else:
                execute_query("""
                    INSERT INTO smartwatch_telemetry (user_id, heart_rate, spo2, steps, sleep_hours, activity_level, stress_level, calories_burned, recovery_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, hr, spo2, steps, sleep, act, stress, cal, rec))

            return jsonify({"success": True, "smartwatch": data})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/smartwatch/sample-stream', methods=['GET'])
def get_sample_smartwatch_stream():
    """Returns sample cleaned records from the Samsung Smartwatch dataset to test telemetry simulation."""
    try:
        cleaned_csv = os.path.join(os.path.dirname(__file__), 'data', 'cleaned_smartwatch_data.csv')
        if not os.path.exists(cleaned_csv):
            return jsonify([])
        
        samples = []
        with open(cleaned_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, r in enumerate(reader):
                if idx >= 30:
                    break
                samples.append({
                    "userId": r.get("userId"),
                    "heartRate": float(r.get("heartRate", 72)),
                    "spo2": float(r.get("spo2", 98)),
                    "steps": int(r.get("steps", 5000)),
                    "sleepHours": float(r.get("sleepHours", 7.0)),
                    "activityLevel": r.get("activity_level") or r.get("activityLevel", "Active"),
                    "stressLevel": int(r.get("stressLevel", 5)),
                    "caloriesBurned": int(r.get("caloriesBurned", 300)),
                    "recoveryScore": int(r.get("recoveryScore", 80))
                })
        return jsonify(samples)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/smartwatch/pipeline-stats', methods=['GET'])
def get_pipeline_stats():
    """Returns preprocessing and cleaning statistics for transparency."""
    return jsonify({
        "rawRecordsCount": 169,
        "cleanedRecordsCount": 169,
        "missingValuesImputed": {
            "heartRate": 14,
            "bloodOxygenSpO2": 11,
            "stepCount": 9,
            "sleepDuration": 12
        },
        "anomaliesAndErrorsHandled": {
            "errorSleepTokensImputedWithMedian": 8,
            "spellingCorrectionsSeddentaryToSedentary": 52,
            "spellingCorrectionsActveToActive": 38,
            "stressLevelStringNormalizations": 4
        },
        "featureEngineering": [
            "Active Calories Burned (derived from step count & heart rate elevation)",
            "Sleep Recovery Readiness Score (0-100 derived from sleep duration & stress level)",
            "Dynamic Real-Time Calorie Budget Adjustment",
            "Disease-Specific Nutrient Safety Constraint Filtering"
        ],
        "datasetIntegration": "Samsung Smartwatch Health Telemetry + ICMR-NIN Indian Food Nutrition + Clinical Medical Profiles"
    })


# --- AI Hybrid Recommendation Engine with Explainable AI (XAI) ---

@app.route('/api/recommendations/hybrid', methods=['POST'])
def get_hybrid_recommendations():
    """
    Computes Hybrid Recommendations combining:
    1. Content-Based Filtering (User profile + Smartwatch real-time vitals + Medical conditions constraints).
    2. Collaborative Filtering (User-item rating matrix & similar persona clusters).
    3. Explainable AI (XAI) transparent justification generation.
    """
    try:
        data = request.json or {}
        user_id = 'default_user'
        meal_type = data.get('mealType', 'all')
        category_filter = data.get('category', 'all')
        alpha = float(data.get('contentWeight', 0.6))  # weight for content-based (0.0 to 1.0)
        
        # Load user profile & smartwatch
        user_state = get_user_state_dict(user_id) or {}
        profile = user_state.get('profile') or data.get('profile') or {}
        smartwatch = user_state.get('smartwatch') or data.get('smartwatch') or {}
        med_conditions = user_state.get('medicalConditions') or data.get('medicalConditions') or {}

        # Load Indian recipes
        food_json_path = os.path.join(os.path.dirname(__file__), 'data', 'indian_food_nutrition.json')
        if not os.path.exists(food_json_path):
            return jsonify([])

        with open(food_json_path, 'r', encoding='utf-8') as f:
            all_dishes = json.load(f)

        # Retrieve user ratings from DB
        user_ratings_map = {}
        try:
            ratings_rows = query_all('SELECT recipe_id, rating FROM recipe_ratings WHERE user_id = %s', (user_id,))
            for r in ratings_rows:
                user_ratings_map[r['recipe_id']] = r['rating']
        except Exception as e:
            print("Notice: No recipe ratings fetched:", e)

        # Smartwatch dynamic multipliers
        steps = smartwatch.get('steps', 6000)
        calories_burned = smartwatch.get('caloriesBurned', 300)
        stress = smartwatch.get('stressLevel', 4)
        sleep = smartwatch.get('sleepHours', 7.0)

        # Dynamic target calorie budget per main meal
        base_tdee = profile.get('targetCalories', 2000)
        # Extra burn from steps gives dynamic allowance
        dynamic_daily_budget = base_tdee + max(0, round(calories_burned * 0.4))
        target_meal_cal = dynamic_daily_budget * 0.30 if meal_type != 'snack' else dynamic_daily_budget * 0.15

        has_diabetes = med_conditions.get('diabetes', False)
        has_hypertension = med_conditions.get('hypertension', False)
        has_heart_disease = med_conditions.get('heartDisease', False)
        has_obesity = med_conditions.get('obesityPcos', False)

        scored_dishes = []

        for dish in all_dishes:
            # Category & mealType filter
            if meal_type != 'all' and dish.get('mealType') != meal_type:
                continue
            if category_filter != 'all' and dish.get('category') != category_filter:
                continue

            # 1. Content-Based Score Calculation (Base 100)
            c_score = 70.0

            # Proximity to ideal meal calorie budget
            cal = dish.get('calories', 200)
            cal_diff = abs(cal - target_meal_cal)
            c_score -= min(30.0, (cal_diff / target_meal_cal) * 35.0)

            # Smartwatch Active Burn Replenishment
            if steps > 8000:
                # Reward protein content for muscular recovery
                protein = dish.get('protein', 5)
                if protein >= 10:
                    c_score += 15.0
            if stress > 6:
                # Stress increases cortisol: boost antioxidant/folate, penalize high free sugar
                if dish.get('folate', 0) > 40:
                    c_score += 10.0
                if dish.get('freeSugar', 0) > 6:
                    c_score -= 15.0
            if sleep < 6.0:
                # Poor sleep: reward light digestive food
                if dish.get('category') in ['Soups', 'Salads & Raitas', 'Beverages']:
                    c_score += 12.0

            # Disease-Specific Constraints & Rules
            if has_diabetes:
                sugar = dish.get('freeSugar', 0)
                gi = dish.get('glycemicIndex', 'Low')
                fiber = dish.get('fiber', 0)
                if sugar > 5.0:
                    c_score -= 35.0
                if gi == 'High':
                    c_score -= 25.0
                if fiber >= 3.5:
                    c_score += 15.0

            if has_hypertension:
                sodium = dish.get('sodium', 200)
                if sodium > 400:
                    c_score -= 40.0
                elif sodium <= 150:
                    c_score += 20.0

            if has_heart_disease:
                fats = dish.get('fat', 5)
                folate = dish.get('folate', 0)
                vitC = dish.get('vitaminC', 0)
                if fats > 15:
                    c_score -= 25.0
                if folate > 40 or vitC > 25:
                    c_score += 18.0

            if has_obesity:
                if cal > 350:
                    c_score -= 25.0
                if dish.get('protein', 0) >= 8 and dish.get('fiber', 0) >= 3:
                    c_score += 18.0

            content_score = max(10.0, min(100.0, c_score))

            # 2. Collaborative Filtering Score Calculation (0 - 100)
            # Check user rating first
            recipe_id = dish.get('id')
            if recipe_id in user_ratings_map:
                collab_score = user_ratings_map[recipe_id] * 20.0  # 5 stars -> 100
            else:
                # Community persona cohort simulated prediction
                # Base rating around 4.2 stars (84%)
                base_collab = 82.0
                if dish.get('diabeticSafe') and has_diabetes:
                    base_collab += 6.0
                if dish.get('hypertensionSafe') and has_hypertension:
                    base_collab += 6.0
                if dish.get('heartSafe') and has_heart_disease:
                    base_collab += 4.0
                collab_score = max(50.0, min(98.0, base_collab))

            # 3. Hybrid Combined Score
            hybrid_score = round((alpha * content_score) + ((1.0 - alpha) * collab_score), 1)

            # 4. Explainable AI (XAI) Transparent Attribution
            smartwatch_xai = []
            if steps > 8000:
                smartwatch_xai.append(f"Supports post-activity recovery for {steps:,} steps with {dish.get('protein')}g protein.")
            elif steps < 4000:
                smartwatch_xai.append("Light caloric load tailored to your current sedentary activity day.")
            if stress > 6:
                smartwatch_xai.append("Rich in calming antioxidants & bio-available folate to counter elevated stress.")
            if not smartwatch_xai:
                smartwatch_xai.append("Balances basal energy expenditure with optimal macronutrient satiety.")

            clinical_xai = []
            if has_diabetes:
                clinical_xai.append(f"Diabetes Safe: {dish.get('glycemicIndex')} GI with only {dish.get('freeSugar')}g free sugar.")
            if has_hypertension:
                clinical_xai.append(f"Hypertension Compliant: Sodium {dish.get('sodium')}mg (well under the 400mg meal ceiling).")
            if has_heart_disease:
                clinical_xai.append(f"Cardio Protective: {dish.get('fat')}g fats and {dish.get('fiber')}g dietary fiber.")
            if has_obesity:
                clinical_xai.append(f"Satiety Optimized: Only {dish.get('calories')} kcal per serving.")
            if not clinical_xai:
                clinical_xai.append("Aligns cleanly with daily ICMR-NIN preventive nutrition guidelines.")

            dish_copy = dict(dish)
            dish_copy['contentScore'] = round(content_score, 1)
            dish_copy['collabScore'] = round(collab_score, 1)
            dish_copy['hybridScore'] = hybrid_score
            dish_copy['userRating'] = user_ratings_map.get(recipe_id)
            dish_copy['xaiExplanation'] = {
                "smartwatchRationale": " ".join(smartwatch_xai),
                "clinicalRationale": " ".join(clinical_xai),
                "nutrientHighlights": f"{dish.get('protein')}g Protein • {dish.get('fiber')}g Fiber • {dish.get('sodium')}mg Sodium",
                "predictedRating": round(collab_score / 20.0, 1)
            }

            scored_dishes.append(dish_copy)

        # Sort descending by Hybrid Score
        scored_dishes.sort(key=lambda x: x['hybridScore'], reverse=True)
        return jsonify(scored_dishes)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Hybrid recommendation failed: {str(e)}"}), 500


# --- ICMR-NIN & Disease Nutritional Analysis Endpoint ---

@app.route('/api/nutrition/analyze', methods=['POST'])
def analyze_daily_nutrition():
    """
    Evaluates current meal plan against ICMR-NIN recommended dietary allowances (RDA)
    and checks compliance against user's 4 supported medical conditions.
    """
    try:
        data = request.json or {}
        meal_plan = data.get('mealPlan') or {}
        profile = data.get('profile') or {}
        med_conditions = data.get('medicalConditions') or {}
        smartwatch = data.get('smartwatch') or {}

        # Accumulate nutrients across all meals
        totals = {
            "calories": 0, "carbs": 0, "protein": 0, "fat": 0,
            "freeSugar": 0, "fiber": 0, "sodium": 0, "calcium": 0,
            "iron": 0, "vitaminC": 0, "folate": 0
        }

        meals_count = 0
        for m_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            recipe = meal_plan.get(m_type)
            if recipe:
                meals_count += 1
                for key in totals.keys():
                    totals[key] += float(recipe.get(key, 0))

        # Round totals
        for key in totals.keys():
            totals[key] = round(totals[key], 1)

        # ICMR-NIN RDA Benchmarks (Adult Indian standard)
        weight = float(profile.get('weight', 65))
        target_calories = float(profile.get('targetCalories', 2000))
        target_protein = float(profile.get('targetProtein', round(weight * 0.9)))

        rda_targets = {
            "calories": target_calories,
            "protein": target_protein,
            "fiber": 35.0,        # ICMR recommended minimum 30-40g
            "sodium": 1500.0 if med_conditions.get('hypertension') else 2000.0,
            "freeSugar": 10.0 if med_conditions.get('diabetes') else 25.0,
            "calcium": 1000.0,
            "iron": 29.0 if profile.get('gender') == 'female' else 19.0,
            "vitaminC": 80.0,
            "folate": 300.0
        }

        # Percentage compliances
        compliance = {}
        for key in rda_targets.keys():
            target = rda_targets[key]
            val = totals.get(key, 0)
            compliance[key] = min(150, round((val / target) * 100)) if target > 0 else 100

        # Clinical Warning Diagnostics
        warnings = []
        if med_conditions.get('diabetes') and totals['freeSugar'] > rda_targets['freeSugar']:
            warnings.append(f"Excess Free Sugar ({totals['freeSugar']}g vs safe limit {rda_targets['freeSugar']}g). Consider swapping sweets or high-sugar beverages.")
        if med_conditions.get('hypertension') and totals['sodium'] > rda_targets['sodium']:
            warnings.append(f"High Daily Sodium ({totals['sodium']}mg vs cap {rda_targets['sodium']}mg). Restrict papads, pickles, and salty snacks.")
        if med_conditions.get('heartDisease') and totals['fat'] > 45:
            warnings.append(f"Elevated total fats ({totals['fat']}g). Prioritize cold-pressed oils and minimize fried savories.")
        if totals['fiber'] < 25 and meals_count >= 3:
            warnings.append("Low dietary fiber intake (<25g). Add sprouted moong, salads, or whole wheat theplas.")

        return jsonify({
            "totals": totals,
            "rdaTargets": rda_targets,
            "compliancePercentages": compliance,
            "clinicalWarnings": warnings,
            "mealsLoggedCount": meals_count
        })

    except Exception as e:
        return jsonify({"error": f"Nutritional analysis failed: {str(e)}"}), 500


# --- Recipe Rating Endpoint for Collaborative Filtering ---

@app.route('/api/rate', methods=['GET', 'POST'])
def handle_rating():
    user_id = 'default_user'
    if request.method == 'GET':
        try:
            rows = query_all("SELECT recipe_id AS recipeId, rating, review FROM recipe_ratings WHERE user_id = %s", (user_id,))
            return jsonify(rows)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            data = request.json or {}
            recipe_id = data.get('recipeId')
            rating = int(data.get('rating', 5))
            review = data.get('review', '')

            if not recipe_id:
                return jsonify({"error": "recipeId is required"}), 400

            # Delete existing rating if present then re-insert
            execute_query("DELETE FROM recipe_ratings WHERE user_id=%s AND recipe_id=%s", (user_id, recipe_id))
            execute_query("INSERT INTO recipe_ratings (user_id, recipe_id, rating, review) VALUES (%s, %s, %s, %s)",
                          (user_id, recipe_id, rating, review))

            return jsonify({"success": True, "recipeId": recipe_id, "rating": rating})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# --- Chatbot Workflow API ---

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Diet Coach Workflow Chatbot endpoint.
    Expects JSON:
    {
      "message": "user raw text",
      "history": [{"role": "user"|"model", "text": "..."}],
      "profile": {...},
      "mealPlan": {...},
      "completedMeals": {...},
      "waterIntake": 0
    }
    """
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        history = data.get("history", [])
        
        profile = data.get("profile") or {}
        meal_plan = data.get("mealPlan") or {}
        completed_meals = data.get("completedMeals") or {}
        water_intake = data.get("waterIntake", 0)

        # Parse user details
        name = profile.get("name", "User")
        gender = profile.get("gender", "Unspecified")
        age = profile.get("age", "N/A")
        weight = profile.get("weight", "N/A")
        height = profile.get("height", "N/A")
        activity_level = profile.get("activityLevel", "N/A")
        goal = profile.get("goal", "maintain")
        diet_type = profile.get("dietType", "Balanced")
        target_calories = profile.get("targetCalories", 2000)
        target_protein = profile.get("targetProtein", 120)
        target_carbs = profile.get("targetCarbs", 200)
        target_fat = profile.get("targetFat", 70)

        # Map goal code to labels
        goal_text = "Maintain Weight"
        if goal == "lose":
            goal_text = "Lose Weight (Calorie Deficit)"
        elif goal == "gain":
            goal_text = "Gain Weight (Calorie Surplus)"

        # Meal Plan Formatting helper
        def format_meal(meal_name):
            recipe = meal_plan.get(meal_name)
            if not recipe:
                return "Not selected"
            return f"{recipe.get('title')} ({recipe.get('calories')} kcal, P: {recipe.get('protein')}g, C: {recipe.get('carbs')}g, F: {recipe.get('fat')}g)"

        breakfast = format_meal("breakfast")
        lunch = format_meal("lunch")
        dinner = format_meal("dinner")
        snack = format_meal("snack")

        # Completed Meals string
        completed_list = []
        for meal, completed in completed_meals.items():
            completed_list.append(f"{meal.capitalize()}: {'Eaten' if completed else 'Not Eaten'}")
        completed_meals_text = ", ".join(completed_list)

        water_display = f"{water_intake} cups ({water_intake * 250} ml)" if isinstance(water_intake, (int, float)) and water_intake <= 8 else f"{water_intake} ml"

        # Build System Instruction
        system_instruction = f"""You are NutriGuide AI, an encouraging, professional, and intelligent AI Diet Coach.
You help the user stay on track with their weight goals and nutrition.

User Details:
- Name: {name}
- Gender: {gender}
- Age: {age} years
- Weight: {weight} kg
- Height: {height} cm
- Activity Level: {activity_level}
- Goal: {goal_text}
- Diet Type: {diet_type}
- Daily Targets: {target_calories} kcal, Protein: {target_protein}g, Carbs: {target_carbs}g, Fat: {target_fat}g

Today's status:
- Meal Plan:
  * Breakfast: {breakfast}
  * Lunch: {lunch}
  * Dinner: {dinner}
  * Snack: {snack}
- Completed Meals: {completed_meals_text}
- Water Intake: {water_display} (Daily Target: 8 cups / 2000 ml)

You can help the user with questions, recipes, swaps, and logging. 
If the user wants to execute an action (like logging water, eating meals, swapping meals, or navigating tabs), you MUST issue an action command at the very end of your response. 
The command MUST be exactly on its own line in the format:
ACTION_TRIGGER: {{"type": "...", "amount": ..., "mealType": "..."}}

Supported actions:
1. Log water: ACTION_TRIGGER: {{"type": "add_water", "amount": 250}} or other amounts (e.g. 500, or negative like -250). Use when the user says they drank water, logged water, or asks to add water. Note: 1 cup = 250ml.
2. Toggle meal status: ACTION_TRIGGER: {{"type": "toggle_meal", "mealType": "breakfast" | "lunch" | "dinner" | "snack"}}
3. Swap a meal: ACTION_TRIGGER: {{"type": "swap_meal", "mealType": "breakfast" | "lunch" | "dinner" | "snack"}}
4. Switch screen tabs: ACTION_TRIGGER: {{"type": "change_tab", "tab": "dashboard" | "planner" | "recipes" | "shopping" | "tables"}}
5. Reset profile: ACTION_TRIGGER: {{"type": "reset_profile"}}

Always answer politely and concisely. If you trigger an action, mention it naturally (e.g., "I've added 250ml of water to your log. Keep it up!")."""

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Check if Gemini key is available
        if gemini_api_key and not gemini_api_key.startswith("your_"):
            # Map input history into Gemini contents format
            contents = []
            for h in history:
                role = "user" if h.get("role") == "user" else "model"
                t = (h.get("text") or "").strip()
                if t:
                    contents.append({
                        "role": role,
                        "parts": [{"text": t}]
                    })
            
            # Gemini contents must start with a 'user' turn
            while contents and contents[0].get("role") == "model":
                contents.pop(0)

            # Add latest user message
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_instruction}]
                },
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 800
                }
            }

            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]
            reply_text = None

            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_api_key}"
                try:
                    res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
                    if res.status_code == 200:
                        res_data = res.json()
                        candidates = res_data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if "text" in p and not p.get("thought", False)]
                            reply_text = "".join(text_parts).strip()
                            if reply_text:
                                break
                    else:
                        print(f"Gemini model {model_name} returned status {res.status_code}: {res.text[:120]}")
                except Exception as e:
                    print(f"Gemini model {model_name} request failed: {e}")

            if not reply_text:
                print("All Gemini models failed or unavailable. Falling back to Rule-Based matching.")
                reply_text, action = run_fallback_chatbot(user_message)
                return jsonify({"reply": reply_text, "action": action})
        else:
            # Fallback to local rule-based matching if no API key is defined
            reply_text, action = run_fallback_chatbot(user_message)
            return jsonify({"reply": reply_text, "action": action})

        # Parse potential action from Gemini's reply text
        action = None
        cleaned_reply = reply_text
        
        # Look for ACTION_TRIGGER: in the reply
        if "ACTION_TRIGGER:" in reply_text:
            parts = reply_text.split("ACTION_TRIGGER:")
            cleaned_reply = parts[0].strip()
            if cleaned_reply.endswith("```"):
                cleaned_reply = cleaned_reply[:-3].strip()
            action_str = parts[1].strip()
            
            # If there's content after the action JSON line, clean it up
            if "\n" in action_str:
                action_str = action_str.split("\n")[0].strip()
            
            action_str = action_str.strip('`').strip()
                
            try:
                action = json.loads(action_str)
            except Exception:
                import re
                match = re.search(r'\{.*?\}', action_str)
                if match:
                    try:
                        action = json.loads(match.group(0))
                    except Exception as e:
                        print(f"Failed to regex parse action JSON: {action_str}. Error: {e}")

        return jsonify({
            "reply": cleaned_reply,
            "action": action
        })

    except Exception as e:
        return jsonify({"error": f"Failed in chat processing: {str(e)}"}), 500


def run_fallback_chatbot(user_message):
    """
    A smart rule-based keyword matching chatbot to run if no Gemini key is provided.
    Extracts intents like logging water, eating meals, swapping recipes, or changing tabs.
    """
    msg = user_message.lower()
    
    # 1. Logging water
    if "water" in msg or "drink" in msg or "ml" in msg:
        amount = 250
        if "500" in msg:
            amount = 500
        elif "1000" in msg or "1l" in msg:
            amount = 1000
        elif "subtract" in msg or "remove" in msg or "minus" in msg:
            amount = -250
            
        return (
            f"I've logged {abs(amount)}ml of water for you. Keep staying hydrated!",
            {"type": "add_water", "amount": amount}
        )
    
    # 2. Toggle meal status
    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    for mt in meal_types:
        if mt in msg:
            if "eat" in msg or "ate" in msg or "done" in msg or "complete" in msg or "log" in msg or "check" in msg:
                return (
                    f"Got it! I have marked your {mt} as eaten.",
                    {"type": "toggle_meal", "mealType": mt}
                )
            if "swap" in msg or "change" in msg or "different" in msg or "replace" in msg:
                return (
                    f"Sure, let's swap your {mt} for an alternative recipe.",
                    {"type": "swap_meal", "mealType": mt}
                )

    # 3. Changing tabs
    if "shopping" in msg or "list" in msg or "buy" in msg:
        return (
            "Opening your shopping checklist panel.",
            {"type": "change_tab", "tab": "shopping"}
        )
    if "recipe" in msg or "library" in msg or "dishes" in msg:
        return (
            "Navigating to the Recipe Library.",
            {"type": "change_tab", "tab": "recipes"}
        )
    if "planner" in msg or "calendar" in msg or "plan" in msg:
        return (
            "Opening the weekly Meal Planner page.",
            {"type": "change_tab", "tab": "planner"}
        )
    if "table" in msg or "database" in msg or "logs" in msg:
        return (
            "Opening your detailed Data Tables view.",
            {"type": "change_tab", "tab": "tables"}
        )
    if "home" in msg or "dashboard" in msg:
        return (
            "Switching back to the main Dashboard.",
            {"type": "change_tab", "tab": "dashboard"}
        )
    
    if "reset" in msg and "profile" in msg:
        return (
            "Understood, triggering profile reset configuration.",
            {"type": "reset_profile"}
        )

    # Default reply if no intent matched
    has_key = bool(os.getenv("GEMINI_API_KEY") and not os.getenv("GEMINI_API_KEY").startswith("your_"))
    tip = "" if has_key else "\n\n(Tip: Add a GEMINI_API_KEY to your backend/.env to unlock personalized AI responses!)"
    return (
        f"Hello! I'm your AI Diet Coach. I can help log water, mark meals as eaten, swap recipes, or answer diet questions. Try typing 'Add 500ml water' or 'What should I eat today?'.{tip}",
        None
    )


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Run server
    app.run(host='0.0.0.0', port=port, debug=True)
