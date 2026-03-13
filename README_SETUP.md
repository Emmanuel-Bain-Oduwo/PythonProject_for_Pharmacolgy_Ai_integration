# 🏥 PharmaCliniq Pro — Hospital Pharmacology System
## Complete Setup & Deployment Guide (FIXED v3.1)

---

## 🐛 Bugs Fixed in This Version

| Bug | Location | Fix |
|-----|----------|-----|
| `genetics` table column mismatch | `database_schema.py` | Renamed `gene` → `gene_name`, added `gene_symbol`, `chromosome`, `enzyme_function`, `phenotype_consequences`, `key_variants` |
| `patient_profiles` missing columns | `database_schema.py` | Added `name`, `blood_group`, `diagnoses` |
| `emergency_protocols` column mismatch | `database_schema.py` | Renamed `protocol_name` → `name` |
| `patient_medications` wrong key columns | `database_schema.py` | `patient_code`→`patient_id`, added `medication_id`, `dose_prescribed`, `is_active` |
| `patient_lab_results` wrong key columns | `database_schema.py` | `patient_code`→`patient_id`, added `ordered_by` |
| `diet_plans` missing columns | `database_schema.py` | Added `patient_id`, `plan_json` |
| Backend API `/patients` SQL errors | `Backend_API.py` | Fixed all INSERT/SELECT to use correct column names |
| Frontend genetics page crash | `app_main_pharma.py` | Fixed to use `gene_name`, `gene_symbol`, `phenotype_consequences` |
| Frontend emergency protocols crash | `app_main_pharma.py` | Fixed to use `name` column |

---

## ⚡ Quick Start (5 minutes)

```bash
# 1. Clone / copy all files to one folder
mkdir pharma_system && cd pharma_system
# Copy all .py files here

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your DeepSeek API key
cp .env.template .env
# Open .env and add: DEEPSEEK_API_KEY=your_key_here

# 5. ONE command to set everything up
python startup.py

# 6. Launch the app
streamlit run app_main_pharma.py
```

The app will open at **http://localhost:8501** 🎉

---

## 🌐 Deploy for 100+ Testers (Free — Streamlit Community Cloud)

This is the easiest way to share with 100 people to test:

### Step 1 — Push to GitHub
```bash
# Create a new GitHub repo (public or private)
git init
git add .
git commit -m "PharmaCliniq Pro v3.1"
git remote add origin https://github.com/YOUR_USERNAME/pharmacliniq
git push -u origin main
```

### Step 2 — Deploy on Streamlit Cloud
1. Go to **https://share.streamlit.io**
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository and `app_main_pharma.py` as main file
5. Add secrets (click "Advanced settings" → "Secrets"):
   ```toml
   DEEPSEEK_API_KEY = "your_deepseek_api_key"
   ```
6. Click **Deploy** — done! 🚀

Your app gets a public URL like `https://pharmacliniq.streamlit.app`
Share that URL with your 100 testers.

### ⚠️ Important: Database in Cloud
Streamlit Cloud has an ephemeral filesystem. To persist data across restarts,
add this at the top of `app_main_pharma.py`:
```python
import subprocess, sys
# Auto-init DB on first run
if not os.path.exists("identifier.sqlite"):
    subprocess.run([sys.executable, "startup.py"])
```

---

## 🖥️ Alternative: Deploy on Railway (Free tier, persistent DB)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway new
railway add
railway up
```

Set environment variable `DEEPSEEK_API_KEY` in Railway dashboard.

---

## 🔧 Start Backend API (Optional — for advanced use)

```bash
# In a separate terminal
uvicorn Backend_API:app --reload --port 8000

# API docs at: http://localhost:8000/docs
```

---

## 🗂️ File Reference

| File | Purpose | Status |
|------|---------|--------|
| `database_schema.py` | Creates 15 SQLite tables | ✅ FIXED |
| `Backend_API.py` | FastAPI REST API | ✅ FIXED |
| `app_main_pharma.py` | Streamlit UI | ✅ FIXED + ENHANCED |
| `startup.py` | Auto-init DB + models | ✅ NEW |
| `db_config.py` | DB path config | ✅ Unchanged |
| `deepseek_config.py` | DeepSeek AI config | ✅ Unchanged |
| `clinical_engine.py` | Clinical calculators | ✅ Unchanged |
| `ml_models.py` | ML models | ✅ Unchanged |
| `seed_medications_100.py` | Seed 100 drugs | ✅ Unchanged |
| `seed_ayurveda_50.py` | Seed 50 Ayurveda items | ✅ Unchanged |
| `seed_genetics.py` | Seed 13 PGx genes | ✅ Unchanged |
| `seed_lab_ranges.py` | Seed 40+ lab ranges | ✅ Unchanged |
| `requirements.txt` | Python dependencies | ✅ NEW |
| `.env.template` | Env variable template | ✅ NEW |

---

## 🤖 New Features in v3.1

### 1. Patient Guide Tab (Drug Database)
Every medication now has a **🧑 Patient Guide** tab that:
- Explains the drug in plain English (no medical jargon)
- Explains **each condition** the drug treats simply
- Uses analogies and emojis to be accessible
- Powered by DeepSeek AI on-demand

### 2. Enhanced AI Chat Page
- Dedicated full-page AI chat with role-aware presets
- **Quick drug lookup** sidebar (Clinical info / Patient-friendly / Side effects)
- Streaming responses (text appears as AI generates it)
- Conversation history with clear button
- Works for ALL roles — especially great for patients

---

## 🎭 Role-Specific Features

| Role | Key Features |
|------|-------------|
| 👨‍⚕️ Doctor | Interactions, dose calculations, risk scores, AI consult |
| 💊 Pharmacist | Full monographs, TDM, interactions, substitutions |
| 👩‍⚕️ Nurse | Emergency protocols, lab interpretation, admin guides |
| 🧑 Patient | Patient Guide (plain-English meds), Ayurveda, Diet planner, AI Chat |
| 📚 Medical Student | Full DB, PGx, calculators, AI teaching |

---

## 🔧 Troubleshooting

```bash
# DB not found?
python startup.py  # re-initialises everything

# Genetics/Emergency pages crashing? (OLD schema)
# Delete identifier.sqlite and re-run startup.py
rm identifier.sqlite
python startup.py

# DeepSeek not responding?
python -c "from deepseek_config import deepseek_chat_sync; print(deepseek_chat_sync([{'role':'user','content':'hello'}]))"

# Port 8000 busy?
uvicorn Backend_API:app --reload --port 8001

# ML models missing?
python ml_models.py
```

---

## ⚠️ Clinical Disclaimer
This system is for **educational and clinical decision support** only.
It is NOT a substitute for professional medical judgment.
Always verify with current guidelines and consult qualified clinicians.
