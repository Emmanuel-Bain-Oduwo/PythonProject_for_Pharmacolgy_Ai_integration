"""
ml_models.py  — Machine Learning + Visualisation Engine
Scikit-learn models: patient risk, interaction severity, diet planner, lab interpreter.
Visualisation: matplotlib, seaborn, plotly, pandas, numpy.
Run standalone: python ml_models.py
"""
import sqlite3, json, logging, os
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import plotly.graph_objects as go
import plotly.express as px

from db_config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODELS_DIR, exist_ok=True)


# ── PatientRiskModel ──────────────────────────────────────────────────────────
class PatientRiskModel:
    FEATURES = ["age","weight_kg","egfr","albumin","med_count","comorbidity_count",
                "hba1c","crp","wbc","heart_rate","sbp","is_pm_cyp2d6","is_pm_cyp2c19",
                "is_elderly","has_renal_impairment","has_diabetes","has_cardiac"]

    def __init__(self):
        self.model_path  = os.path.join(MODELS_DIR, "patient_risk_rf.pkl")
        self.scaler_path = os.path.join(MODELS_DIR, "patient_risk_scaler.pkl")
        self.model = None
        self.scaler = StandardScaler()

    def _synth(self, n=600):
        np.random.seed(42)
        d = {
            "age":               np.random.normal(55, 20, n).clip(18, 95),
            "weight_kg":         np.random.normal(70, 15, n).clip(40, 150),
            "egfr":              np.random.normal(65, 25, n).clip(5, 120),
            "albumin":           np.random.normal(3.8, 0.6, n).clip(1.5, 5.0),
            "med_count":         np.random.poisson(4, n).clip(0, 20),
            "comorbidity_count": np.random.poisson(2, n).clip(0, 10),
            "hba1c":             np.random.normal(6.5, 1.5, n).clip(4, 14),
            "crp":               np.random.exponential(5, n).clip(0, 300),
            "wbc":               np.random.normal(7, 3, n).clip(1, 30),
            "heart_rate":        np.random.normal(80, 15, n).clip(40, 160),
            "sbp":               np.random.normal(130, 20, n).clip(70, 220),
            "is_pm_cyp2d6":      np.random.binomial(1, 0.07, n),
            "is_pm_cyp2c19":     np.random.binomial(1, 0.025, n),
        }
        df = pd.DataFrame(d)
        df["is_elderly"]          = (df["age"] >= 65).astype(int)
        df["has_renal_impairment"]= (df["egfr"] < 60).astype(int)
        df["has_diabetes"]        = np.random.binomial(1, 0.3, n)
        df["has_cardiac"]         = np.random.binomial(1, 0.25, n)
        risk = ((df["age"]>70)*2 + (df["egfr"]<30)*3 + (df["med_count"]>7)*2 +
                (df["albumin"]<3.0)*2 + (df["crp"]>50)*2 + df["has_cardiac"] +
                df["is_pm_cyp2d6"] + np.random.binomial(1, 0.1, n))
        labels = (risk >= 4).astype(int)
        return df[self.FEATURES], labels

    def train(self):
        X, y = self._synth()
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        Xtr_s = self.scaler.fit_transform(Xtr)
        Xte_s = self.scaler.transform(Xte)
        self.model = RandomForestClassifier(n_estimators=100, max_depth=8,
                                            random_state=42, class_weight="balanced")
        self.model.fit(Xtr_s, ytr)
        auc = roc_auc_score(yte, self.model.predict_proba(Xte_s)[:,1])
        joblib.dump(self.model,  self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        log.info("✅ PatientRiskModel trained. AUC=%.3f", auc)
        return {"roc_auc": round(auc,3)}

    def load(self):
        if os.path.exists(self.model_path):
            self.model  = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            return True
        return False

    def predict(self, data: Dict) -> Dict:
        if not self.model and not self.load():
            self.train()
        X = np.array([data.get(f,0) for f in self.FEATURES]).reshape(1,-1)
        prob = float(self.model.predict_proba(self.scaler.transform(X))[0][1])
        imps = dict(zip(self.FEATURES, self.model.feature_importances_))
        top  = sorted(imps.items(), key=lambda x:-x[1])[:5]
        risk_level = "🟢 Low" if prob<0.3 else "🟡 Moderate" if prob<0.6 else "🔴 High"
        recs = []
        if data.get("egfr",100)<30:   recs.append("Adjust renally-cleared medications urgently")
        if data.get("med_count",0)>7: recs.append("Medication reconciliation — polypharmacy")
        if data.get("albumin",4)<3.0: recs.append("Nutritional support — hypoalbuminaemia")
        if prob>=0.6:                 recs.append("Enhanced clinical monitoring recommended")
        return {
            "risk_probability": round(prob, 3),
            "risk_level": risk_level,
            "top_risk_factors": [{"factor":k,"importance":round(v,3)} for k,v in top],
            "recommendation": "; ".join(recs) or "Standard care monitoring",
        }

    def plot_feature_importance(self, save_path=None):
        if not self.model and not self.load():
            self.train()
        imps = pd.Series(self.model.feature_importances_, index=self.FEATURES).sort_values()
        fig, ax = plt.subplots(figsize=(10,7))
        sns.set_style("whitegrid")
        imps.plot(kind="barh", ax=ax, color=sns.color_palette("RdYlGn_r", len(imps)))
        ax.set_title("Patient Risk — Feature Importance", fontsize=13, fontweight="bold")
        plt.tight_layout()
        path = save_path or os.path.join(MODELS_DIR, "feature_importance.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path


# ── DrugInteractionPredictor ──────────────────────────────────────────────────
class DrugInteractionPredictor:
    SEV_MAP = {0:"Minor",1:"Moderate",2:"Major",3:"Contraindicated"}

    def __init__(self):
        self.model_path = os.path.join(MODELS_DIR, "interaction_gbc.pkl")
        self.model = None

    def _synth(self, n=500):
        np.random.seed(0)
        rows = []
        for _ in range(n):
            sc, nti, add, pko = (np.random.randint(0,3), np.random.randint(0,2),
                                  np.random.randint(0,2), np.random.randint(0,3))
            label = min((sc+nti*2+add+pko//2)//2, 3)
            rows.append([sc, nti, add, pko, label])
        df = pd.DataFrame(rows, columns=["shared_cyp","narrow_ti","additive","pk_overlap","label"])
        return df[["shared_cyp","narrow_ti","additive","pk_overlap"]], df["label"]

    def train(self):
        X, y = self._synth()
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=1)
        self.model = GradientBoostingClassifier(n_estimators=80, random_state=1)
        self.model.fit(Xtr, ytr)
        acc = self.model.score(Xte, yte)
        joblib.dump(self.model, self.model_path)
        log.info("✅ InteractionPredictor trained. Accuracy=%.3f", acc)
        return {"accuracy": round(acc,3)}

    def load(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            return True
        return False

    def predict_severity(self, shared_cyp=0, narrow_ti=0, additive=0, pk_overlap=0):
        if not self.model and not self.load():
            self.train()
        label = int(self.model.predict([[shared_cyp, narrow_ti, additive, pk_overlap]])[0])
        return self.SEV_MAP.get(label, "Unknown")


# ── DietRecommendationEngine ──────────────────────────────────────────────────
class DietRecommendationEngine:
    CONDITION_FOODS = {
        "diabetes":    {"include":["Oats","Bitter Melon","Fenugreek","Guava","Lentils","Jamun"],
                        "avoid":["White rice (excess)","Sugary drinks","Refined sugar"],
                        "note":"Low GI diet. 5-6 small meals."},
        "hypertension":{"include":["Beetroot","Garlic","Banana","Flaxseeds","Oats","Spinach"],
                        "avoid":["Excess salt (>2g Na/day)","Processed foods","Alcohol excess"],
                        "note":"DASH diet. Target <2.3g sodium/day."},
        "chronic_kidney_disease":{"include":["White rice","Apple","Cabbage","Egg white"],
                                   "avoid":["Banana","Tomato","Beans","Nuts","Salt substitutes"],
                                   "note":"Restrict K+, P, Na, protein. Dietitian referral essential."},
        "anaemia":     {"include":["Spinach","Lentils","Moringa","Beetroot","Pomegranate","Jaggery"],
                        "avoid":["Tea/coffee with meals"],
                        "note":"Combine iron with Vit C (lemon). Cook in iron vessel."},
        "obesity":     {"include":["Oats","Bottle gourd","Leafy greens","Flaxseeds","Lentils"],
                        "avoid":["Fried foods","Sugary drinks","Refined carbs"],
                        "note":"High fibre, low calorie density."},
        "cardiac":     {"include":["Oats","Garlic","Pomegranate","Flaxseeds","Olive oil","Walnuts"],
                        "avoid":["Trans fats","Excess saturated fat","Processed meats"],
                        "note":"Mediterranean or DASH diet."},
    }

    def generate_plan(self, patient: Dict) -> Dict:
        from clinical_engine import ClinicalCalculator, Gender
        gender = Gender.MALE if patient.get("gender","male").lower()=="male" else Gender.FEMALE
        bmr  = ClinicalCalculator.harris_benedict_bmr(
            patient.get("weight_kg",70), patient.get("height_cm",170), patient.get("age",50), gender)
        tdee = ClinicalCalculator.tdee(bmr, patient.get("activity_level","moderate"))
        goal = patient.get("goal","maintain")
        cal  = int(tdee - 500 if goal=="lose" else tdee + 300 if goal=="gain" else tdee)
        conditions = [c.lower() for c in patient.get("conditions",[])]
        cp = (0.40,0.30,0.30) if "diabetes" in conditions else \
             (0.55,0.15,0.30) if "chronic_kidney_disease" in conditions else (0.50,0.25,0.25)
        plan = {
            "calories_target": cal, "bmr": round(bmr), "tdee": round(tdee),
            "macros": {"carbohydrates_g":round(cal*cp[0]/4),"protein_g":round(cal*cp[1]/4),
                       "fat_g":round(cal*cp[2]/9),"fiber_g":25},
            "meals": {"breakfast":"Oatmeal + berries + flaxseeds + green tea",
                      "morning_snack":"Handful nuts + amla",
                      "lunch":"Brown rice + dal + 2 sabzis + curd + salad",
                      "evening_snack":"Roasted chana + coconut water",
                      "dinner":"Grilled protein + steamed vegetables + small rice",
                      "note":f"Total ~{cal} kcal/day. Consult dietitian."},
            "condition_specific": {c: self.CONDITION_FOODS[c] for c in conditions if c in self.CONDITION_FOODS},
            "hydration": f"{round(patient.get('weight_kg',70)*0.033,1)} L/day minimum",
        }
        return plan


# ── LabInterpreter ────────────────────────────────────────────────────────────
class LabInterpreter:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def interpret(self, test_name, value, gender="male", age=40):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM lab_reference_ranges WHERE test_name=? OR abbreviation=?",
                    (test_name, test_name))
        ref = cur.fetchone()
        result = {"test": test_name, "value": value}
        if not ref:
            result["status"] = "Reference range not found in database"
            return result
        lo = ref["min_adult_female"] if gender.lower()=="female" else ref["min_adult_male"]
        hi = ref["max_adult_female"] if gender.lower()=="female" else ref["max_adult_male"]
        if age < 18:
            lo, hi = ref["min_child"], ref["max_child"]
        result["unit"]            = ref["unit"]
        result["reference_range"] = f"{lo} – {hi} {ref['unit']}"
        crit_lo, crit_hi          = ref["critical_low"], ref["critical_high"]
        if crit_lo and value <= crit_lo:  result["status"] = "🚨 CRITICAL LOW"
        elif crit_hi and value >= crit_hi:result["status"] = "🚨 CRITICAL HIGH"
        elif lo and value < lo:           result["status"] = "🔴 LOW"
        elif hi and value > hi:           result["status"] = "🔴 HIGH"
        else:                             result["status"] = "✅ Normal"
        result["clinical_meaning"] = ref["clinical_meaning"]
        if ref["drug_effects"]:
            try:   result["drugs_affecting_this_test"] = json.loads(ref["drug_effects"])
            except: pass
        return result


# ── VisualisationEngine ───────────────────────────────────────────────────────
class VisualisationEngine:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
        os.makedirs(self.output_dir, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="husl")

    def pk_concentration_time_curve(self, dose_mg, vd_l, clearance_l_h,
                                     interval_h=12, n_doses=5, drug_name="Drug"):
        ke   = clearance_l_h / vd_l
        time = np.linspace(0, interval_h * n_doses, 500)
        conc = np.zeros(len(time))
        for d in range(n_doses):
            t0 = d * interval_h
            for i, t in enumerate(time):
                if t >= t0:
                    conc[i] += (dose_mg/vd_l) * np.exp(-ke*(t-t0))
        fig, ax = plt.subplots(figsize=(12,6))
        ax.plot(time, conc, color="#2980b9", linewidth=2.5)
        ax.fill_between(time, conc, alpha=0.25, color="#2980b9")
        ax.set_xlabel("Time (hours)"); ax.set_ylabel("Concentration (mg/L)")
        ax.set_title(f"{drug_name} — PK Simulation\nDose={dose_mg}mg q{interval_h}h | t½={0.693/ke:.1f}h",
                     fontsize=13, fontweight="bold")
        plt.tight_layout()
        path = os.path.join(self.output_dir, f"pk_{drug_name.replace(' ','_')}.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path

    def medication_category_distribution(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        df = pd.read_sql("SELECT category, COUNT(*) as count FROM medications GROUP BY category", conn)
        conn.close()
        fig, axes = plt.subplots(1,2,figsize=(14,7))
        colors = sns.color_palette("tab20", len(df))
        axes[0].pie(df["count"], labels=df["category"], autopct="%1.1f%%", colors=colors, startangle=140)
        axes[0].set_title("Medication Categories", fontweight="bold")
        df.sort_values("count").plot(kind="barh", x="category", y="count", ax=axes[1], color=colors)
        axes[1].set_title("Count per Category", fontweight="bold")
        plt.tight_layout()
        path = os.path.join(self.output_dir, "medication_categories.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path

    def interaction_heatmap(self, interactions_df: pd.DataFrame):
        sev_num = {"Minor":1,"Moderate":2,"Major":3,"Contraindicated":4}
        interactions_df["sev_num"] = interactions_df["severity"].map(sev_num)
        pivot = interactions_df.pivot_table(index="drug_a", columns="drug_b",
                                             values="sev_num", aggfunc="max").fillna(0)
        fig, ax = plt.subplots(figsize=(12,10))
        sns.heatmap(pivot, annot=True, fmt=".0f", cmap="RdYlGn_r", vmin=0, vmax=4, ax=ax)
        ax.set_title("Drug Interaction Heatmap", fontsize=14, fontweight="bold")
        plt.tight_layout()
        path = os.path.join(self.output_dir, "interaction_heatmap.png")
        fig.savefig(path, dpi=150); plt.close(fig)
        return path

    def risk_gauge_plotly(self, risk_prob: float, patient_id="Patient"):
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=round(risk_prob*100, 1),
            domain={"x":[0,1],"y":[0,1]},
            title={"text":f"Risk Score — {patient_id}","font":{"size":20}},
            gauge={"axis":{"range":[0,100]},
                   "bar":{"color":"darkblue"},
                   "steps":[{"range":[0,30],"color":"#27ae60"},
                              {"range":[30,60],"color":"#f39c12"},
                              {"range":[60,100],"color":"#e74c3c"}],
                   "threshold":{"line":{"color":"red","width":4},"thickness":0.75,"value":60}},
        ))
        return fig


# ── Train all models ──────────────────────────────────────────────────────────
def train_all_models():
    log.info("Training all ML models...")
    PatientRiskModel().train()
    DrugInteractionPredictor().train()
    log.info("✅ All ML models saved to %s", MODELS_DIR)


if __name__ == "__main__":
    train_all_models()
    prm = PatientRiskModel()
    r = prm.predict({"age":72,"weight_kg":75,"egfr":28,"albumin":2.8,"med_count":9,
                     "comorbidity_count":4,"hba1c":8.5,"crp":85,"wbc":12,
                     "heart_rate":95,"sbp":165,"is_pm_cyp2d6":0,"is_pm_cyp2c19":0,
                     "is_elderly":1,"has_renal_impairment":1,"has_diabetes":1,"has_cardiac":1})
    print(json.dumps(r, indent=2))
