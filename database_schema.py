"""
database_schema.py VERSION v3.1
==========================================
"""

import sqlite3, logging
from db_config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def create_all_tables():
    conn = get_conn(); cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, generic_name TEXT, brand_names TEXT,
        category TEXT, drug_class TEXT, medication_type TEXT DEFAULT 'Rx',
        atc_code TEXT, dea_schedule TEXT,
        mechanism_action TEXT, mechanism_simple TEXT,
        absorption TEXT, bioavailability TEXT, protein_binding TEXT,
        volume_distribution TEXT, half_life TEXT, time_to_peak TEXT,
        metabolism TEXT, metabolites TEXT, excretion TEXT, pk_json TEXT,
        onset_action TEXT, duration_action TEXT, receptor_target TEXT,
        therapeutic_index TEXT, pd_json TEXT,
        dose_adult TEXT, dose_adult_loading TEXT, dose_adult_maintenance TEXT,
        dose_pediatric TEXT, dose_geriatric TEXT, dose_renal_adj TEXT,
        dose_hepatic_adj TEXT, dose_obesity_adj TEXT, max_daily_dose TEXT,
        route_admin TEXT, frequency TEXT, duration_therapy TEXT, food_timing TEXT,
        indications TEXT,
        conditions_treated TEXT,
        contraindications TEXT, warnings TEXT, black_box_warning TEXT,
        adverse_effects_common TEXT, adverse_effects_serious TEXT,
        toxicity_symptoms TEXT, antidote TEXT,
        drug_interactions_list TEXT, food_interactions TEXT, lab_interactions TEXT,
        monitoring_params TEXT, lab_tests_required TEXT, tdm_info TEXT,
        pregnancy_category TEXT, lactation_safety TEXT,
        pediatric_notes TEXT, geriatric_notes TEXT, renal_notes TEXT, hepatic_notes TEXT,
        cyp_substrate TEXT, cyp_inhibitor TEXT, cyp_inducer TEXT,
        gene_variants TEXT, pharmacogenomic_notes TEXT,
        diet_interactions TEXT, nutritional_effects TEXT,
        who_essential INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS ayurveda_diet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, local_names TEXT,
        entry_type TEXT NOT NULL, category TEXT,
        botanical_name TEXT, plant_family TEXT, parts_used TEXT,
        rasa TEXT, virya TEXT, vipaka TEXT, dosha_effect TEXT,
        traditional_uses TEXT, modern_evidence TEXT,
        indications TEXT, contraindications TEXT,
        calories_per_100g REAL, protein_g REAL, carbs_g REAL,
        fat_g REAL, fiber_g REAL, key_nutrients TEXT,
        drug_interactions TEXT, interactions_detail TEXT,
        dose_adult TEXT, dose_pediatric TEXT, dose_geriatric TEXT,
        preparation TEXT, safety_notes TEXT,
        glycemic_index TEXT, diet_category TEXT, health_benefits TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS drug_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug_a TEXT NOT NULL, drug_b TEXT NOT NULL,
        severity TEXT NOT NULL, interaction_type TEXT,
        mechanism TEXT, clinical_effect TEXT, effect TEXT,
        management TEXT, evidence_level TEXT, onset TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(drug_a, drug_b)
    )""")

    # FIXED: column names now match seed_genetics.py and frontend exactly
    cur.execute("""CREATE TABLE IF NOT EXISTS genetics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gene_name TEXT NOT NULL,
        gene_symbol TEXT,
        chromosome TEXT,
        enzyme_function TEXT,
        population_frequency TEXT,
        affected_drugs TEXT,
        key_variants TEXT,
        phenotype_consequences TEXT,
        clinical_actions TEXT,
        testing_indications TEXT,
        fda_labels_with_pgx TEXT,
        evidence_level TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS lab_reference_ranges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL, abbreviation TEXT, category TEXT,
        min_adult_male REAL, max_adult_male REAL,
        min_adult_female REAL, max_adult_female REAL,
        min_child REAL, max_child REAL,
        min_neonate REAL, max_neonate REAL,
        unit TEXT, critical_low REAL, critical_high REAL,
        clinical_meaning TEXT, drug_effects TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # FIXED: added name, blood_group, diagnoses columns
    cur.execute("""CREATE TABLE IF NOT EXISTS patient_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_code TEXT UNIQUE,
        name TEXT,
        age INTEGER, weight_kg REAL, height_cm REAL,
        gender TEXT, blood_group TEXT,
        bmi REAL, bsa_m2 REAL, serum_creatinine REAL,
        crcl_ml_min REAL, egfr REAL, albumin REAL,
        total_bilirubin REAL, ast REAL, alt REAL,
        cyp2d6_phenotype TEXT, cyp3a4_phenotype TEXT,
        cyp2c19_phenotype TEXT, cyp2c9_phenotype TEXT,
        diagnoses TEXT,
        conditions TEXT,
        allergies TEXT,
        hba1c REAL, tsh REAL, testosterone REAL, estrogen REAL,
        is_pregnant INTEGER DEFAULT 0, is_breastfeeding INTEGER DEFAULT 0,
        is_smoker INTEGER DEFAULT 0, is_alcoholic INTEGER DEFAULT 0,
        role TEXT DEFAULT 'patient', notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    # FIXED: patient_code→patient_id, added medication_id, dose_prescribed, is_active
    cur.execute("""CREATE TABLE IF NOT EXISTS patient_medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        medication_id INTEGER,
        medication_name TEXT,
        dose_prescribed TEXT,
        dose TEXT,
        frequency TEXT, route TEXT,
        start_date TEXT, end_date TEXT,
        prescribed_by TEXT, indication TEXT,
        is_active INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # FIXED: patient_code→patient_id, added ordered_by
    cur.execute("""CREATE TABLE IF NOT EXISTS patient_lab_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        value REAL, unit TEXT, test_date TEXT,
        status TEXT, notes TEXT,
        ordered_by TEXT, entered_by TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # FIXED: patient_code→patient_id, added plan_json
    cur.execute("""CREATE TABLE IF NOT EXISTS diet_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        plan_name TEXT, plan_type TEXT,
        plan_json TEXT,
        calories_target INTEGER, protein_target REAL,
        carbs_target REAL, fat_target REAL, fiber_target REAL,
        breakfast TEXT, lunch TEXT, dinner TEXT, snacks TEXT,
        foods_to_avoid TEXT, created_by_ai INTEGER DEFAULT 1,
        notes TEXT, created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS diet_tracker (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, log_date TEXT, meal_type TEXT,
        food_name TEXT, quantity_g REAL, calories REAL,
        protein_g REAL, carbs_g REAL, fat_g REAL, fiber_g REAL,
        notes TEXT, created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS ml_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, model_name TEXT,
        prediction TEXT, probability REAL, confidence TEXT,
        features_used TEXT, recommendation TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS clinical_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, note_type TEXT,
        note_text TEXT, author_role TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # FIXED: renamed protocol_name → name
    cur.execute("""CREATE TABLE IF NOT EXISTS emergency_protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT, indication TEXT,
        steps TEXT, medications TEXT, drugs TEXT, doses TEXT,
        notes TEXT, reference TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Added plain_english column for patient education
    cur.execute("""CREATE TABLE IF NOT EXISTS conditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icd10 TEXT, description TEXT,
        plain_english TEXT,
        first_line_drugs TEXT, second_line_drugs TEXT,
        monitoring TEXT, patient_education TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_role TEXT, action TEXT, table_name TEXT,
        record_id TEXT, detail TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit(); conn.close()
    log.info("✅  All 15 tables created / verified in %s", DB_PATH)


if __name__ == "__main__":
    create_all_tables()
