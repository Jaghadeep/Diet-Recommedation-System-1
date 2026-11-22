# 🥗 NutriGuide: Intelligent Precision Nutrition & Clinical Lifestyle Management Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![React](https://img.shields.io/badge/Frontend-React_19_%2B_Vite_8-61dafb.svg)](https://react.dev/)
[![Flask](https://img.shields.io/badge/Backend-Python_3.13_Flask-000000.svg)](https://flask.palletsprojects.com/)
[![AI Engine](https://img.shields.io/badge/AI_Engine-Google_Gemini_3_Agent-4285f4.svg)](https://ai.google.dev/)
[![Standards](https://img.shields.io/badge/Clinical_Standards-ICMR--NIN_RDA_2024-orange.svg)](https://www.nin.res.in/)
[![Mobile](https://img.shields.io/badge/Mobile-Android_APK_Capacitor-34a853.svg)](https://capacitorjs.com/)

> **NutriGuide** is a full-stack, cross-platform precision health and clinical nutrition management platform. It bridges real-time IoT wearable telemetry (Samsung Galaxy Watch), Indian clinical dietary guidelines (ICMR-NIN RDA standards), a hybrid Explainable AI (XAI) recommendation engine, and an autonomous **Google Gemini 3** agentic Diet Coach that directly controls the application UI.

---

## 📑 Complete Software Documentation

The full software engineering report (Problem Statement, SRS, SDD, ERD, API specs, Implementation, and Testing Matrix) is available in two formats:
- 📄 **[PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)** (Full GitHub-flavored Markdown specification)
- 🌐 **[PROJECT_DOCUMENTATION.html](./PROJECT_DOCUMENTATION.html)** (Interactive report with 1-click **PDF Export / Print**)

---

## ✨ Key Features

### 🤖 1. Autonomous Agentic AI Diet Coach (Google Gemini 3)
- Real-time conversational coach with live context injection (your live profile, calorie budget, daily meal plan, hydration level, and meal completions).
- **Agentic UI Control**: Emits structured action triggers (`ACTION_TRIGGER: {"type": ...}`) that automatically update your hydration meter, check off eaten meals, swap recipes, or switch screens without manual clicking.
- Built-in multi-model fallback (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`) with deterministic offline NLP fallback.

### ⌚ 2. Wearable IoT Telemetry Stream & Preprocessing
- Automated data cleaning pipeline (`backend/data_pipeline.py`) that sanitizes raw smartwatch data, imputes corrupted readings using statistical medians, and filters noise.
- Dynamically derives **Active Calories Burned** and an algorithmic **Sleep Recovery Score (0-100)** to adapt daily caloric and hydration needs.

### 🧠 3. Hybrid Recommendation Engine with Explainable AI (XAI)
- Combines **Content-Based Filtering** (nutritional distance & clinical disease constraints) with **Collaborative Filtering** (peer rating matrices).
- **Explainable AI (XAI)**: Generates human-readable clinical justifications for every recommended dish explaining *why* it matches your biometric state.

### 🍛 4. Indian Nutritional Database & ICMR-NIN Clinical RDA Compliance
- Curated database of authentic Indian recipes with full macronutrient and micronutrient profiles (Sodium, Free Sugar, Fiber, Calcium, Iron, Vitamin C, Folate).
- Clinical safety guardrails for **Type-2 Diabetes**, **Hypertension**, **Cardiovascular Disease**, and **PCOS**.

### 🗓️ 5. Weekly Meal Planner & Dynamic Recipe Swapping
- 4-slot daily plan: Breakfast, Lunch, Dinner, and Snack.
- 1-click recipe swapping that matches nutritional equivalency.

### 🛒 6. Smart Categorized Shopping Checklist
- Aggregates ingredients across all planned meals and organizes them into categorized aisles (*Produce 🥦, Proteins 🥩, Dairy 🥛, Pantry 🧂*).

### 📱 7. Cross-Platform Web & Mobile Native APK
- Responsive desktop and mobile glassmorphism UI built with **React 19** and **Vite 8**.
- Native Android build powered by **Capacitor 8** (`NutriGuide.apk` included in root).

---

## 🏛️ System Architecture

```text
+--------------------------------------------------------------------------+
|                  Presentation Layer: React 19 + Vite + Capacitor         |
|  [Glassmorphic Dashboard]  [Meal Planner]  [Shopping List]  [AI Coach UI]|
+--------------------------------------------------------------------------+
                                     │  ▲
              REST API Calls (JSON)  │  │  State Updates & Action Triggers
                                     ▼  │
+--------------------------------------------------------------------------+
|                     Application Layer: Python 3.13 Flask                 |
|  • /api/state: Unified synchronization & persistence                     |
|  • /api/chat: Prompt orchestration & agentic action parsing              |
|  • /api/recommendations/hybrid: Content + Collaborative XAI recommender   |
|  • /api/smartwatch: IoT streaming & recovery metrics                     |
|  • /api/nutrition/analyze: ICMR-NIN RDA benchmark validation            |
+--------------------------------------------------------------------------+
                     │                                  │
         SQL Queries │                      HTTP API    │
                     ▼                                  ▼
+------------------------------------+   +---------------------------------+
|         Persistence Layer          |   |       Intelligence Layer        |
|  Primary: MySQL 8.0                |   |  Google Gemini 3 (flash-lite)   |
|  Auto-Fallback: SQLite database.db |   |  • Multimodal intent detection  |
|  Client Mirror: localStorage       |   |  • Clinical nutrition reasoning |
+------------------------------------+   +---------------------------------+
```

---

## 🗄️ Database Schema

The database utilizes 8 normalized relational tables:
1. `users` — Anthropometrics, BMR, TDEE, fitness goals, and macro targets.
2. `meal_plans` — Active Breakfast, Lunch, Dinner, and Snack recipes.
3. `completed_meals` — Daily completion status (Boolean 0/1 per slot).
4. `water_intake` — Hydration counter (tracked in 250ml cup increments).
5. `shopping_checked_items` — Interactive grocery checklist states.
6. `smartwatch_telemetry` — Live heart rate, SpO2, steps, sleep, stress, and recovery score.
7. `medical_conditions` — Diagnostic flags for Diabetes, Hypertension, CVD, and PCOS.
8. `recipe_ratings` — User ratings (1-5 stars) and reviews for collaborative filtering.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js** (v18+ or v22 LTS) & npm
- **Python** (v3.10 to v3.13)
- **MySQL Server** (Optional: the backend automatically initializes and falls back to SQLite `database.db` if MySQL is offline)

---

### 2. Backend Setup (Flask API)

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure your environment variables in backend/.env
# (Copy from backend/.env.example)
cp .env.example .env

# Start the Flask API server
python app.py
```
> The backend will initialize the database and run on `http://localhost:5000`.

---

### 3. Frontend Setup (React + Vite)

```bash
# Navigate to React directory
cd React

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
> The frontend application will launch on `http://localhost:5173`.

---

### 4. Running Mobile Android App

A pre-built Android package is available in the repository root:
- 📦 **[`NutriGuide.apk`](./NutriGuide.apk)** (Direct installation for Android devices)

To build from source using Capacitor:
```bash
cd React
npm run build
npx cap sync
npx cap open android
```

---

## 🛠️ Technology Stack

| Domain | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite 8, Lucide React, Modern CSS Glassmorphism |
| **Mobile** | Capacitor 8 Native Android Bridge, Android 14+ |
| **Backend** | Python 3.13, Flask 3.x, Werkzeug, python-dotenv |
| **Database** | MySQL 8.0 (Primary) / SQLite 3 (Automatic Fallback) |
| **AI / LLM** | Google Gemini 3 (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) |
| **IoT Data** | Custom Data Cleaning Pipeline (Statistical Median Imputation) |
| **Clinical Standard** | ICMR-NIN (National Institute of Nutrition, India) RDA 2024 |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
