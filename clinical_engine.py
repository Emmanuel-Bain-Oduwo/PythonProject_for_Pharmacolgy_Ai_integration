"""
clinical_engine.py
===================
Comprehensive clinical calculation engine.
Covers: renal, hepatic, BSA, IBW, dose adjustments, QTc, PK modelling,
        paediatric formulas, genetics, hormone and lab interpretation.
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ─── ENUMS ────────────────────────────────────────────────────────────────────
class Gender(Enum):
    MALE = "male"
    FEMALE = "female"

class RenalStage(Enum):
    NORMAL     = "Normal (eGFR ≥90)"
    MILD       = "Mild CKD G2 (eGFR 60-89)"
    MODERATE_A = "Moderate CKD G3a (eGFR 45-59)"
    MODERATE_B = "Moderate CKD G3b (eGFR 30-44)"
    SEVERE     = "Severe CKD G4 (eGFR 15-29)"
    ESRD       = "Kidney failure G5 (eGFR <15)"


# ─── PATIENT PROFILE ─────────────────────────────────────────────────────────
@dataclass
class PatientProfile:
    age: int
    weight_kg: float
    height_cm: float
    gender: Gender
    serum_creatinine: Optional[float] = None   # mg/dL
    albumin: Optional[float] = None            # g/dL
    bilirubin: Optional[float] = None          # mg/dL
    ast: Optional[float] = None                # IU/L
    alt: Optional[float] = None                # IU/L
    is_pregnant: bool = False
    is_breastfeeding: bool = False
    ethnicity: Optional[str] = None
    cyp2d6_phenotype: Optional[str] = None     # PM/IM/EM/UM
    cyp2c19_phenotype: Optional[str] = None
    cyp2c9_phenotype: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)


# ─── CLINICAL CALCULATOR ─────────────────────────────────────────────────────
class ClinicalCalculator:

    # ── Body metrics ──────────────────────────────────────────────────────────
    @staticmethod
    def bsa_mosteller(weight_kg: float, height_cm: float) -> float:
        """BSA (m²) = √[(height(cm) × weight(kg)) / 3600]"""
        return math.sqrt((height_cm * weight_kg) / 3600)

    @staticmethod
    def bsa_dubois(weight_kg: float, height_cm: float) -> float:
        """BSA (m²) = 0.007184 × height^0.725 × weight^0.425"""
        return 0.007184 * (height_cm ** 0.725) * (weight_kg ** 0.425)

    @staticmethod
    def ibw_devine(height_cm: float, gender: Gender) -> float:
        """Ideal Body Weight — Devine formula (kg)"""
        h_in = height_cm / 2.54
        if h_in <= 60:
            return 50.0 if gender == Gender.MALE else 45.5
        excess = h_in - 60
        return (50 + 2.3 * excess) if gender == Gender.MALE else (45.5 + 2.3 * excess)

    @staticmethod
    def adjusted_bw(actual_kg: float, ibw_kg: float) -> float:
        """Adjusted Body Weight for obese patients = IBW + 0.4(ABW - IBW)"""
        if actual_kg <= ibw_kg:
            return actual_kg
        return ibw_kg + 0.4 * (actual_kg - ibw_kg)

    @staticmethod
    def bmi(weight_kg: float, height_cm: float) -> float:
        h_m = height_cm / 100
        return weight_kg / (h_m ** 2)

    @staticmethod
    def bmi_category(bmi_val: float) -> str:
        if bmi_val < 18.5:   return "Underweight"
        if bmi_val < 25:     return "Normal weight"
        if bmi_val < 30:     return "Overweight"
        if bmi_val < 35:     return "Obese Class I"
        if bmi_val < 40:     return "Obese Class II"
        return "Obese Class III (Morbid)"

    # ── Renal function ────────────────────────────────────────────────────────
    @staticmethod
    def crcl_cockcroft_gault(age: int, weight_kg: float, scr: float,
                              gender: Gender) -> float:
        """CrCl (mL/min) — Cockcroft-Gault. Use IBW in obesity."""
        crcl = ((140 - age) * weight_kg) / (72 * scr)
        if gender == Gender.FEMALE:
            crcl *= 0.85
        return round(crcl, 1)

    @staticmethod
    def egfr_ckd_epi(age: int, scr: float, gender: Gender,
                     is_black: bool = False) -> float:
        """
        eGFR (mL/min/1.73m²) — CKD-EPI 2021 (race-free)
        Standard clinical formula for CKD staging.
        """
        if gender == Gender.FEMALE:
            kappa, alpha = 0.7, -0.241
        else:
            kappa, alpha = 0.9, -0.302

        scr_kappa = scr / kappa
        term1 = min(scr_kappa, 1) ** alpha
        term2 = max(scr_kappa, 1) ** (-1.200)
        egfr = 142 * term1 * term2 * (0.9938 ** age)
        if gender == Gender.FEMALE:
            egfr *= 1.012
        return round(egfr, 1)

    @staticmethod
    def ckd_stage(egfr: float) -> RenalStage:
        if egfr >= 90:  return RenalStage.NORMAL
        if egfr >= 60:  return RenalStage.MILD
        if egfr >= 45:  return RenalStage.MODERATE_A
        if egfr >= 30:  return RenalStage.MODERATE_B
        if egfr >= 15:  return RenalStage.SEVERE
        return RenalStage.ESRD

    @staticmethod
    def egfr_mdrd(age: int, scr: float, gender: Gender) -> float:
        """MDRD 4-variable eGFR"""
        egfr = 175 * (scr ** -1.154) * (age ** -0.203)
        if gender == Gender.FEMALE:
            egfr *= 0.742
        return round(egfr, 1)

    # ── Hepatic function ──────────────────────────────────────────────────────
    @staticmethod
    def child_pugh_score(bilirubin: float, albumin: float,
                         pt_seconds_prolonged: float,
                         ascites: str, encephalopathy: str) -> Tuple[int, str]:
        """
        Child-Pugh score for hepatic impairment.
        Returns (score, class).
        ascites: 'none'/'mild'/'moderate-severe'
        encephalopathy: 'none'/'grade1-2'/'grade3-4'
        """
        score = 0
        # Bilirubin (mg/dL)
        if bilirubin < 2: score += 1
        elif bilirubin <= 3: score += 2
        else: score += 3
        # Albumin (g/dL)
        if albumin > 3.5: score += 1
        elif albumin >= 2.8: score += 2
        else: score += 3
        # PT prolongation (seconds)
        if pt_seconds_prolonged < 4: score += 1
        elif pt_seconds_prolonged <= 6: score += 2
        else: score += 3
        # Ascites
        asc_map = {"none": 1, "mild": 2, "moderate-severe": 3}
        score += asc_map.get(ascites, 1)
        # Encephalopathy
        enc_map = {"none": 1, "grade1-2": 2, "grade3-4": 3}
        score += enc_map.get(encephalopathy, 1)

        if score <= 6:   cp_class = "A (Well-compensated)"
        elif score <= 9: cp_class = "B (Significant functional compromise)"
        else:            cp_class = "C (Decompensated)"

        return score, cp_class

    # ── QTc ───────────────────────────────────────────────────────────────────
    @staticmethod
    def qtc_bazett(qt_ms: float, hr_bpm: float) -> float:
        """QTc = QT / √(RR). RR = 60/HR in seconds."""
        rr = 60 / hr_bpm
        return round(qt_ms / math.sqrt(rr), 1)

    @staticmethod
    def qtc_fridericia(qt_ms: float, hr_bpm: float) -> float:
        """QTc = QT / ∛(RR)"""
        rr = 60 / hr_bpm
        return round(qt_ms / (rr ** (1/3)), 1)

    @staticmethod
    def qtc_risk(qtc_ms: float) -> str:
        if qtc_ms < 450:  return "Normal (< 450ms)"
        if qtc_ms < 470:  return "⚠️ Borderline (450-469ms) — caution with QT-prolonging drugs"
        if qtc_ms < 500:  return "🔴 Prolonged (470-499ms) — avoid QT-prolonging drugs"
        return "🚨 CRITICAL (≥500ms) — HIGH risk Torsades de Pointes. STOP QT drugs."

    # ── PK calculations ───────────────────────────────────────────────────────
    @staticmethod
    def loading_dose(target_conc: float, vd_l_per_kg: float,
                     weight_kg: float, bioavailability: float = 1.0) -> float:
        """Loading Dose = (Target Cp × Vd) / F"""
        return round((target_conc * vd_l_per_kg * weight_kg) / bioavailability, 2)

    @staticmethod
    def maintenance_dose(target_conc: float, clearance_l_h_per_kg: float,
                          weight_kg: float, bioavailability: float = 1.0,
                          interval_h: float = 24.0) -> float:
        """Maintenance Dose = (Target Cp × CL × interval) / F"""
        return round((target_conc * clearance_l_h_per_kg * weight_kg * interval_h) / bioavailability, 2)

    @staticmethod
    def half_life(vd_l: float, clearance_l_h: float) -> float:
        """t½ = (0.693 × Vd) / CL"""
        return round(0.693 * vd_l / clearance_l_h, 2)

    @staticmethod
    def time_to_steady_state(half_life_h: float) -> float:
        """~5 half-lives to reach steady state"""
        return round(5 * half_life_h, 1)

    @staticmethod
    def trough_level(initial_conc: float, half_life_h: float,
                     interval_h: float) -> float:
        """Trough = C0 × e^(-0.693/t½ × interval)"""
        ke = 0.693 / half_life_h
        return round(initial_conc * math.exp(-ke * interval_h), 3)

    @staticmethod
    def peak_level_iv(dose_mg: float, vd_l: float) -> float:
        """Peak (IV bolus) = Dose / Vd"""
        return round(dose_mg / vd_l, 3)

    # ── Paediatric dosing ─────────────────────────────────────────────────────
    @staticmethod
    def youngs_rule(adult_dose: float, child_age_years: float) -> float:
        """Young's Rule: Child dose = (Age / (Age + 12)) × Adult dose"""
        return round((child_age_years / (child_age_years + 12)) * adult_dose, 2)

    @staticmethod
    def clarks_rule(adult_dose: float, child_weight_kg: float) -> float:
        """Clark's Rule: Child dose = (Weight(lb) / 150) × Adult dose"""
        weight_lb = child_weight_kg * 2.205
        return round((weight_lb / 150) * adult_dose, 2)

    @staticmethod
    def weight_based_dose(dose_per_kg: float, weight_kg: float,
                           max_dose: Optional[float] = None) -> float:
        """Weight-based dose with optional ceiling"""
        dose = dose_per_kg * weight_kg
        if max_dose:
            dose = min(dose, max_dose)
        return round(dose, 2)

    @staticmethod
    def bsa_based_dose(dose_per_m2: float, bsa_m2: float,
                        max_dose: Optional[float] = None) -> float:
        """BSA-based dose (oncology)"""
        dose = dose_per_m2 * bsa_m2
        if max_dose:
            dose = min(dose, max_dose)
        return round(dose, 2)

    # ── Nutrition / metabolism ─────────────────────────────────────────────────
    @staticmethod
    def harris_benedict_bmr(weight_kg: float, height_cm: float,
                             age: int, gender: Gender) -> float:
        """Basal Metabolic Rate (kcal/day) — revised Harris-Benedict"""
        if gender == Gender.MALE:
            return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
        else:
            return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)

    @staticmethod
    def tdee(bmr: float, activity_level: str) -> float:
        """Total Daily Energy Expenditure"""
        factors = {
            "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
            "active": 1.725, "very_active": 1.9
        }
        return round(bmr * factors.get(activity_level, 1.2), 0)

    @staticmethod
    def corrected_calcium(measured_ca: float, albumin: float) -> float:
        """Corrected Ca (mg/dL) = Measured Ca + 0.8 × (4.0 - Albumin)"""
        return round(measured_ca + 0.8 * (4.0 - albumin), 2)

    @staticmethod
    def anion_gap(sodium: float, chloride: float, bicarbonate: float,
                  albumin: Optional[float] = None) -> Dict:
        """Anion gap ± albumin correction"""
        ag = sodium - (chloride + bicarbonate)
        result = {"anion_gap": round(ag, 1), "normal_range": "8-12 mEq/L (uncorrected)"}
        if albumin:
            ag_corrected = ag + 2.5 * (4.0 - albumin)
            result["ag_corrected"] = round(ag_corrected, 1)
            result["interpretation"] = "High AG acidosis" if ag_corrected > 12 else "Normal AG"
        else:
            result["interpretation"] = "High AG acidosis" if ag > 12 else "Normal AG"
        return result

    @staticmethod
    def map_calculation(sbp: float, dbp: float) -> float:
        """Mean Arterial Pressure = DBP + (SBP - DBP) / 3"""
        return round(dbp + (sbp - dbp) / 3, 1)

    @staticmethod
    def phenytoin_correction_albumin(measured_level: float, albumin: float,
                                     uraemia: bool = False) -> float:
        """
        Corrected phenytoin for hypoalbuminaemia.
        Normal: C_corrected = C_measured / (0.2 × albumin + 0.1)
        Uraemia: C_corrected = C_measured / (0.1 × albumin + 0.1)
        """
        if uraemia:
            return round(measured_level / (0.1 * albumin + 0.1), 2)
        return round(measured_level / (0.2 * albumin + 0.1), 2)

    @staticmethod
    def vancomycin_auc_method(auc_target: float = 500,
                               mic: float = 1.0) -> Dict:
        """Vancomycin AUC/MIC target (2020 ASHP guidelines)"""
        return {
            "target_auc_mic": f"{auc_target}/{mic}",
            "auc_target": f"{auc_target} mg·h/L",
            "clinical_target": "AUC/MIC 400-600 recommended over trough monitoring",
            "previous_trough_target": "15-20 mg/L (if AUC not available)"
        }

    @staticmethod
    def creatinine_clearance_paediatric(height_cm: float, scr: float) -> float:
        """Schwartz Formula for paediatric eGFR
        eGFR (mL/min/1.73m²) = k × height(cm) / SCr
        k = 0.413 (Schwartz 2009 revised)
        """
        return round(0.413 * height_cm / scr, 1)

    @staticmethod
    def wells_score_dvt(clinical_features: Dict) -> Tuple[int, str]:
        """
        Wells Score for DVT probability
        Returns (score, probability).
        clinical_features: dict with boolean values for each criterion
        """
        criteria = {
            "active_cancer": 1,
            "paralysis_plaster": 1,
            "bedridden_3days_or_surgery_12wks": 1,
            "localised_tenderness": 1,
            "entire_leg_swollen": 1,
            "calf_swelling_3cm_diff": 1,
            "pitting_oedema": 1,
            "collateral_superficial_veins": 1,
            "previously_documented_dvt": 1,
            "alternative_diagnosis_likely": -2,
        }
        score = sum(v for k, v in criteria.items()
                    if clinical_features.get(k, False))
        if score <= 0:
            prob = "Low probability (<5%)"
        elif score <= 2:
            prob = "Moderate probability (17%)"
        else:
            prob = "High probability (53%)"

        return score, prob

    @staticmethod
    def chads2_vasc(age: int, gender: Gender,
                    chf: bool, hypertension: bool, diabetes: bool,
                    stroke_tia: bool, vascular_disease: bool) -> Tuple[int, str]:
        """CHA₂DS₂-VASc for AF stroke risk"""
        score = 0
        if chf:           score += 1
        if hypertension:  score += 1
        if age >= 75:     score += 2
        elif age >= 65:   score += 1
        if diabetes:      score += 1
        if stroke_tia:    score += 2
        if vascular_disease: score += 1
        if gender == Gender.FEMALE: score += 1

        if score == 0:   rec = "Low risk — no anticoagulation needed"
        elif score == 1: rec = "Low-moderate — consider anticoagulation (especially if male)"
        else:            rec = f"Anticoagulation recommended (CHA₂DS₂-VASc {score})"

        return score, rec


