"""
seed_lab_ranges.py — Lab reference ranges seeder
"""
import sqlite3, json, logging
from db_config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

LAB_RANGES = [
    # ── HAEMATOLOGY ──────────────────────────────────────────────────────────
    {"test_name":"Haemoglobin","abbreviation":"Hb","category":"Haematology","unit":"g/dL",
     "min_adult_male":13.5,"max_adult_male":17.5,"min_adult_female":12.0,"max_adult_female":16.0,
     "min_child":11.0,"max_child":16.0,"critical_low":7.0,"critical_high":20.0,
     "clinical_meaning":"Oxygen-carrying protein in RBCs. Low = anaemia. High = polycythaemia.",
     "drug_effects":json.dumps(["Iron supplements ↑","ESAs (erythropoietin) ↑","Chemotherapy ↓","Hydroxyurea ↓","Methotrexate ↓"])},

    {"test_name":"White Blood Cell Count","abbreviation":"WBC","category":"Haematology","unit":"×10⁹/L",
     "min_adult_male":4.0,"max_adult_male":11.0,"min_adult_female":4.0,"max_adult_female":11.0,
     "min_child":5.0,"max_child":15.0,"critical_low":2.0,"critical_high":30.0,
     "clinical_meaning":"Immune cells. High = infection/inflammation/leukaemia. Low = immunosuppression/myelosuppression.",
     "drug_effects":json.dumps(["G-CSF (filgrastim) ↑","Corticosteroids ↑ (demargination)","Chemotherapy ↓","Clozapine ↓","Carbamazepine ↓","Methotrexate ↓"])},

    {"test_name":"Platelet Count","abbreviation":"PLT","category":"Haematology","unit":"×10⁹/L",
     "min_adult_male":150,"max_adult_male":400,"min_adult_female":150,"max_adult_female":400,
     "min_child":150,"max_child":450,"critical_low":50,"critical_high":1000,
     "clinical_meaning":"Clotting cells. Low = bleeding risk. Very high = thrombosis/reactive.",
     "drug_effects":json.dumps(["Heparin ↓ (HIT)","Quinine ↓","Valproate ↓","Linezolid ↓","Chemotherapy ↓","Thrombopoietin analogues ↑"])},

    {"test_name":"Neutrophil Count (Absolute)","abbreviation":"ANC","category":"Haematology","unit":"×10⁹/L",
     "min_adult_male":1.8,"max_adult_male":7.5,"min_adult_female":1.8,"max_adult_female":7.5,
     "min_child":1.5,"max_child":8.5,"critical_low":0.5,"critical_high":None,
     "clinical_meaning":"<0.5 = severe neutropenia (febrile neutropenia risk). Mandatory monitoring for clozapine.",
     "drug_effects":json.dumps(["G-CSF ↑","Clozapine ↓ (REMS monitoring)","Carbamazepine ↓","Chemotherapy ↓"])},

    {"test_name":"Reticulocyte Count","abbreviation":"Retics","category":"Haematology","unit":"%",
     "min_adult_male":0.5,"max_adult_male":2.5,"min_adult_female":0.5,"max_adult_female":2.5,
     "min_child":0.5,"max_child":3.5,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Immature RBCs. High = haemolysis/blood loss/iron/B12/folate response. Low = aplasia.",
     "drug_effects":json.dumps(["Iron/B12/Folate supplements ↑ (if deficient)","Hydroxyurea ↑ MCV (MCV rises with HU compliance)"])},

    {"test_name":"Erythrocyte Sedimentation Rate","abbreviation":"ESR","category":"Haematology","unit":"mm/h",
     "min_adult_male":0,"max_adult_male":15,"min_adult_female":0,"max_adult_female":20,
     "min_child":0,"max_child":10,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Non-specific inflammation marker. Very high (>100) suggests serious infection, malignancy, vasculitis, myeloma.",
     "drug_effects":json.dumps(["NSAIDs ↓","Corticosteroids ↓","OCP ↑"])},

    # ── BIOCHEMISTRY / CHEMISTRY ────────────────────────────────────────────
    {"test_name":"Sodium","abbreviation":"Na","category":"Electrolytes","unit":"mEq/L",
     "min_adult_male":136,"max_adult_male":145,"min_adult_female":136,"max_adult_female":145,
     "min_child":135,"max_child":145,"critical_low":120,"critical_high":160,
     "clinical_meaning":"Principal extracellular cation. Low (hyponatraemia) = SIADH, heart failure, diuretics. High = dehydration.",
     "drug_effects":json.dumps(["Thiazide/loop diuretics ↓","SSRIs/SNRIs (SIADH) ↓","Carbamazepine (SIADH) ↓","Hypertonic saline ↑","Demeclocycline ↑ (treat SIADH)"])},

    {"test_name":"Potassium","abbreviation":"K","category":"Electrolytes","unit":"mEq/L",
     "min_adult_male":3.5,"max_adult_male":5.0,"min_adult_female":3.5,"max_adult_female":5.0,
     "min_child":3.5,"max_child":5.5,"critical_low":2.5,"critical_high":6.5,
     "clinical_meaning":"Intracellular cation. Cardiac rhythm dependent on K+. Critical values require IMMEDIATE action.",
     "drug_effects":json.dumps(["ACE-I/ARBs/K-sparing diuretics ↑","Spironolactone ↑","Digoxin toxicity worsened by hypokalaemia","Thiazides/loops/β2-agonists ↓","Insulin ↓","Salbutamol ↓"])},

    {"test_name":"Chloride","abbreviation":"Cl","category":"Electrolytes","unit":"mEq/L",
     "min_adult_male":98,"max_adult_male":106,"min_adult_female":98,"max_adult_female":106,
     "min_child":97,"max_child":107,"critical_low":80,"critical_high":120,
     "clinical_meaning":"Follows sodium. Low = metabolic alkalosis (vomiting, diuretics). Evaluate with anion gap.",
     "drug_effects":json.dumps(["Loop diuretics ↓","Vomiting → ↓"])},

    {"test_name":"Bicarbonate","abbreviation":"HCO3","category":"Electrolytes","unit":"mEq/L",
     "min_adult_male":22,"max_adult_male":29,"min_adult_female":22,"max_adult_female":29,
     "min_child":18,"max_child":25,"critical_low":10,"critical_high":40,
     "clinical_meaning":"Acid-base buffer. Low = metabolic acidosis. High = metabolic alkalosis. Interpret with pH and pCO2.",
     "drug_effects":json.dumps(["Sodium bicarbonate ↑","Acetazolamide ↓","Metformin (lactic acidosis) ↓","Topiramate ↓"])},

    {"test_name":"Creatinine","abbreviation":"Cr","category":"Renal","unit":"mg/dL",
     "min_adult_male":0.7,"max_adult_male":1.2,"min_adult_female":0.5,"max_adult_female":1.0,
     "min_child":0.3,"max_child":0.7,"critical_low":None,"critical_high":10.0,
     "clinical_meaning":"Muscle metabolism byproduct. Marker of GFR. Use CKD-EPI to calculate eGFR.",
     "drug_effects":json.dumps(["Cimetidine ↑ (blocks tubular secretion)","Trimethoprim ↑","NSAIDs ↑ (renal vasoconstriction)","Contrast media ↑","Aminoglycosides ↑"])},

    {"test_name":"Blood Urea Nitrogen","abbreviation":"BUN","category":"Renal","unit":"mg/dL",
     "min_adult_male":7,"max_adult_male":20,"min_adult_female":7,"max_adult_female":20,
     "min_child":5,"max_child":18,"critical_low":None,"critical_high":100,
     "clinical_meaning":"Protein catabolism product. High = renal failure, dehydration, upper GI bleed, high protein diet. BUN:Cr ratio >20 = pre-renal.",
     "drug_effects":json.dumps(["Tetracyclines ↑","Corticosteroids ↑","NSAIDs ↑"])},

    {"test_name":"Uric Acid","abbreviation":"UA","category":"Renal","unit":"mg/dL",
     "min_adult_male":3.4,"max_adult_male":7.0,"min_adult_female":2.4,"max_adult_female":6.0,
     "min_child":2.0,"max_child":5.5,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Purine metabolism end product. >7 = hyperuricaemia. Gout attacks typically at >8-9. Treat to <6 in gout.",
     "drug_effects":json.dumps(["Allopurinol/febuxostat ↓","Thiazide diuretics ↑","Aspirin (low-dose) ↑","Ciclosporin ↑","Pyrazinamide ↑","Probenecid ↓"])},

    {"test_name":"Glucose (Fasting)","abbreviation":"FBG","category":"Metabolic","unit":"mg/dL",
     "min_adult_male":70,"max_adult_male":99,"min_adult_female":70,"max_adult_female":99,
     "min_child":70,"max_child":100,"critical_low":50,"critical_high":600,
     "clinical_meaning":"100-125 = pre-diabetes. ≥126 fasting = diabetes. Critical low = neuroglycopenia.",
     "drug_effects":json.dumps(["Corticosteroids ↑","Thiazides ↑","Antipsychotics ↑","Insulin ↓","Metformin ↓","GLP-1 RA ↓","SGLT-2 inhibitors ↓","Beta-blockers (mask hypoglycaemia)"])},

    {"test_name":"HbA1c","abbreviation":"HbA1c","category":"Metabolic","unit":"%",
     "min_adult_male":4.0,"max_adult_male":5.6,"min_adult_female":4.0,"max_adult_female":5.6,
     "min_child":4.0,"max_child":5.6,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Average glucose last 2-3 months. 5.7-6.4% = pre-DM. ≥6.5% = DM. Target usually <7% (individualise). ≥10% = very poor control.",
     "drug_effects":json.dumps(["Insulin ↓","Metformin ↓","GLP-1 RA ↓","SGLT-2i ↓","Erythropoietin (falsely lowers — faster RBC turnover)","Haemolysis falsely lowers HbA1c"])},

    {"test_name":"Total Cholesterol","abbreviation":"TC","category":"Lipids","unit":"mg/dL",
     "min_adult_male":0,"max_adult_male":199,"min_adult_female":0,"max_adult_female":199,
     "min_child":0,"max_child":169,"critical_low":None,"critical_high":None,
     "clinical_meaning":"<200 desirable. 200-239 borderline. ≥240 high. Interpret with LDL, HDL, TG, cardiac risk.",
     "drug_effects":json.dumps(["Statins ↓ 30-50%","Ezetimibe ↓","PCSK9 inhibitors ↓↓","Fibrates ↓ (mainly TG)","Thiazides ↑","Ciclosporin ↑","Oestrogens ↑ (TG mainly)"])},

    {"test_name":"LDL Cholesterol","abbreviation":"LDL","category":"Lipids","unit":"mg/dL",
     "min_adult_male":0,"max_adult_male":129,"min_adult_female":0,"max_adult_female":129,
     "min_child":0,"max_child":109,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Primary target for CVD prevention. <70 in very high risk (prior CVD/diabetes). <55 in extreme risk.",
     "drug_effects":json.dumps(["Statins ↓ 30-55%","Ezetimibe ↓ 15-20%","PCSK9 inhibitors ↓ 60%","Bile acid sequestrants ↓","Fibrates ↑ (slight) or neutral"])},

    {"test_name":"HDL Cholesterol","abbreviation":"HDL","category":"Lipids","unit":"mg/dL",
     "min_adult_male":40,"max_adult_male":None,"min_adult_female":50,"max_adult_female":None,
     "min_child":40,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Protective. <40 male/<50 female = low (CVD risk factor). Exercise ↑ HDL. Hard to raise with drugs.",
     "drug_effects":json.dumps(["Fibrates ↑","Niacin ↑","Statins ↑ modest","Beta-blockers ↓","Thiazides ↓","Smoking ↓"])},

    {"test_name":"Triglycerides","abbreviation":"TG","category":"Lipids","unit":"mg/dL",
     "min_adult_male":0,"max_adult_male":149,"min_adult_female":0,"max_adult_female":149,
     "min_child":0,"max_child":99,"critical_low":None,"critical_high":500,
     "clinical_meaning":"150-199 borderline. 200-499 high. ≥500 = pancreatitis risk. Fasting sample essential.",
     "drug_effects":json.dumps(["Fibrates ↓ 30-50%","Omega-3 FA ↓","Statins ↓ 20-30%","Corticosteroids ↑","Atypical antipsychotics ↑","Oestrogens ↑","Alcohol ↑","Thiazides ↑"])},

    # ── LIVER FUNCTION ───────────────────────────────────────────────────────
    {"test_name":"Alanine Aminotransferase","abbreviation":"ALT","category":"LFTs","unit":"IU/L",
     "min_adult_male":0,"max_adult_male":40,"min_adult_female":0,"max_adult_female":35,
     "min_child":0,"max_child":30,"critical_low":None,"critical_high":1000,
     "clinical_meaning":"Liver-specific enzyme. Best marker of hepatocellular damage. >3x ULN = significant. >10x = severe hepatitis.",
     "drug_effects":json.dumps(["Paracetamol (overdose) massive ↑","Statins ↑ (usually mild)","Methotrexate ↑","Isoniazid ↑","Fluconazole ↑","Valproate ↑","Nitrofurantoin ↑"])},

    {"test_name":"Aspartate Aminotransferase","abbreviation":"AST","category":"LFTs","unit":"IU/L",
     "min_adult_male":0,"max_adult_male":40,"min_adult_female":0,"max_adult_female":35,
     "min_child":0,"max_child":40,"critical_low":None,"critical_high":1000,
     "clinical_meaning":"Less liver-specific (also cardiac, muscle). AST:ALT >2:1 = alcoholic hepatitis. Massive rise (>1000) = ischaemia or paracetamol.",
     "drug_effects":json.dumps(["Same as ALT"])},

    {"test_name":"Alkaline Phosphatase","abbreviation":"ALP","category":"LFTs","unit":"IU/L",
     "min_adult_male":40,"max_adult_male":130,"min_adult_female":35,"max_adult_female":105,
     "min_child":0,"max_child":350,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Biliary obstruction, bone disease (Paget's), liver infiltration. High in children (bone growth). Isolated high ALP → check GGT.",
     "drug_effects":json.dumps(["Phenytoin/Carbamazepine ↑","Oestrogens ↑ (cholestasis)","Statins mild ↑"])},

    {"test_name":"Gamma-Glutamyl Transferase","abbreviation":"GGT","category":"LFTs","unit":"IU/L",
     "min_adult_male":0,"max_adult_male":60,"min_adult_female":0,"max_adult_female":40,
     "min_child":0,"max_child":25,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Very sensitive hepatic enzyme. Raised with alcohol, liver disease, cholestasis, enzyme inducers. Confirms hepatic origin of raised ALP.",
     "drug_effects":json.dumps(["Alcohol ↑ (very sensitive)","Enzyme inducers (carbamazepine, rifampicin, phenytoin) ↑","Statins mild ↑"])},

    {"test_name":"Bilirubin Total","abbreviation":"Bili","category":"LFTs","unit":"mg/dL",
     "min_adult_male":0.2,"max_adult_male":1.2,"min_adult_female":0.2,"max_adult_female":1.0,
     "min_child":0.2,"max_child":1.0,"critical_low":None,"critical_high":15.0,
     "clinical_meaning":"<1.2 normal. Jaundice visible at >2.5. Pre-hepatic (haemolysis) = unconjugated ↑. Hepatocellular/obstructive = conjugated ↑.",
     "drug_effects":json.dumps(["Atazanavir/Indinavir ↑ (inhibit UGT1A1 → unconjugated)","Rifampicin ↑","Haemolytic drugs ↑"])},

    {"test_name":"Albumin","abbreviation":"Alb","category":"LFTs","unit":"g/dL",
     "min_adult_male":3.5,"max_adult_male":5.0,"min_adult_female":3.5,"max_adult_female":5.0,
     "min_child":3.0,"max_child":5.0,"critical_low":2.0,"critical_high":None,
     "clinical_meaning":"Liver synthetic function, nutrition, chronic disease. Affects protein binding of many drugs (phenytoin, warfarin). Corrected calcium needed when low.",
     "drug_effects":json.dumps(["Albumin infusion ↑ (short-term)","Malnutrition ↓","Chronic inflammation ↓"])},

    # ── COAGULATION ───────────────────────────────────────────────────────────
    {"test_name":"INR (International Normalised Ratio)","abbreviation":"INR","category":"Coagulation","unit":"ratio",
     "min_adult_male":0.8,"max_adult_male":1.2,"min_adult_female":0.8,"max_adult_female":1.2,
     "min_child":0.8,"max_child":1.2,"critical_low":None,"critical_high":5.0,
     "clinical_meaning":"Warfarin monitoring: target 2-3 (most), 2.5-3.5 (mechanical valves). >5 = serious over-anticoagulation. Liver disease causes raised INR.",
     "drug_effects":json.dumps(["Warfarin ↑ (intended)","Vitamin K ↓","Antibiotics ↑ (reduce gut flora producing Vit K)","NSAIDs/aspirin ↑ (bleeding risk)","Antifungals ↑ (CYP2C9 inhibition)","Rifampicin ↓ (CYP induction)"])},

    {"test_name":"APTT (Activated Partial Thromboplastin Time)","abbreviation":"APTT","category":"Coagulation","unit":"seconds",
     "min_adult_male":25,"max_adult_male":35,"min_adult_female":25,"max_adult_female":35,
     "min_child":25,"max_child":40,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Intrinsic pathway. Monitors unfractionated heparin (target 1.5-2.5x control). Prolonged in haemophilia, lupus anticoagulant, liver disease.",
     "drug_effects":json.dumps(["Unfractionated heparin ↑ (intended)","Dabigatran ↑","Argatroban ↑","Direct thrombin inhibitors ↑"])},

    {"test_name":"D-Dimer","abbreviation":"D-dimer","category":"Coagulation","unit":"ng/mL",
     "min_adult_male":0,"max_adult_male":500,"min_adult_female":0,"max_adult_female":500,
     "min_child":0,"max_child":500,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Fibrin degradation product. High sensitivity (NPV 99%) for DVT/PE but low specificity. Age-adjusted cutoff = age×10 in patients >50 years.",
     "drug_effects":json.dumps(["Anticoagulation ↓ (treatment)","False ↑ with: infection, cancer, pregnancy, post-surgery"])},

    # ── THYROID ───────────────────────────────────────────────────────────────
    {"test_name":"Thyroid Stimulating Hormone","abbreviation":"TSH","category":"Thyroid","unit":"mIU/L",
     "min_adult_male":0.4,"max_adult_male":4.0,"min_adult_female":0.4,"max_adult_female":4.0,
     "min_child":0.7,"max_child":6.4,"critical_low":0.01,"critical_high":20.0,
     "clinical_meaning":"Best thyroid screening test. Low = hyperthyroid (primary) or pituitary. High = hypothyroid. Target 0.5-2.5 on levothyroxine. Pregnancy: lower targets.",
     "drug_effects":json.dumps(["Levothyroxine ↓ (if over-replaced)","Amiodarone ↑ or ↓","Lithium ↑ (hypothyroidism)","Rifampicin ↑ (increases T4 metabolism)","Biotin (falsely ↓ — discontinue 2 days before test)","Antithyroid drugs ↑"])},

    {"test_name":"Free T4","abbreviation":"fT4","category":"Thyroid","unit":"ng/dL",
     "min_adult_male":0.8,"max_adult_male":1.8,"min_adult_female":0.8,"max_adult_female":1.8,
     "min_child":0.7,"max_child":2.0,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Active thyroid hormone. Low + high TSH = hypothyroid. High + low TSH = hyperthyroid.",
     "drug_effects":json.dumps(["Levothyroxine ↑","Amiodarone ↑ (inhibits T4→T3)","Heparin (falsely ↑ in vitro)","Phenytoin ↓ (displaces from binding)"])},

    {"test_name":"Free T3","abbreviation":"fT3","category":"Thyroid","unit":"pg/mL",
     "min_adult_male":2.3,"max_adult_male":4.2,"min_adult_female":2.3,"max_adult_female":4.2,
     "min_child":1.8,"max_child":4.6,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Active thyroid hormone (3-4x more potent than T4). Raised in T3 thyrotoxicosis. Low in non-thyroidal illness (sick euthyroid).",
     "drug_effects":json.dumps(["Amiodarone ↓ (blocks T4→T3 conversion)","Propranolol ↓ T3 (blocks peripheral conversion)"])},

    # ── CARDIAC ───────────────────────────────────────────────────────────────
    {"test_name":"Troponin I (High Sensitivity)","abbreviation":"hsTnI","category":"Cardiac","unit":"ng/L",
     "min_adult_male":0,"max_adult_male":15.6,"min_adult_female":0,"max_adult_female":9.0,
     "min_child":0,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Cardiac myocyte necrosis marker. Rise + fall pattern = NSTEMI. Highly sensitive — also rises in AKI, PE, heart failure, myocarditis.",
     "drug_effects":json.dumps(["Cardiotoxic chemotherapy (doxorubicin, trastuzumab) ↑","Cocaine ↑"])},

    {"test_name":"BNP (B-type Natriuretic Peptide)","abbreviation":"BNP","category":"Cardiac","unit":"pg/mL",
     "min_adult_male":0,"max_adult_male":100,"min_adult_female":0,"max_adult_female":100,
     "min_child":0,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"<100 = HF unlikely. 100-400 = grey zone. >400 = HF likely. Guides diuretic therapy. Rises with renal failure.",
     "drug_effects":json.dumps(["Diuretics ↓","ACE-I/ARBs ↓","Sacubitril/Valsartan (Neprilysin inhibitor) ↑ BNP but ↓ NT-proBNP","Spironolactone ↓"])},

    {"test_name":"NT-proBNP","abbreviation":"NT-proBNP","category":"Cardiac","unit":"pg/mL",
     "min_adult_male":0,"max_adult_male":125,"min_adult_female":0,"max_adult_female":125,
     "min_child":0,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Age-adjusted cutoffs: <50y: <450; 50-75y: <900; >75y: <1800. Longer half-life than BNP.",
     "drug_effects":json.dumps(["Sacubitril/valsartan ↓","Diuretics ↓"])},

    {"test_name":"Creatine Kinase","abbreviation":"CK","category":"Cardiac","unit":"IU/L",
     "min_adult_male":22,"max_adult_male":200,"min_adult_female":22,"max_adult_female":170,
     "min_child":0,"max_child":200,"critical_low":None,"critical_high":1000,
     "clinical_meaning":"Muscle enzyme. High = myocardial infarction (CK-MB fraction), myopathy/rhabdomyolysis, IM injection. >10x ULN = rhabdomyolysis.",
     "drug_effects":json.dumps(["Statins ↑ (myopathy)","Fibrates + statins ↑↑","Antipsychotics ↑ (NMS)","Cocaine ↑","Colchicine + statins ↑"])},

    # ── HORMONES & MISC ───────────────────────────────────────────────────────
    {"test_name":"Cortisol (Morning)","abbreviation":"Cortisol","category":"Hormones","unit":"mcg/dL",
     "min_adult_male":6,"max_adult_male":23,"min_adult_female":6,"max_adult_female":23,
     "min_child":3,"max_child":21,"critical_low":3.0,"critical_high":None,
     "clinical_meaning":"9AM sample. <3 = adrenal insufficiency (confirm with synacthen). >23 = cushing's (24h UFC or dexamethasone suppression test).",
     "drug_effects":json.dumps(["Corticosteroids ↓ endogenous (HPA suppression)","OCP ↑ (raises cortisol-binding globulin — total cortisol)"])},

    {"test_name":"Testosterone (Total)","abbreviation":"Testosterone","category":"Hormones","unit":"ng/dL",
     "min_adult_male":264,"max_adult_male":916,"min_adult_female":15,"max_adult_female":70,
     "min_child":0,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"<264 in males = hypogonadism. >70 in females = PCOS/androgen excess. Sample in morning (diurnal variation).",
     "drug_effects":json.dumps(["Anabolic steroids ↑","Ketoconazole ↓","Opioids ↓","Finasteride ↑ testosterone (↓ DHT)","GnRH analogues ↓","Spironolactone ↓"])},

    {"test_name":"Ferritin","abbreviation":"Ferritin","category":"Haematology","unit":"ng/mL",
     "min_adult_male":12,"max_adult_male":300,"min_adult_female":12,"max_adult_female":150,
     "min_child":7,"max_child":140,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Iron stores marker. <12 = iron deficiency. Acute phase reactant (falsely normal/high in infection/inflammation). Target >100 + TSAT>20% for anaemia of CKD.",
     "drug_effects":json.dumps(["Iron supplements ↑","Erythropoietin (depletes stores — needs iron supplementation)","Repeated transfusions ↑"])},

    {"test_name":"Serum Iron","abbreviation":"Fe","category":"Haematology","unit":"mcg/dL",
     "min_adult_male":60,"max_adult_male":170,"min_adult_female":50,"max_adult_female":150,
     "min_child":50,"max_child":120,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Diurnal variation (higher morning). Low + high TIBC = iron deficiency. Low + low TIBC = anaemia of chronic disease.",
     "drug_effects":json.dumps(["Iron supplements ↑","Antacids (reduce absorption)","Tetracyclines/quinolones (chelate iron — 2h gap)","Methyldopa (chelates)"])},

    {"test_name":"C-Reactive Protein","abbreviation":"CRP","category":"Inflammatory","unit":"mg/L",
     "min_adult_male":0,"max_adult_male":5,"min_adult_female":0,"max_adult_female":5,
     "min_child":0,"max_child":5,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Acute phase reactant. <1 = low CVD risk (hsCRP). >10 = significant inflammation/infection. >100 = serious infection (sepsis, empyema, osteomyelitis).",
     "drug_effects":json.dumps(["Statins ↓ (anti-inflammatory effect)","NSAIDs ↓","Corticosteroids ↓","OCP ↑"])},

    {"test_name":"Vancomycin Trough Level","abbreviation":"Vanc-trough","category":"TDM","unit":"mg/L",
     "min_adult_male":10,"max_adult_male":20,"min_adult_female":10,"max_adult_female":20,
     "min_child":10,"max_child":20,"critical_low":None,"critical_high":None,
     "clinical_meaning":"OLD target. NEW (2020 ASHP guidelines): AUC/MIC 400-600 preferred. If trough only: 10-15 mg/L for most; 15-20 for MRSA/severe.",
     "drug_effects":json.dumps(["Vancomycin — monitor for nephrotoxicity + ototoxicity","Loop diuretics increase nephrotoxicity risk"])},

    {"test_name":"Digoxin Level","abbreviation":"Dig","category":"TDM","unit":"ng/mL",
     "min_adult_male":0.5,"max_adult_male":2.0,"min_adult_female":0.5,"max_adult_female":2.0,
     "min_child":0.5,"max_child":2.0,"critical_low":None,"critical_high":2.0,
     "clinical_meaning":"Sample 6-12h post-dose. AF rate control: 0.5-1.0. HF: 0.5-0.8 preferred (mortality benefit range). >2 = toxic range.",
     "drug_effects":json.dumps(["Amiodarone ↑ (doubles level)","Clarithromycin/erythromycin ↑","Verapamil/diltiazem ↑","Hypokalaemia ↑ toxicity","Rifampicin ↓"])},

    {"test_name":"Lithium Level","abbreviation":"Li","category":"TDM","unit":"mEq/L",
     "min_adult_male":0.6,"max_adult_male":1.0,"min_adult_female":0.6,"max_adult_female":1.0,
     "min_child":None,"max_child":None,"critical_low":None,"critical_high":1.5,
     "clinical_meaning":"12h post-dose sample. Acute mania: 0.8-1.2. Maintenance: 0.6-0.8. Elderly: 0.4-0.6. >1.5 = toxic. >2.0 = life-threatening.",
     "drug_effects":json.dumps(["NSAIDs ↑ (reduce renal clearance — DANGEROUS)","ACE-I/ARBs ↑ (reduce clearance)","Thiazides ↑ (reduce clearance)","Caffeine ↓"])},

    {"test_name":"Phenytoin Level","abbreviation":"PHT","category":"TDM","unit":"mcg/mL",
     "min_adult_male":10,"max_adult_male":20,"min_adult_female":10,"max_adult_female":20,
     "min_child":10,"max_child":20,"critical_low":None,"critical_high":30.0,
     "clinical_meaning":"Free level 1-2 mcg/mL. Non-linear kinetics — small dose changes → large level changes. Correct for albumin in hypoalbuminaemia.",
     "drug_effects":json.dumps(["Valproate displaces → ↑ free level","Carbamazepine ↓","Fluconazole ↑","Rifampicin ↓","Shankhpushpi ↓"])},

    {"test_name":"Paracetamol Level","abbreviation":"APAP","category":"TDM","unit":"mcg/mL",
     "min_adult_male":0,"max_adult_male":None,"min_adult_female":0,"max_adult_female":None,
     "min_child":0,"max_child":None,"critical_low":None,"critical_high":None,
     "clinical_meaning":"4h post-ingestion level interpreted on Rumack-Matthew nomogram. >150 mcg/mL at 4h = treatment with acetylcysteine indicated.",
     "drug_effects":json.dumps(["N-Acetylcysteine (antidote — treatment)"])},

    {"test_name":"International Normalised Ratio (Therapeutic)","abbreviation":"INR_tx","category":"Coagulation","unit":"ratio",
     "min_adult_male":2.0,"max_adult_male":3.0,"min_adult_female":2.0,"max_adult_female":3.0,
     "min_child":None,"max_child":None,"critical_low":None,"critical_high":5.0,
     "clinical_meaning":"THERAPEUTIC range for warfarin. AF/DVT/PE: 2.0-3.0. Mechanical valve: 2.5-3.5. >5 = over-anticoagulated.",
     "drug_effects":json.dumps(["Warfarin (intended)","Antibiotics ↑ (gut flora)","Antifungals ↑","Rifampicin ↓","St John's Wort ↓","Vitamin K foods ↓"])},

    {"test_name":"Procalcitonin","abbreviation":"PCT","category":"Inflammatory","unit":"ng/mL",
     "min_adult_male":0,"max_adult_male":0.1,"min_adult_female":0,"max_adult_female":0.1,
     "min_child":0,"max_child":0.5,"critical_low":None,"critical_high":None,
     "clinical_meaning":"Biomarker for bacterial infection and sepsis. <0.1 = unlikely bacterial infection. >0.5 = likely bacterial. >2.0 = sepsis. Used for antibiotic stewardship.",
     "drug_effects":json.dumps(["Antibiotics ↓ (treatment response)"])},
]


def seed_lab_ranges():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    COLUMNS = [
        "test_name","abbreviation","category","unit",
        "min_adult_male","max_adult_male","min_adult_female","max_adult_female",
        "min_child","max_child","critical_low","critical_high",
        "clinical_meaning","drug_effects",
    ]

    inserted = skipped = 0
    for lab in LAB_RANGES:
        row = {c: lab.get(c) for c in COLUMNS}
        ph = ", ".join(["?"] * len(COLUMNS))
        col_str = ", ".join(COLUMNS)
        try:
            cur.execute(f"INSERT OR IGNORE INTO lab_reference_ranges ({col_str}) VALUES ({ph})",
                        [row[c] for c in COLUMNS])
            if cur.rowcount > 0:
                inserted += 1
                log.info("  ✅ %s", lab["test_name"])
            else:
                skipped += 1
        except Exception as e:
            log.error("  ❌ %s: %s", lab.get("test_name","?"), e)

    conn.commit()
    conn.close()
    log.info("\n📊 Lab Ranges — Inserted: %d | Skipped: %d | Total: %d",
             inserted, skipped, len(LAB_RANGES))


if __name__ == "__main__":
    seed_lab_ranges()
