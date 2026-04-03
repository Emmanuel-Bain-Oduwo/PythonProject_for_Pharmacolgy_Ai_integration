"""
seed_emergency_protocols.py
---------------------------
Seeds core emergency protocols used by the Streamlit and API emergency pages.
"""

import json
import logging
import sqlite3
from typing import Tuple

from db_config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


PROTOCOLS = [
    {
        "name": "Anaphylaxis (Adult)",
        "category": "Allergy / Resuscitation",
        "indication": "Acute severe allergic reaction with airway/breathing/circulation compromise.",
        "steps": json.dumps([
            "Call for help and activate emergency response.",
            "Lay patient flat, raise legs, avoid standing suddenly.",
            "Give IM adrenaline in lateral thigh immediately.",
            "High-flow oxygen and establish IV access.",
            "Repeat IM adrenaline every 5 minutes if persistent symptoms.",
            "Add fluids, antihistamine, and steroid as adjuncts.",
            "Observe for biphasic reaction and monitor vitals.",
        ]),
        "drugs": json.dumps([
            "Adrenaline IM",
            "Normal saline IV bolus",
            "Chlorpheniramine",
            "Hydrocortisone",
            "Nebulized salbutamol (if bronchospasm)",
        ]),
        "doses": "Adrenaline IM 0.5 mg (1:1000) adult; repeat every 5 min if needed.",
        "notes": "Adrenaline is first-line. Do not delay for IV access.",
        "reference": "WHO / ACLS aligned emergency allergy practice",
    },
    {
        "name": "Acute Severe Asthma",
        "category": "Respiratory",
        "indication": "Severe bronchospasm with respiratory distress or impending respiratory failure.",
        "steps": json.dumps([
            "Assess airway, breathing, circulation and pulse oximetry.",
            "Give oxygen to target SpO2 94-98%.",
            "Start repeated/nebulized short-acting beta-agonist.",
            "Add ipratropium in severe attacks.",
            "Give systemic corticosteroid early.",
            "Escalate with magnesium sulfate if poor response.",
            "Prepare ICU/intubation pathway if tiring or rising CO2.",
        ]),
        "drugs": json.dumps([
            "Salbutamol nebulization",
            "Ipratropium bromide",
            "Hydrocortisone IV or prednisolone oral",
            "Magnesium sulfate IV",
        ]),
        "doses": "Salbutamol 5 mg neb q20min x3; hydrocortisone 100 mg IV; magnesium sulfate 2 g IV over 20 min.",
        "notes": "Reassess after each cycle; watch exhaustion and silent chest.",
        "reference": "GINA severe asthma emergency recommendations",
    },
    {
        "name": "Hyperkalemia (Emergency)",
        "category": "Electrolyte",
        "indication": "Severe hyperkalemia or ECG changes suggestive of potassium toxicity.",
        "steps": json.dumps([
            "Confirm potassium urgently and obtain ECG.",
            "Stabilize myocardium with IV calcium.",
            "Shift potassium intracellularly (insulin+dextrose, beta-agonist).",
            "Consider bicarbonate if metabolic acidosis.",
            "Remove potassium (loop diuretic, resin, dialysis in severe/renal failure).",
            "Repeat labs and ECG frequently.",
        ]),
        "drugs": json.dumps([
            "Calcium gluconate",
            "Regular insulin + dextrose",
            "Nebulized salbutamol",
            "Sodium bicarbonate (selected cases)",
            "Potassium binders / dialysis",
        ]),
        "doses": "Calcium gluconate 10 mL of 10% IV over 2-5 min; insulin 10 U IV + dextrose 25 g.",
        "notes": "Treat ECG changes immediately, do not wait for repeat potassium.",
        "reference": "Emergency medicine electrolyte protocols",
    },
    {
        "name": "Hypoglycemia (Conscious and Unconscious)",
        "category": "Endocrine / Metabolic",
        "indication": "Symptomatic low blood glucose or altered consciousness due to hypoglycemia.",
        "steps": json.dumps([
            "Check capillary glucose immediately.",
            "If conscious: give fast-acting oral glucose.",
            "If unconscious/NPO: give IV dextrose or IM glucagon.",
            "Recheck glucose after 10-15 minutes and repeat if needed.",
            "Provide long-acting carbohydrate once stable.",
            "Identify and correct precipitating cause.",
        ]),
        "drugs": json.dumps([
            "Oral glucose",
            "Dextrose IV",
            "Glucagon IM",
        ]),
        "doses": "Dextrose 25 g IV (50 mL of D50 or equivalent) OR glucagon 1 mg IM if no IV access.",
        "notes": "Avoid overtreatment and rebound hyperglycemia.",
        "reference": "ADA emergency glucose management",
    },
    {
        "name": "Acute Coronary Syndrome (Initial)",
        "category": "Cardiology",
        "indication": "Suspected ACS with chest pain or ischemic ECG changes.",
        "steps": json.dumps([
            "Rapid assessment: ECG within 10 minutes.",
            "Assess hemodynamics and oxygen saturation.",
            "Give antiplatelet loading unless contraindicated.",
            "Start anti-ischemic and anticoagulation per protocol.",
            "Activate reperfusion pathway for STEMI.",
            "Serial troponin and continuous monitoring.",
        ]),
        "drugs": json.dumps([
            "Aspirin",
            "P2Y12 inhibitor",
            "Heparin/LMWH",
            "Nitroglycerin (if appropriate)",
            "High-intensity statin",
        ]),
        "doses": "Aspirin 300-325 mg chewed loading; add second antiplatelet per local protocol.",
        "notes": "Tailor antithrombotics to bleeding risk and renal function.",
        "reference": "ESC/ACC acute coronary syndrome guidance",
    },
    {
        "name": "Diabetic Ketoacidosis (DKA)",
        "category": "Endocrine / Metabolic",
        "indication": "Hyperglycemia, ketonemia/ketonuria, and metabolic acidosis with dehydration.",
        "steps": json.dumps([
            "Assess airway, breathing, circulation and mental status immediately.",
            "Start isotonic IV fluids promptly and monitor hemodynamics.",
            "Check potassium before insulin and replace potassium as indicated.",
            "Start fixed-rate IV insulin infusion after initial fluid and potassium safety check.",
            "Monitor glucose, ketones, bicarbonate, anion gap, and electrolytes every 2-4 hours.",
            "Add dextrose when glucose falls to continue ketone clearance safely.",
            "Identify trigger (infection, missed insulin, MI, stroke) and treat cause.",
        ]),
        "drugs": json.dumps([
            "0.9% Normal saline",
            "Regular insulin IV infusion",
            "Potassium chloride",
            "Dextrose infusion when glucose falls",
        ]),
        "doses": "Typical insulin infusion 0.1 U/kg/h after potassium assessment; replace potassium per protocol.",
        "notes": "Do not start insulin if severe hypokalemia is present until potassium correction begins.",
        "reference": "ADA/AACE DKA management recommendations",
    },
    {
        "name": "Hyperosmolar Hyperglycemic State (HHS)",
        "category": "Endocrine / Metabolic",
        "indication": "Severe hyperglycemia with hyperosmolality, profound dehydration, and minimal ketosis.",
        "steps": json.dumps([
            "Rapid volume resuscitation with isotonic fluids.",
            "Correct electrolytes and monitor osmolality closely.",
            "Initiate insulin infusion after adequate initial fluid replacement.",
            "Lower glucose and osmolality gradually to avoid cerebral edema.",
            "Search and treat precipitating causes urgently.",
        ]),
        "drugs": json.dumps(["0.9% Normal saline", "Regular insulin infusion", "Potassium replacement"]),
        "doses": "Use cautious insulin after fluids; avoid rapid osmolality shifts.",
        "notes": "Mortality is high; aggressive monitoring and trigger control are critical.",
        "reference": "ADA hyperglycemic crisis consensus",
    },
    {
        "name": "Sepsis and Septic Shock (Initial Bundle)",
        "category": "Infectious Disease / Critical Care",
        "indication": "Suspected infection with organ dysfunction or hypotension suggesting septic shock.",
        "steps": json.dumps([
            "Obtain cultures quickly and measure lactate.",
            "Start broad-spectrum antibiotics early (ideally within 1 hour in shock).",
            "Give initial fluid bolus and reassess perfusion dynamically.",
            "Start vasopressors if hypotension persists after fluids.",
            "Track urine output, MAP, lactate trend, and organ function.",
        ]),
        "drugs": json.dumps(["Broad-spectrum IV antibiotics", "Crystalloid fluids", "Norepinephrine"]),
        "doses": "Initial crystalloid 30 mL/kg in shock; vasopressor target MAP >= 65 mmHg.",
        "notes": "Antimicrobial de-escalation should follow culture and clinical response.",
        "reference": "Surviving Sepsis Campaign bundle",
    },
    {
        "name": "Status Epilepticus",
        "category": "Neurology",
        "indication": "Seizure lasting >5 minutes or recurrent seizures without full recovery.",
        "steps": json.dumps([
            "Protect airway and provide oxygen; check glucose rapidly.",
            "Give first-line benzodiazepine promptly.",
            "If persistent, load second-line antiseizure medication.",
            "Escalate to refractory seizure protocol and ICU if ongoing.",
            "Investigate and treat underlying cause (infection, metabolic, toxic, structural).",
        ]),
        "drugs": json.dumps(["Lorazepam or diazepam", "Levetiracetam/valproate/fosphenytoin", "Anesthetic agents (refractory)"]),
        "doses": "Lorazepam 0.1 mg/kg IV (max 4 mg), repeat once if needed; then second-line loading.",
        "notes": "Time-critical treatment reduces neuronal injury and mortality.",
        "reference": "ILAE / emergency neurology guidelines",
    },
    {
        "name": "Acute Ischemic Stroke (Initial)",
        "category": "Neurology / Stroke",
        "indication": "Sudden focal neurologic deficit with suspected acute ischemic stroke.",
        "steps": json.dumps([
            "Activate stroke code and establish last-known-well time.",
            "Immediate non-contrast CT brain and vascular imaging per pathway.",
            "Assess thrombolysis and thrombectomy eligibility rapidly.",
            "Control blood pressure within protocol thresholds.",
            "Monitor airway, glucose, and neurologic status closely.",
        ]),
        "drugs": json.dumps(["Alteplase/tenecteplase (eligible)", "Antiplatelet therapy when appropriate"]),
        "doses": "Alteplase 0.9 mg/kg (max 90 mg) when eligible per institutional protocol.",
        "notes": "Avoid delays; imaging and eligibility decisions are time-critical.",
        "reference": "AHA/ASA acute ischemic stroke guidance",
    },
    {
        "name": "Acute Pulmonary Edema",
        "category": "Cardiorespiratory",
        "indication": "Respiratory distress with suspected acute cardiogenic pulmonary edema.",
        "steps": json.dumps([
            "Sit patient upright and provide high-flow oxygen or NIV.",
            "Give vasodilator if blood pressure allows.",
            "Administer IV loop diuretic and reassess response.",
            "Monitor blood pressure, oxygenation, urine output, and ECG.",
            "Escalate to ICU/intubation if deteriorating.",
        ]),
        "drugs": json.dumps(["Nitroglycerin", "Furosemide", "Non-invasive ventilation"]),
        "doses": "Furosemide 20-80 mg IV based on prior diuretic exposure and renal function.",
        "notes": "Hypotension and renal dysfunction require individualized vasodilator/diuretic strategy.",
        "reference": "ESC acute heart failure recommendations",
    },
    {
        "name": "Upper GI Bleed (Initial)",
        "category": "Gastroenterology",
        "indication": "Hematemesis/melena or suspected significant upper gastrointestinal hemorrhage.",
        "steps": json.dumps([
            "Assess airway and hemodynamics; establish large-bore IV access.",
            "Resuscitate with fluids/blood products as needed.",
            "Start IV proton pump inhibitor therapy.",
            "Risk stratify and arrange urgent endoscopy.",
            "Consider variceal protocol when clinically suspected.",
        ]),
        "drugs": json.dumps(["IV PPI", "Blood products", "Octreotide/terlipressin if variceal bleed"]),
        "doses": "Pantoprazole 80 mg IV bolus then infusion or intermittent high-dose regimen per protocol.",
        "notes": "Transfusion targets and anticoagulation reversal should follow local policy.",
        "reference": "ACG/ESGE GI bleed management guidance",
    },
    {
        "name": "Hypertensive Emergency",
        "category": "Cardiovascular",
        "indication": "Severe blood pressure elevation with acute target-organ damage.",
        "steps": json.dumps([
            "Confirm BP and assess end-organ injury (neurologic, cardiac, renal, retinal).",
            "Begin controlled IV antihypertensive reduction.",
            "Target initial MAP reduction by about 20-25% in first hour unless condition-specific exceptions.",
            "Continuous cardiac and hemodynamic monitoring.",
            "Tailor agent to syndrome (aortic dissection, stroke, pulmonary edema, eclampsia).",
        ]),
        "drugs": json.dumps(["Labetalol", "Nicardipine", "Nitroglycerin", "Sodium nitroprusside (selected)"]),
        "doses": "Use IV titration protocol with frequent BP checks; avoid overly rapid pressure drops.",
        "notes": "Management differs for ischemic stroke, hemorrhagic stroke, and aortic dissection.",
        "reference": "ACC/AHA hypertensive crisis recommendations",
    },
    {
        "name": "Opioid Overdose",
        "category": "Toxicology",
        "indication": "Suspected opioid toxicity with respiratory depression or reduced consciousness.",
        "steps": json.dumps([
            "Assess airway and breathing; start assisted ventilation if needed.",
            "Administer naloxone with titrated dosing.",
            "Monitor for recurrent respiratory depression due to shorter naloxone half-life.",
            "Search for co-ingestants and complications (aspiration, trauma).",
            "Observe until clinically stable and consider referral for addiction care.",
        ]),
        "drugs": json.dumps(["Naloxone", "Oxygen", "Ventilatory support"]),
        "doses": "Naloxone 0.04-0.4 mg IV/IM/IN, repeat/titrate to adequate ventilation.",
        "notes": "Priority is ventilation and oxygenation; avoid abrupt severe withdrawal when possible.",
        "reference": "Emergency toxicology and overdose protocols",
    },
    {
        "name": "Acute Kidney Injury (Medication Safety Emergency)",
        "category": "Renal",
        "indication": "Rapid decline in renal function with oliguria, rising creatinine, or toxic medication exposure.",
        "steps": json.dumps([
            "Confirm AKI severity and trend creatinine/urine output.",
            "Stop nephrotoxic and renally-cleared high-risk drugs where appropriate.",
            "Optimize volume status and hemodynamics.",
            "Check electrolytes, acid-base, and ECG for life-threatening disturbances.",
            "Escalate for renal replacement therapy evaluation when indicated.",
        ]),
        "drugs": json.dumps(["Medication review and temporary holds", "Electrolyte-directed treatment", "Dialysis support when indicated"]),
        "doses": "Use renal-adjusted dosing immediately for all essential medications.",
        "notes": "Early medication reconciliation reduces preventable nephrotoxicity and adverse outcomes.",
        "reference": "KDIGO AKI and medication safety principles",
    },
]


