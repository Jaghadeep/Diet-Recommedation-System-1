import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import mysql from 'mysql2/promise';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Resolve directory name in ES Module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Database connection
let db;

// Helper to get a single row
async function dbGet(sql, params) {
  const paramArray = Array.isArray(params) ? params : (params !== undefined ? [params] : []);
  const [rows] = await db.query(sql, paramArray);
  return rows[0];
}

async function initDb() {
  try {
    const dbName = process.env.DB_NAME || 'nutriguide';
    
    // Connect to MySQL server first without selecting a database
    const connection = await mysql.createConnection({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT, 10) || 3306,
      user: process.env.DB_USER || 'root',
      password: process.env.DB_PASSWORD || ''
    });

    // Create database if not exists and select it
    await connection.query(`CREATE DATABASE IF NOT EXISTS \`${dbName}\``);
    await connection.query(`USE \`${dbName}\``);

    db = connection;
    console.log(`Connected to MySQL database: ${dbName}`);

    // 1. Create Users profile table
    await db.query(`
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
    `);

    // 2. Create Meal Plans table
    await db.query(`
      CREATE TABLE IF NOT EXISTS meal_plans (
        user_id VARCHAR(255) PRIMARY KEY,
        breakfast_recipe TEXT,
        lunch_recipe TEXT,
        dinner_recipe TEXT,
        snack_recipe TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 3. Create Completed Meals status table
    await db.query(`
      CREATE TABLE IF NOT EXISTS completed_meals (
        user_id VARCHAR(255) PRIMARY KEY,
        breakfast INT DEFAULT 0,
        lunch INT DEFAULT 0,
        dinner INT DEFAULT 0,
        snack INT DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 4. Create Water Intake table
    await db.query(`
      CREATE TABLE IF NOT EXISTS water_intake (
        user_id VARCHAR(255) PRIMARY KEY,
        water_intake INT DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 5. Create Shopping Checked Items table
    await db.query(`
      CREATE TABLE IF NOT EXISTS shopping_checked_items (
        user_id VARCHAR(255) PRIMARY KEY,
        checked_items TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    console.log('Database tables verified/created successfully.');
  } catch (error) {
    console.error('Error initializing database:', error);
    process.exit(1);
  }
}

// Start database initialization before starting server
await initDb();

// --- Endpoints ---

// Get complete state
app.get('/api/state', async (req, res) => {
  try {
    const user = await dbGet('SELECT * FROM users WHERE id = ?', 'default_user');
    if (!user) {
      return res.json({
        profile: null,
        mealPlan: null,
        completedMeals: { breakfast: false, lunch: false, dinner: false, snack: false },
        waterIntake: 0,
        shoppingCheckedItems: {}
      });
    }

    const mealPlanRow = await dbGet('SELECT * FROM meal_plans WHERE user_id = ?', 'default_user');
    const completedMealsRow = await dbGet('SELECT * FROM completed_meals WHERE user_id = ?', 'default_user');
    const waterIntakeRow = await dbGet('SELECT * FROM water_intake WHERE user_id = ?', 'default_user');
    const shoppingRow = await dbGet('SELECT * FROM shopping_checked_items WHERE user_id = ?', 'default_user');

    res.json({
      profile: {
        name: user.name,
        gender: user.gender,
        age: user.age,
        weight: user.weight,
        height: user.height,
        activityLevel: user.activity_level,
        goal: user.goal,
        dietType: user.diet_type,
        bmr: user.bmr,
        tdee: user.tdee,
        targetCalories: user.target_calories,
        targetProtein: user.target_protein,
        targetCarbs: user.target_carbs,
        targetFat: user.target_fat
      },
      mealPlan: mealPlanRow ? {
        breakfast: JSON.parse(mealPlanRow.breakfast_recipe || 'null'),
        lunch: JSON.parse(mealPlanRow.lunch_recipe || 'null'),
        dinner: JSON.parse(mealPlanRow.dinner_recipe || 'null'),
        snack: JSON.parse(mealPlanRow.snack_recipe || 'null')
      } : null,
      completedMeals: completedMealsRow ? {
        breakfast: !!completedMealsRow.breakfast,
        lunch: !!completedMealsRow.lunch,
        dinner: !!completedMealsRow.dinner,
        snack: !!completedMealsRow.snack
      } : { breakfast: false, lunch: false, dinner: false, snack: false },
      waterIntake: waterIntakeRow ? waterIntakeRow.water_intake : 0,
      shoppingCheckedItems: shoppingRow ? JSON.parse(shoppingRow.checked_items || '{}') : {}
    });
  } catch (err) {
    console.error('Error fetching state:', err);
    res.status(500).json({ error: 'Failed to fetch database state' });
  }
});

// Update complete state (bulk update)
app.post('/api/state', async (req, res) => {
  try {
    const { profile, mealPlan, completedMeals, waterIntake, shoppingCheckedItems } = req.body;
    
    if (profile) {
      await db.query(
        `INSERT INTO users (id, name, gender, age, weight, height, activity_level, goal, diet_type, bmr, tdee, target_calories, target_protein, target_carbs, target_fat) 
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE 
           name = VALUES(name), gender = VALUES(gender), age = VALUES(age), weight = VALUES(weight), height = VALUES(height), 
           activity_level = VALUES(activity_level), goal = VALUES(goal), diet_type = VALUES(diet_type), bmr = VALUES(bmr), 
           tdee = VALUES(tdee), target_calories = VALUES(target_calories), target_protein = VALUES(target_protein), 
           target_carbs = VALUES(target_carbs), target_fat = VALUES(target_fat)`, 
        ['default_user', profile.name, profile.gender, profile.age, profile.weight, profile.height, profile.activityLevel, profile.goal, profile.dietType, profile.bmr, profile.tdee, profile.targetCalories, profile.targetProtein, profile.targetCarbs, profile.targetFat]
      );
    } else {
      await db.query('DELETE FROM users WHERE id = ?', ['default_user']);
    }

    if (mealPlan) {
      await db.query(
        `INSERT INTO meal_plans (user_id, breakfast_recipe, lunch_recipe, dinner_recipe, snack_recipe) 
         VALUES (?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE 
           breakfast_recipe = VALUES(breakfast_recipe), lunch_recipe = VALUES(lunch_recipe), 
           dinner_recipe = VALUES(dinner_recipe), snack_recipe = VALUES(snack_recipe)`,
        [
          'default_user',
          JSON.stringify(mealPlan.breakfast || null),
          JSON.stringify(mealPlan.lunch || null),
          JSON.stringify(mealPlan.dinner || null),
          JSON.stringify(mealPlan.snack || null)
        ]
      );
    } else {
      await db.query('DELETE FROM meal_plans WHERE user_id = ?', ['default_user']);
    }

    if (completedMeals) {
      await db.query(
        `INSERT INTO completed_meals (user_id, breakfast, lunch, dinner, snack) 
         VALUES (?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE 
           breakfast = VALUES(breakfast), lunch = VALUES(lunch), dinner = VALUES(dinner), snack = VALUES(snack)`,
        [
          'default_user',
          completedMeals.breakfast ? 1 : 0,
          completedMeals.lunch ? 1 : 0,
          completedMeals.dinner ? 1 : 0,
          completedMeals.snack ? 1 : 0
        ]
      );
    } else {
      await db.query('DELETE FROM completed_meals WHERE user_id = ?', ['default_user']);
    }

    if (waterIntake !== undefined) {
      await db.query(
        `INSERT INTO water_intake (user_id, water_intake) 
         VALUES (?, ?)
         ON DUPLICATE KEY UPDATE 
           water_intake = VALUES(water_intake)`,
        ['default_user', waterIntake]
      );
    } else {
      await db.query('DELETE FROM water_intake WHERE user_id = ?', ['default_user']);
    }

    if (shoppingCheckedItems) {
      await db.query(
        `INSERT INTO shopping_checked_items (user_id, checked_items) 
         VALUES (?, ?)
         ON DUPLICATE KEY UPDATE 
           checked_items = VALUES(checked_items)`,
        ['default_user', JSON.stringify(shoppingCheckedItems)]
      );
    } else {
      await db.query('DELETE FROM shopping_checked_items WHERE user_id = ?', ['default_user']);
    }

    res.json({ success: true });
  } catch (err) {
    console.error('Error updating state:', err);
    res.status(500).json({ error: 'Failed to update database state' });
  }
});

// Get individual sections

// Get Profile
app.get('/api/profile', async (req, res) => {
  try {
    const user = await dbGet('SELECT * FROM users WHERE id = ?', 'default_user');
    if (!user) return res.json(null);
    res.json({
      name: user.name,
      gender: user.gender,
      age: user.age,
      weight: user.weight,
      height: user.height,
      activityLevel: user.activity_level,
      goal: user.goal,
      dietType: user.diet_type,
      bmr: user.bmr,
      tdee: user.tdee,
      targetCalories: user.target_calories,
      targetProtein: user.target_protein,
      targetCarbs: user.target_carbs,
      targetFat: user.target_fat
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Profile
app.post('/api/profile', async (req, res) => {
  try {
    const profile = req.body;
    if (!profile) {
      await db.query('DELETE FROM users WHERE id = ?', ['default_user']);
      return res.json({ success: true, profile: null });
    }
    await db.query(
      `INSERT INTO users (id, name, gender, age, weight, height, activity_level, goal, diet_type, bmr, tdee, target_calories, target_protein, target_carbs, target_fat) 
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON DUPLICATE KEY UPDATE 
         name = VALUES(name), gender = VALUES(gender), age = VALUES(age), weight = VALUES(weight), height = VALUES(height), 
         activity_level = VALUES(activity_level), goal = VALUES(goal), diet_type = VALUES(diet_type), bmr = VALUES(bmr), 
         tdee = VALUES(tdee), target_calories = VALUES(target_calories), target_protein = VALUES(target_protein), 
         target_carbs = VALUES(target_carbs), target_fat = VALUES(target_fat)`, 
      ['default_user', profile.name, profile.gender, profile.age, profile.weight, profile.height, profile.activityLevel, profile.goal, profile.dietType, profile.bmr, profile.tdee, profile.targetCalories, profile.targetProtein, profile.targetCarbs, profile.targetFat]
    );
    res.json({ success: true, profile });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get Meal Plan
app.get('/api/mealplan', async (req, res) => {
  try {
    const row = await dbGet('SELECT * FROM meal_plans WHERE user_id = ?', 'default_user');
    if (!row) return res.json(null);
    res.json({
      breakfast: JSON.parse(row.breakfast_recipe || 'null'),
      lunch: JSON.parse(row.lunch_recipe || 'null'),
      dinner: JSON.parse(row.dinner_recipe || 'null'),
      snack: JSON.parse(row.snack_recipe || 'null')
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Meal Plan
app.post('/api/mealplan', async (req, res) => {
  try {
    const mealPlan = req.body;
    if (!mealPlan) {
      await db.query('DELETE FROM meal_plans WHERE user_id = ?', ['default_user']);
      return res.json({ success: true, mealPlan: null });
    }
    await db.query(
      `INSERT INTO meal_plans (user_id, breakfast_recipe, lunch_recipe, dinner_recipe, snack_recipe) 
       VALUES (?, ?, ?, ?, ?)
       ON DUPLICATE KEY UPDATE 
         breakfast_recipe = VALUES(breakfast_recipe), lunch_recipe = VALUES(lunch_recipe), 
         dinner_recipe = VALUES(dinner_recipe), snack_recipe = VALUES(snack_recipe)`,
      [
        'default_user',
        JSON.stringify(mealPlan.breakfast || null),
        JSON.stringify(mealPlan.lunch || null),
        JSON.stringify(mealPlan.dinner || null),
        JSON.stringify(mealPlan.snack || null)
      ]
    );
    res.json({ success: true, mealPlan });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get Water
app.get('/api/water', async (req, res) => {
  try {
    const row = await dbGet('SELECT water_intake FROM water_intake WHERE user_id = ?', 'default_user');
    res.json({ waterIntake: row ? row.water_intake : 0 });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Water
app.post('/api/water', async (req, res) => {
  try {
    const waterIntake = parseInt(req.body.waterIntake, 10) || 0;
    await db.query(
      `INSERT INTO water_intake (user_id, water_intake) 
       VALUES (?, ?)
       ON DUPLICATE KEY UPDATE 
         water_intake = VALUES(water_intake)`,
      ['default_user', waterIntake]
    );
    res.json({ success: true, waterIntake });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get Shopping
app.get('/api/shopping', async (req, res) => {
  try {
    const row = await dbGet('SELECT checked_items FROM shopping_checked_items WHERE user_id = ?', 'default_user');
    res.json(row ? JSON.parse(row.checked_items || '{}') : {});
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Shopping
app.post('/api/shopping', async (req, res) => {
  try {
    const shoppingCheckedItems = req.body;
    await db.query(
      `INSERT INTO shopping_checked_items (user_id, checked_items) 
       VALUES (?, ?)
       ON DUPLICATE KEY UPDATE 
         checked_items = VALUES(checked_items)`,
      ['default_user', JSON.stringify(shoppingCheckedItems || {})]
    );
    res.json({ success: true, shoppingCheckedItems: shoppingCheckedItems });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Reset database endpoint
app.post('/api/reset', async (req, res) => {
  try {
    await db.query('DELETE FROM users WHERE id = ?', ['default_user']);
    await db.query('DELETE FROM meal_plans WHERE user_id = ?', ['default_user']);
    await db.query('DELETE FROM completed_meals WHERE user_id = ?', ['default_user']);
    await db.query('DELETE FROM water_intake WHERE user_id = ?', ['default_user']);
    await db.query('DELETE FROM shopping_checked_items WHERE user_id = ?', ['default_user']);
    
    res.json({
      success: true,
      state: {
        profile: null,
        mealPlan: null,
        completedMeals: { breakfast: false, lunch: false, dinner: false, snack: false },
        waterIntake: 0,
        shoppingCheckedItems: {}
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
