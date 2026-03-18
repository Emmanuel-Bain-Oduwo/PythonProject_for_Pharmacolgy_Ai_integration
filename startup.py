"""
startup.py — Auto-initialise database on first run.
Run this ONCE before starting the app, or call it at the top of app_main_pharma.py.

Usage:
  python startup.py

What it does:
  1. Creates all 15 database tables (if not already created)
  2. Seeds medications, ayurveda, genetics, lab ranges (if tables are empty)
  3. Trains ML models (if model files don't exist)
"""
import os, logging, subprocess, sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def run(script):
    script_path = BASE_DIR / script
    log.info(f"Running {script_path.name}...")
    if not script_path.exists():
        log.error("❌ Missing script: %s", script_path)
        return False

    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        log.error("Error in %s: %s", script_path.name, result.stderr[:500])
    else:
        log.info("✅ %s completed", script_path.name)
    return result.returncode == 0

def main():
    log.info("=== PharmaCliniq Pro — Startup Initialiser ===")
    failed = []

    # 1. Create tables
    from database_schema import create_all_tables
    create_all_tables()

    # 2. Check if tables are empty and seed if needed
    from db_config import DB_PATH
    import sqlite3
    conn = sqlite3.connect(DB_PATH)

    if conn.execute("SELECT COUNT(*) FROM medications").fetchone()[0] == 0:
        log.info("Medications table empty — seeding...")
        if not run("seed_medications_100.py"):
            failed.append("seed_medications_100.py")
    else:
        log.info("✅ Medications already seeded")

    if conn.execute("SELECT COUNT(*) FROM ayurveda_diet").fetchone()[0] == 0:
        log.info("Ayurveda table empty — seeding...")
        if not run("seed_ayurveda_50.py"):
            failed.append("seed_ayurveda_50.py")
    else:
        log.info("✅ Ayurveda already seeded")

    if conn.execute("SELECT COUNT(*) FROM genetics").fetchone()[0] == 0:
        log.info("Genetics table empty — seeding...")
        if not run("seed_genetics.py"):
            failed.append("seed_genetics.py")
    else:
        log.info("✅ Genetics already seeded")

    if conn.execute("SELECT COUNT(*) FROM lab_reference_ranges").fetchone()[0] == 0:
        log.info("Lab ranges table empty — seeding...")
        if not run("seed_lab_ranges.py"):
            failed.append("seed_lab_ranges.py")
    else:
        log.info("✅ Lab ranges already seeded")

    if conn.execute("SELECT COUNT(*) FROM emergency_protocols").fetchone()[0] == 0:
        log.info("Emergency protocols table empty — seeding...")
        if not run("seed_emergency_protocols.py"):
            failed.append("seed_emergency_protocols.py")
    else:
        log.info("✅ Emergency protocols already seeded")

    conn.close()

    # 3. Train ML models if missing
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    if not os.path.exists(os.path.join(models_dir, "patient_risk_rf.pkl")):
        log.info("ML models missing — training...")
        if not run("ml_models.py"):
            failed.append("ml_models.py")
    else:
        log.info("✅ ML models already trained")

    if failed:
        log.error("=== ⚠️ Startup completed with failures: %s ===", ", ".join(failed))
    else:
        log.info("=== ✅ Startup complete! System is ready. ===")

    log.info("Next steps:")
    log.info("  1. streamlit run app_main_pharma.py")
    log.info("  2. (Optional) uvicorn Backend_API:app --reload --port 8000")

if __name__ == "__main__":
    main()