def seed_emergency_protocols() -> Tuple[int, int]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    inserted = 0
    updated = 0

    for item in PROTOCOLS:
        drugs_val = item.get("drugs")
        medications_val = item.get("medications", drugs_val)
        existing = cur.execute("SELECT id FROM emergency_protocols WHERE name=?", (item["name"],)).fetchone()
        if existing:
            cur.execute(
                """
                UPDATE emergency_protocols
                SET category=?, indication=?, steps=?, medications=?, drugs=?, doses=?, notes=?, reference=?
                WHERE name=?
                """,
                (
                    item.get("category"),
                    item.get("indication"),
                    item.get("steps"),
                    medications_val,
                    drugs_val,
                    item.get("doses"),
                    item.get("notes"),
                    item.get("reference"),
                    item["name"],
                ),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO emergency_protocols
                (name, category, indication, steps, medications, drugs, doses, notes, reference)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["name"],
                    item.get("category"),
                    item.get("indication"),
                    item.get("steps"),
                    medications_val,
                    drugs_val,
                    item.get("doses"),
                    item.get("notes"),
                    item.get("reference"),
                ),
            )
            inserted += 1

    conn.commit()
    conn.close()
    log.info("✅ Emergency protocols seeded. inserted=%d updated=%d total=%d", inserted, updated, len(PROTOCOLS))
    return inserted, updated


if __name__ == "__main__":
    seed_emergency_protocols()
