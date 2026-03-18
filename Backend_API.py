"""
Backend_API.py VERSION v3.1
=======================================
Run: uvicorn Backend_API:app --reload --port 8000
"""

import json, sqlite3, logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db_config import DB_PATH
from clinical_engine import ClinicalCalculator, DoseAdjustmentEngine, SafetyChecker, PatientProfile, Gender
from ml_models import PatientRiskModel, DrugInteractionPredictor, DietRecommendationEngine, VisualisationEngine, train_all_models
from lab_interpreter import LabInterpreter
from deepseek_config import deepseek_chat
from seed_emergency_protocols import seed_emergency_protocols

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="Hospital Pharmacology System API",
    description="Clinical decision support — medications, interactions, ML, genetics, diet",
    version="3.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def row_to_dict(row) -> dict:
    if row is None: return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and v.startswith(("[", "{")):
            try: d[k] = json.loads(v)
            except: pass
    return d


class PatientCreate(BaseModel):
    name: str; age: int; gender: str; weight_kg: float; height_cm: float
    blood_group: Optional[str] = None; diagnoses: Optional[List[str]] = []
    allergies: Optional[List[str]] = []; serum_creatinine: Optional[float] = None
    hba1c: Optional[float] = None; cyp2d6_phenotype: Optional[str] = None
    cyp2c19_phenotype: Optional[str] = None

class LabResult(BaseModel):
    test_name: str; value: float; unit: str
    test_date: Optional[str] = None; ordered_by: Optional[str] = None

class InteractionCheckRequest(BaseModel):
    drug_names: List[str] = Field(..., min_items=2)

class RiskPredictRequest(BaseModel):
    age: int; weight_kg: float; egfr: float; albumin: float
    med_count: int; comorbidity_count: int
    hba1c: Optional[float] = 6.0; crp: Optional[float] = 5.0
    wbc: Optional[float] = 7.0; heart_rate: Optional[float] = 75; sbp: Optional[float] = 120
    is_elderly: Optional[int] = 0; has_renal_impairment: Optional[int] = 0
    has_diabetes: Optional[int] = 0; has_cardiac: Optional[int] = 0
    is_pm_cyp2d6: Optional[int] = 0; is_pm_cyp2c19: Optional[int] = 0

class DietPlanRequest(BaseModel):
    patient_id: Optional[int] = None; age: int; gender: str
    weight_kg: float; height_cm: float; activity_level: str = "moderate"
    conditions: List[str] = []; goal: str = "maintain"

class ChatRequest(BaseModel):
    message: str; role: Optional[str] = "doctor"
    patient_context: Optional[Dict] = None
    conversation_history: Optional[List[Dict]] = []

class DoseCalcRequest(BaseModel):
    drug_name: str; patient_age: int; patient_weight_kg: float
    patient_height_cm: float; patient_gender: str
    serum_creatinine: Optional[float] = None; albumin: Optional[float] = None


@app.get("/", tags=["Root"])
def root():
    return {"system": "Hospital Pharmacology System API v3.1", "status": "✅ Running", "docs": "/docs"}


@app.get("/medications", tags=["Medications"])
def list_medications(search: Optional[str] = None, category: Optional[str] = None,
                     who_essential: Optional[int] = None, limit: int = 50, offset: int = 0):
    conn = get_db()
    sql = """SELECT id, name, generic_name, category, drug_class, medication_type,
                    route_admin, dose_adult, pregnancy_category, who_essential,
                    indications, conditions_treated, mechanism_simple
             FROM medications WHERE 1=1"""
    params = []
    if search:
        sql += " AND (name LIKE ? OR generic_name LIKE ? OR drug_class LIKE ? OR category LIKE ?)"
        s = f"%{search}%"; params += [s, s, s, s]
    if category:
        sql += " AND category = ?"; params.append(category)
    if who_essential is not None:
        sql += " AND who_essential = ?"; params.append(who_essential)
    count_sql = sql.replace(
        "SELECT id, name, generic_name, category, drug_class, medication_type,\n                    route_admin, dose_adult, pregnancy_category, who_essential,\n                    indications, conditions_treated, mechanism_simple",
        "SELECT COUNT(*)"
    )
    total = conn.execute(count_sql, params).fetchone()[0]
    sql += " ORDER BY category, name LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"total": total, "limit": limit, "offset": offset, "data": [row_to_dict(r) for r in rows]}