# ─── DOSE ADJUSTMENT ENGINE ──────────────────────────────────────────────────
class DoseAdjustmentEngine:

    @staticmethod
    def renal_adjustment(drug_name: str, crcl: float,
                          dose_json: Optional[str] = None) -> Dict:
        """
        Provides renal dose guidance.
        dose_json: JSON string from medications table (dose_renal_adj column)
        """
        import json as _json
        result = {"drug": drug_name, "crcl": crcl}
        stage = ClinicalCalculator.ckd_stage(crcl)
        result["ckd_stage"] = stage.value

        if dose_json:
            try:
                adj = _json.loads(dose_json)
                result["adjustment_table"] = adj
            except Exception:
                pass

        if crcl < 10:
            result["flag"] = "🚨 ESRD — Avoid most renally cleared drugs or use dialysis-specific dose"
        elif crcl < 30:
            result["flag"] = "🔴 Severe CKD — Significant dose reduction usually required"
        elif crcl < 60:
            result["flag"] = "🟡 Moderate CKD — Monitor closely; dose adjustment likely needed"
        else:
            result["flag"] = "🟢 Normal to mild — Standard doses generally appropriate"

        return result

    @staticmethod
    def geriatric_assessment(age: int, drug_class: str) -> Dict:
        """
        Beers Criteria-informed geriatric prescribing assessment.
        Flags high-risk drug classes.
        """
        high_risk_geriatric = {
            "Benzodiazepine": "⚠️ HIGH RISK ELDERLY: falls, cognitive impairment, dependence",
            "Tricyclic Antidepressant": "⚠️ HIGH RISK: anticholinergic, QTc, orthostatic hypotension",
            "Antihistamine (1st gen)": "⚠️ HIGH RISK: anticholinergic (diphenhydramine, chlorphenamine)",
            "Sulphonylurea": "⚠️ HIGH RISK: prolonged hypoglycaemia in elderly",
            "NSAID": "⚠️ HIGH RISK: GI bleed, renal impairment, fluid retention",
            "Antipsychotic (Typical)": "⚠️ HIGH RISK: falls, QTc, stroke in dementia",
            "Opioid": "⚠️ HIGH RISK: falls, delirium, respiratory depression",
            "Digoxin": "⚠️ HIGH RISK: narrow TI; renal clearance reduced in elderly",
        }
        result = {
            "age": age,
            "drug_class": drug_class,
            "beers_criteria": high_risk_geriatric.get(drug_class, "No specific Beers Criteria flag"),
        }
        if age >= 75:
            result["recommendation"] = "START LOW, GO SLOW — comprehensive medication review recommended"
        elif age >= 65:
            result["recommendation"] = "Review all medications — polypharmacy assessment"
        return result

    @staticmethod
    def pregnancy_classification(category: str, drug_name: str) -> Dict:
        """Interpret FDA pregnancy category"""
        categories = {
            "A": "✅ Adequate human studies show no foetal risk",
            "B": "✅ Animal studies show no risk; no adequate human studies OR animal studies show risk but human studies do not",
            "C": "⚠️ Risk not ruled out — animal studies show adverse effects; no adequate human studies. Use if benefits > risks",
            "D": "🔴 Evidence of human foetal risk — use only if life-threatening and no alternatives",
            "X": "🚨 CONTRAINDICATED in pregnancy — foetal abnormalities documented; risks outweigh any benefit",
        }
        return {
            "drug": drug_name,
            "category": category,
            "meaning": categories.get(category.upper(), "Insufficient data"),
        }

    @staticmethod
    def paediatric_weight_class(weight_kg: float, age_years: float) -> str:
        """Simple paediatric classification"""
        if age_years < (1/12):  return "Neonate (<1 month)"
        if age_years < 1:       return "Young Infant (1-11 months)"
        if age_years < 2:       return "Infant (1-2 years)"
        if age_years < 6:       return "Young Child (2-5 years)"
        if age_years < 12:      return "Child (6-11 years)"
        if age_years < 18:      return "Adolescent (12-17 years)"
        return "Adult"


# ─── DRUG INTERACTION SEVERITY ────────────────────────────────────────────────
class InteractionChecker:

    SEVERITY_COLOURS = {
        "Contraindicated": "🚨",
        "Major": "🔴",
        "Moderate": "🟡",
        "Minor": "🟢",
    }

    @staticmethod
    def format_interaction(drug_a: str, drug_b: str, severity: str,
                            mechanism: str, effect: str,
                            management: str) -> Dict:
        icon = InteractionChecker.SEVERITY_COLOURS.get(severity, "⚪")
        return {
            "drugs": f"{drug_a} + {drug_b}",
            "severity": f"{icon} {severity}",
            "mechanism": mechanism,
            "clinical_effect": effect,
            "management": management,
        }


# ─── SAFETY CHECKER ───────────────────────────────────────────────────────────
class SafetyChecker:

    @staticmethod
    def check_renal_safety(drug_name: str, crcl: float) -> str:
        """Quick safety flag for selected high-risk drugs in renal impairment"""
        renal_warnings = {
            "Metformin": (30, "⚠️ Stop if eGFR <30"),
            "Digoxin": (30, "🔴 Reduce dose significantly; toxic range narrow"),
            "Vancomycin": (50, "🔴 Dose by AUC/MIC; levels mandatory"),
            "Methotrexate": (30, "🚨 Contraindicated in severe renal impairment"),
            "NSAIDs": (60, "⚠️ Caution >CrCl 60; avoid <30"),
            "Lithium": (30, "🔴 High toxicity risk; reduce dose and monitor closely"),
            "Gabapentin": (60, "🟡 Dose reduction needed"),
            "Enoxaparin": (30, "🔴 Reduce dose or switch to UFH"),
        }
        threshold, msg = renal_warnings.get(drug_name, (None, None))
        if threshold and crcl < threshold:
            return f"⚠️ {drug_name}: {msg} (CrCl = {crcl} mL/min)"
        return f"✅ {drug_name}: No specific renal dose flag at CrCl {crcl} mL/min"

    @staticmethod
    def check_qt_risk(drug_list: List[str]) -> List[str]:
        """Flag drugs known to prolong QT"""
        qt_prolongers = {
            "Amiodarone", "Haloperidol", "Quetiapine", "Ciprofloxacin",
            "Levofloxacin", "Azithromycin", "Methadone", "Ondansetron",
            "Domperidone", "Chlorpromazine", "Amitriptyline", "Sotalol",
        }
        flagged = [d for d in drug_list if d in qt_prolongers]
        if len(flagged) >= 2:
            return [f"🚨 MULTIPLE QT-PROLONGING DRUGS: {', '.join(flagged)} — ECG monitoring mandatory"]
        if len(flagged) == 1:
            return [f"⚠️ QT-prolonging drug: {flagged[0]} — obtain baseline ECG"]
        return ["✅ No QT-prolonging drugs detected"]

    @staticmethod
    def check_beers_criteria(drug_list: List[str], age: int) -> List[str]:
        """Check Beers Criteria high-risk drugs for older adults"""
        if age < 65:
            return []
        beers_drugs = {
            "Amitriptyline": "TCA — anticholinergic, sedating, orthostatic hypotension",
            "Diazepam": "Long-acting BZD — cognitive impairment, delirium, falls",
            "Glibenclamide": "Sulphonylurea — prolonged severe hypoglycaemia",
            "Chlorpromazine": "Typical antipsychotic — EPS, orthostatic hypotension, falls",
            "Ibuprofen": "NSAID — GI bleed, AKI, fluid retention",
            "Diclofenac": "NSAID — GI bleed, AKI, fluid retention",
            "Digoxin": "Narrow TI — renal clearance reduced; toxicity risk",
        }
        warnings = []
        for drug in drug_list:
            if drug in beers_drugs:
                warnings.append(f"⚠️ Beers Criteria ({age}y): {drug} — {beers_drugs[drug]}")
        return warnings if warnings else ["✅ No Beers Criteria drugs detected"]

    @staticmethod
    def genetic_dose_recommendation(drug: str, phenotype: str,
                                     gene: str) -> str:
        """Pharmacogenomics-guided dosing recommendations"""
        pgx = {
            ("Warfarin", "CYP2C9", "PM"):    "Reduce maintenance dose by 50-60%",
            ("Clopidogrel", "CYP2C19", "PM"): "Consider alternative (prasugrel/ticagrelor)",
            ("Tramadol", "CYP2D6", "UM"):     "CONTRAINDICATED — life-threatening opioid toxicity",
            ("Codeine", "CYP2D6", "UM"):      "CONTRAINDICATED — fatal respiratory depression reported",
            ("Metoprolol", "CYP2D6", "PM"):   "Reduce starting dose by 50%",
            ("Sertraline", "CYP2C19", "PM"):  "Start at 25mg; titrate slowly",
            ("Tamoxifen", "CYP2D6", "PM"):    "Consider aromatase inhibitor if post-menopausal",
        }
        key = (drug, gene, phenotype.upper())
        rec = pgx.get(key, f"Standard dosing — no specific {gene} {phenotype} recommendation in database")
        return f"🧬 {drug} ({gene} {phenotype}): {rec}"