@app.get("/medications/categories", tags=["Medications"])
def medication_categories():
    conn = get_db()
    rows = conn.execute("SELECT category, COUNT(*) as count FROM medications GROUP BY category ORDER BY category").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/medications/{med_id}", tags=["Medications"])
def get_medication(med_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM medications WHERE id=?", (med_id,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404, f"Medication {med_id} not found")
    return row_to_dict(row)


@app.get("/medications/search/{name}", tags=["Medications"])
def search_medication_by_name(name: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM medications WHERE name LIKE ? OR generic_name LIKE ? LIMIT 10",
                        (f"%{name}%", f"%{name}%")).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.post("/interactions/check", tags=["Interactions"])
def check_interactions(req: InteractionCheckRequest):
    conn = get_db(); results = []
    for i in range(len(req.drug_names)):
        for j in range(i + 1, len(req.drug_names)):
            a, b = req.drug_names[i], req.drug_names[j]
            row = conn.execute(
                "SELECT * FROM drug_interactions WHERE (drug_a LIKE ? AND drug_b LIKE ?) OR (drug_a LIKE ? AND drug_b LIKE ?)",
                (f"%{a}%", f"%{b}%", f"%{b}%", f"%{a}%")
            ).fetchone()
            results.append(
                row_to_dict(row)
                if row else {
                    "drug_a": a,
                    "drug_b": b,
                    "severity": "Needs clinical review",
                    "mechanism": "No direct pair record available; assess using pharmacology and patient factors.",
                    "management": "Use cautious co-prescribing, monitor closely, and review alternatives if needed.",
                }
            )
    qt_flags = SafetyChecker.check_qt_risk(req.drug_names)
    beers = SafetyChecker.check_beers_criteria(req.drug_names, age=70)
    conn.close()
    return {"drugs_checked": req.drug_names,
            "interactions_found": len([r for r in results if r.get("severity") not in {"Unknown", "Needs clinical review"}]),
            "interactions": results, "qt_prolongation_alert": qt_flags, "beers_criteria_flags": beers}


@app.get("/interactions/list", tags=["Interactions"])
def list_interactions(severity: Optional[str] = None, limit: int = 50):
    conn = get_db()
    sql = "SELECT * FROM drug_interactions WHERE 1=1"
    params = []
    if severity: sql += " AND severity = ?"; params.append(severity)
    sql += " ORDER BY severity DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


# ─── PATIENTS (all column fixes here) ────────────────────────────────────────
@app.post("/patients", tags=["Patients"], status_code=201)
def create_patient(p: PatientCreate):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        """INSERT INTO patient_profiles
           (name, age, gender, weight_kg, height_cm, blood_group,
            diagnoses, allergies, serum_creatinine, hba1c,
            cyp2d6_phenotype, cyp2c19_phenotype, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (p.name, p.age, p.gender, p.weight_kg, p.height_cm, p.blood_group,
         json.dumps(p.diagnoses), json.dumps(p.allergies),
         p.serum_creatinine, p.hba1c, p.cyp2d6_phenotype, p.cyp2c19_phenotype,
         datetime.now().isoformat())
    )
    pid = cur.lastrowid; conn.commit(); conn.close()
    return {"id": pid, "message": "Patient created", **p.dict()}


@app.get("/patients/{patient_id}", tags=["Patients"])
def get_patient(patient_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM patient_profiles WHERE id=?", (patient_id,)).fetchone()
    if not row: conn.close(); raise HTTPException(404, "Patient not found")
    patient = row_to_dict(row)
    meds = conn.execute(
        """SELECT pm.*, m.name as med_name, m.drug_class
           FROM patient_medications pm
           LEFT JOIN medications m ON pm.medication_id = m.id
           WHERE pm.patient_id=? AND pm.is_active=1""", (patient_id,)
    ).fetchall()
    patient["current_medications"] = [row_to_dict(m) for m in meds]
    labs = conn.execute(
        "SELECT test_name, value, unit, test_date, status FROM patient_lab_results WHERE patient_id=? ORDER BY test_date DESC LIMIT 20",
        (patient_id,)
    ).fetchall()
    patient["recent_labs"] = [dict(l) for l in labs]
    conn.close(); return patient


@app.get("/patients", tags=["Patients"])
def list_patients(search: Optional[str] = None, limit: int = 50):
    conn = get_db()
    sql = "SELECT id, name, age, gender, diagnoses, created_at FROM patient_profiles WHERE 1=1"
    params = []
    if search: sql += " AND (name LIKE ? OR diagnoses LIKE ?)"; s = f"%{search}%"; params += [s, s]
    sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close(); return [row_to_dict(r) for r in rows]


@app.post("/patients/{patient_id}/labs", tags=["Patients"], status_code=201)
def add_lab_result(patient_id: int, lab: LabResult):
    conn = get_db(); cur = conn.cursor()
    if not conn.execute("SELECT id FROM patient_profiles WHERE id=?", (patient_id,)).fetchone():
        conn.close(); raise HTTPException(404, "Patient not found")
    test_date = lab.test_date or datetime.now().isoformat()
    cur.execute(
        "INSERT INTO patient_lab_results (patient_id, test_name, value, unit, test_date, ordered_by) VALUES (?,?,?,?,?,?)",
        (patient_id, lab.test_name, lab.value, lab.unit, test_date, lab.ordered_by)
    )
    result_id = cur.lastrowid
    p_row = conn.execute("SELECT gender, age FROM patient_profiles WHERE id=?", (patient_id,)).fetchone()
    interpreter = LabInterpreter()
    interpretation = interpreter.interpret(lab.test_name, lab.value,
                                           gender=p_row["gender"] if p_row else "male",
                                           age=p_row["age"] if p_row else 40)
    conn.commit(); conn.close()
    return {"id": result_id, "interpretation": interpretation}


@app.post("/patients/{patient_id}/medications", tags=["Patients"], status_code=201)
def add_patient_medication(patient_id: int, medication_id: int, dose: str, frequency: str, start_date: Optional[str] = None):
    conn = get_db()
    if not conn.execute("SELECT id FROM patient_profiles WHERE id=?", (patient_id,)).fetchone():
        conn.close(); raise HTTPException(404, "Patient not found")
    if not conn.execute("SELECT id FROM medications WHERE id=?", (medication_id,)).fetchone():
        conn.close(); raise HTTPException(404, "Medication not found")
    conn.execute(
        "INSERT OR REPLACE INTO patient_medications (patient_id, medication_id, dose_prescribed, frequency, start_date, is_active) VALUES (?,?,?,?,?,1)",
        (patient_id, medication_id, dose, frequency, start_date or datetime.now().date().isoformat())
    )
    conn.commit(); conn.close()
    return {"message": f"Medication {medication_id} added to patient {patient_id}"}


@app.get("/labs/reference-ranges", tags=["Labs"])
def get_reference_ranges(category: Optional[str] = None):
    conn = get_db()
    sql = "SELECT * FROM lab_reference_ranges WHERE 1=1"
    params = []
    if category: sql += " AND category=?"; params.append(category)
    sql += " ORDER BY category, test_name"
    rows = conn.execute(sql, params).fetchall()
    conn.close(); return [row_to_dict(r) for r in rows]


@app.post("/labs/interpret", tags=["Labs"])
def interpret_lab(test_name: str, value: float, gender: str = "male", age: int = 40):
    if not str(test_name).strip():
        raise HTTPException(422, "test_name is required")
    if age < 0:
        raise HTTPException(422, "age must be non-negative")
    return LabInterpreter().interpret(test_name, value, gender, age)


@app.post("/clinical/calculate", tags=["Clinical"])
def run_clinical_calculations(req: DoseCalcRequest):
    gender = Gender.MALE if req.patient_gender.lower() == "male" else Gender.FEMALE
    calc = ClinicalCalculator()
    ibw = calc.ibw_devine(req.patient_height_cm, gender)
    bsa = calc.bsa_mosteller(req.patient_weight_kg, req.patient_height_cm)
    bmi = calc.bmi(req.patient_weight_kg, req.patient_height_cm)
    result = {
        "bmi": round(bmi, 1), "bmi_category": calc.bmi_category(bmi),
        "ibw_kg": round(ibw, 1), "bsa_m2": round(bsa, 2),
        "adjusted_body_weight_kg": round(calc.adjusted_bw(req.patient_weight_kg, ibw), 1),
        "bmr_kcal_day": round(calc.harris_benedict_bmr(req.patient_weight_kg, req.patient_height_cm, req.patient_age, gender)),
    }
    if req.serum_creatinine:
        crcl = calc.crcl_cockcroft_gault(req.patient_age, min(req.patient_weight_kg, ibw), req.serum_creatinine, gender)
        egfr = calc.egfr_ckd_epi(req.patient_age, req.serum_creatinine, gender)
        result.update({"crcl_ml_min": crcl, "egfr_ml_min_1_73m2": egfr,
                       "ckd_stage": calc.ckd_stage(egfr).value,
                       "renal_safety": SafetyChecker.check_renal_safety(req.drug_name, crcl)})
    return result


@app.post("/ml/predict/risk", tags=["ML"])
def predict_patient_risk(req: RiskPredictRequest):
    return PatientRiskModel().predict(req.dict())


@app.post("/ml/diet-plan", tags=["ML"])
def generate_diet_plan(req: DietPlanRequest):
    plan = DietRecommendationEngine().generate_plan(req.dict())
    if req.patient_id:
        conn = get_db()
        conn.execute("INSERT INTO diet_plans (patient_id, plan_json, created_at) VALUES (?,?,?)",
                     (req.patient_id, json.dumps(plan), datetime.now().isoformat()))
        conn.commit(); conn.close()
    return plan


@app.post("/ml/train", tags=["ML"])
def trigger_training(background_tasks: BackgroundTasks):
    background_tasks.add_task(train_all_models)
    return {"message": "ML model training started in background"}


# ─── GENETICS (fixed column names) ───────────────────────────────────────────
@app.get("/genetics", tags=["Genetics"])
def list_genetics():
    conn = get_db()
    rows = conn.execute("SELECT * FROM genetics ORDER BY gene_name").fetchall()
    conn.close(); return [row_to_dict(r) for r in rows]


@app.get("/genetics/{gene}", tags=["Genetics"])
def get_gene_info(gene: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM genetics WHERE gene_name LIKE ? OR gene_symbol LIKE ?",
                        (f"%{gene}%", f"%{gene}%")).fetchall()
    conn.close()
    if not rows: raise HTTPException(404, f"Gene '{gene}' not found")
    return [row_to_dict(r) for r in rows]


@app.post("/genetics/interpret", tags=["Genetics"])
def interpret_genetics(drug: str, gene: str, phenotype: str):
    return {"drug": drug, "gene": gene, "phenotype": phenotype,
            "recommendation": SafetyChecker.genetic_dose_recommendation(drug, phenotype, gene)}


# ─── EMERGENCY (fixed column name) ───────────────────────────────────────────
@app.get("/emergency/protocols", tags=["Emergency"])
def list_emergency_protocols(category: Optional[str] = None):
    conn = get_db()
    sql = "SELECT * FROM emergency_protocols WHERE 1=1"
    params = []
    if category: sql += " AND category=?"; params.append(category)
    sql += " ORDER BY category, name"
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        conn.close()
        seed_emergency_protocols()
        conn = get_db()
        rows = conn.execute(sql, params).fetchall()
    conn.close(); return [row_to_dict(r) for r in rows]


@app.get("/emergency/protocols/{protocol_id}", tags=["Emergency"])
def get_protocol(protocol_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM emergency_protocols WHERE id=?", (protocol_id,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404, "Protocol not found")
    return row_to_dict(row)


@app.get("/ayurveda", tags=["Ayurveda & Diet"])
def list_ayurveda(entry_type: Optional[str] = None, category: Optional[str] = None,
                  search: Optional[str] = None, limit: int = 50):
    conn = get_db()
    sql = "SELECT * FROM ayurveda_diet WHERE 1=1"; params = []
    if entry_type: sql += " AND entry_type=?"; params.append(entry_type)
    if category: sql += " AND category LIKE ?"; params.append(f"%{category}%")
    if search:
        sql += " AND (name LIKE ? OR health_benefits LIKE ? OR traditional_uses LIKE ?)"
        s = f"%{search}%"; params += [s, s, s]
    sql += " ORDER BY entry_type, name LIMIT ?"; params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close(); return [row_to_dict(r) for r in rows]


@app.get("/ayurveda/interactions/check/{drug_name}", tags=["Ayurveda & Diet"])
def check_herb_drug_interactions(drug_name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT name, entry_type, drug_interactions, safety_notes FROM ayurveda_diet WHERE drug_interactions LIKE ?",
        (f"%{drug_name}%",)).fetchall()
    conn.close()
    return {"drug": drug_name, "herb_food_interactions": [row_to_dict(r) for r in rows], "count": len(rows)}


# ─── AI CONSULTATION ─────────────────────────────────────────────────────────
@app.post("/deepseek/chat", tags=["AI Consultation"])
async def ai_consultation(req: ChatRequest):
    system_prompt = f"""You are a world-class clinical pharmacist AI assistant.
User role: {req.role}. Provide evidence-based, clinically accurate pharmacology guidance.
Always include: mechanism, monitoring, interactions, special populations.
End critical safety info with ⚠️. Not a substitute for clinical judgment."""
    if req.patient_context:
        system_prompt += f"\n\nPatient Context: {json.dumps(req.patient_context, indent=2)}"
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(req.conversation_history or [])
    messages.append({"role": "user", "content": req.message})
    try:
        response_text = await deepseek_chat(messages)
        return {"response": response_text, "role": "assistant", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(503, f"AI service unavailable: {str(e)}")


@app.post("/deepseek/explain-for-patient", tags=["AI Consultation"])
async def explain_drug_for_patient(drug_name: str, conditions: Optional[str] = ""):
    """Patient-friendly explanation of a drug and its conditions — no medical jargon"""
    messages = [
        {"role": "system", "content": "You are a friendly pharmacist explaining medicines to patients with no medical background. Use simple everyday language, analogies, and emojis to be approachable."},
        {"role": "user", "content": f"""Explain {drug_name} to a patient with NO medical knowledge:
1. What is this medicine? (very simple terms)
2. What health problems does it treat? (explain each condition simply — what is it, what happens in body, why is it a problem)
3. How does this medicine help? (use an analogy)
4. How to take it? (key points)
5. Important warnings? (simple language)
Associated conditions: {conditions}"""}
    ]
    try:
        response = await deepseek_chat(messages, max_tokens=1500)
        return {"drug": drug_name, "patient_explanation": response}
    except Exception as e:
        raise HTTPException(503, str(e))


@app.post("/deepseek/drug-monograph", tags=["AI Consultation"])
async def generate_drug_monograph(drug_name: str):
    messages = [
        {"role": "system", "content": "You are a clinical pharmacology expert. Generate comprehensive, accurate drug monographs."},
        {"role": "user", "content": f"Complete clinical monograph for {drug_name}: Mechanism, Indications, Dosing, PK, Adverse Effects, Interactions, Monitoring, Pregnancy, Clinical Pearls."}
    ]
    try:
        return {"drug": drug_name, "monograph": await deepseek_chat(messages)}
    except Exception as e:
        raise HTTPException(503, str(e))


@app.get("/analytics/dashboard", tags=["Analytics"])
def get_dashboard_data():
    conn = get_db()
    stats = {
        "total_medications": conn.execute("SELECT COUNT(*) FROM medications").fetchone()[0],
        "who_essential": conn.execute("SELECT COUNT(*) FROM medications WHERE who_essential=1").fetchone()[0],
        "total_interactions": conn.execute("SELECT COUNT(*) FROM drug_interactions").fetchone()[0],
        "contraindicated_interactions": conn.execute("SELECT COUNT(*) FROM drug_interactions WHERE severity='Contraindicated'").fetchone()[0],
        "total_patients": conn.execute("SELECT COUNT(*) FROM patient_profiles").fetchone()[0],
        "total_ayurveda_entries": conn.execute("SELECT COUNT(*) FROM ayurveda_diet").fetchone()[0],
        "lab_reference_ranges": conn.execute("SELECT COUNT(*) FROM lab_reference_ranges").fetchone()[0],
        "medications_by_category": [dict(r) for r in conn.execute("SELECT category, COUNT(*) as count FROM medications GROUP BY category ORDER BY count DESC").fetchall()],
        "interaction_severity_distribution": [dict(r) for r in conn.execute("SELECT severity, COUNT(*) as count FROM drug_interactions GROUP BY severity").fetchall()],
        "ayurveda_by_type": [dict(r) for r in conn.execute("SELECT entry_type, COUNT(*) as count FROM ayurveda_diet GROUP BY entry_type").fetchall()],
    }
    conn.close(); return stats
