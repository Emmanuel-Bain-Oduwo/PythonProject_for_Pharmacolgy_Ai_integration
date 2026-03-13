"""
seed_genetics.py — Pharmacogenomics database seeder
"""
import sqlite3, json, logging
from db_config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

GENETICS_DATA = [
    {
        "gene_name": "Cytochrome P450 2D6",
        "gene_symbol": "CYP2D6",
        "chromosome": "22q13.1",
        "enzyme_function": "Hepatic oxidase metabolising ~25% of all drugs. Hydroxylation.",
        "population_frequency": json.dumps({"PM": "5-10% Caucasians, 1-2% Asians", "UM": "1-2% Caucasians, 0.5% Asians", "EM": "~65-80%", "IM": "~10-15%"}),
        "affected_drugs": json.dumps(["Codeine","Tramadol","Tamoxifen","Metoprolol","Carvedilol","Fluoxetine","Paroxetine","Risperidone","Haloperidol","Tricyclics","Atomoxetine","Oxycodone"]),
        "key_variants": json.dumps({"*1": "Normal activity", "*2": "Reduced (0.5x)", "*4": "No activity (null allele — most common PM variant in Caucasians)", "*5": "Gene deletion (null)", "*10": "Reduced (most common IM in Asians)", "*17": "Reduced (African)", "*41": "Reduced (~0.5x)", "duplication": "UM — ultra-rapid metaboliser"}),
        "phenotype_consequences": json.dumps({
            "PM (Poor)": "Drug accumulation → toxicity (e.g. opioids, TCAs, metoprolol). Codeine/tramadol ineffective as prodrugs (no conversion to morphine).",
            "IM (Intermediate)": "Partial reduction in metabolism. Slightly higher levels.",
            "EM (Extensive/Normal)": "Standard drug response.",
            "UM (Ultra-rapid)": "Rapid metabolism → sub-therapeutic levels. Codeine/tramadol: rapid conversion to opioid → FATAL toxicity reported (children, post-tonsillectomy deaths).",
        }),
        "clinical_actions": json.dumps({
            "Codeine_PM": "Avoid — no analgesic effect. Use morphine/oxycodone.",
            "Codeine_UM": "CONTRAINDICATED — fatal opioid toxicity. FDA black box warning.",
            "Tamoxifen_PM": "Reduced endoxifen (active metabolite). Consider aromatase inhibitor.",
            "Metoprolol_PM": "5-10x higher plasma levels. Start 12.5-25mg; titrate slowly.",
            "TCA_PM": "Higher levels → arrhythmia/anticholinergic toxicity risk. Reduce dose.",
        }),
        "testing_indications": "Before opioid therapy (especially codeine/tramadol), tamoxifen for breast cancer, psychiatric medication selection",
        "fda_labels_with_pgx": "Codeine, Tramadol, Tamoxifen, Atomoxetine, Thioridazine",
    },
    {
        "gene_name": "Cytochrome P450 2C19",
        "gene_symbol": "CYP2C19",
        "chromosome": "10q24.1-q24.3",
        "enzyme_function": "Hepatic oxidase. Proguanil activation, clopidogrel activation, PPI metabolism, antidepressant metabolism.",
        "population_frequency": json.dumps({"PM": "2-5% Caucasians, 15-20% Asians (especially Chinese, Japanese, Korean)", "UM": "3-5% Caucasians, <1% Asians", "IM": "~25%", "EM": "~60%"}),
        "affected_drugs": json.dumps(["Clopidogrel","Omeprazole","Pantoprazole","Escitalopram","Citalopram","Sertraline","Diazepam","Phenytoin","Proguanil","Voriconazole"]),
        "key_variants": json.dumps({"*1": "Normal", "*2": "No activity (null — most common PM variant globally)", "*3": "No activity (common in Asians)", "*17": "Increased activity — UM"}),
        "phenotype_consequences": json.dumps({
            "PM (Poor)": "Clopidogrel: no antiplatelet effect (prodrug not activated). PPIs: higher drug exposure = better acid suppression. Antidepressants: higher levels.",
            "IM (Intermediate)": "Partial clopidogrel activation. Moderate response.",
            "EM (Normal)": "Standard drug response.",
            "UM (Ultra-rapid)": "PPI rapid metabolism = reduced acid suppression. Faster antidepressant clearance.",
        }),
        "clinical_actions": json.dumps({
            "Clopidogrel_PM": "CRITICAL — no platelet inhibition. Use prasugrel or ticagrelor. FDA black box warning.",
            "PPI_PM": "Higher drug levels. Advantage for H. pylori eradication (higher exposure).",
            "Voriconazole_PM": "Very high levels — toxicity risk. Reduce dose significantly.",
            "Voriconazole_UM": "Sub-therapeutic levels — treatment failure. Increase dose.",
        }),
        "testing_indications": "Before clopidogrel (ACS/PCI), voriconazole therapy, tricyclic antidepressants in certain populations",
        "fda_labels_with_pgx": "Clopidogrel (Black Box Warning), Voriconazole, Citalopram, Escitalopram",
    },
    {
        "gene_name": "Cytochrome P450 2C9",
        "gene_symbol": "CYP2C9",
        "chromosome": "10q24.2",
        "enzyme_function": "Metabolises ~15% of drugs. Warfarin (S-enantiomer), NSAIDs, phenytoin, sulfonylureas.",
        "affected_drugs": json.dumps(["Warfarin","Phenytoin","Ibuprofen","Diclofenac","Celecoxib","Glibenclamide","Losartan","Fluvastatin","Tolbutamide"]),
        "key_variants": json.dumps({"*1": "Normal", "*2": "Reduced (Ile359Leu — 30% activity)", "*3": "Severely reduced (Ile359Leu — 5% activity)", "*5,*6,*8,*11": "Loss of function — more common in sub-Saharan Africans"}),
        "phenotype_consequences": json.dumps({
            "PM (*2/*3, *3/*3)": "Warfarin: very high sensitivity — bleeding risk. Much lower maintenance dose needed. Phenytoin: toxicity at standard doses.",
            "IM (*1/*2, *1/*3)": "Moderately reduced clearance. Warfarin sensitivity increased.",
        }),
        "clinical_actions": json.dumps({
            "Warfarin_PM": "Reduce initial dose significantly (30-70%). INR monitoring essential. Use CPIC dosing algorithm (age, VKORC1, CYP2C9, CYP4F2).",
            "Phenytoin_PM": "Standard doses cause toxicity. Start low; monitor levels.",
            "NSAIDs_PM": "Higher NSAID exposure — greater GI/renal risk.",
        }),
        "testing_indications": "Warfarin initiation (combined with VKORC1), phenytoin loading, in select high-risk patients",
    },
    {
        "gene_name": "Cytochrome P450 3A4",
        "gene_symbol": "CYP3A4",
        "chromosome": "7q21.1",
        "enzyme_function": "Most abundant hepatic and intestinal CYP enzyme — metabolises ~50% of all drugs. Enormous drug interaction potential.",
        "affected_drugs": json.dumps(["Atorvastatin","Simvastatin","Imatinib","Cyclosporine","Tacrolimus","Midazolam","Fentanyl","Carbamazepine","Quetiapine","Amlodipine","Many oncology drugs"]),
        "key_variants": json.dumps({"*1B": "Slightly increased expression", "*22": "Reduced expression (~25% lower CL)"}),
        "phenotype_consequences": json.dumps({
            "General": "Genetic variation less impactful than DRUG INTERACTIONS (inducers/inhibitors). CYP3A4 is the biggest source of drug-drug and drug-food interactions.",
        }),
        "clinical_actions": json.dumps({
            "Inducers (rifampicin, carbamazepine, phenytoin, St John's Wort)": "Dramatically REDUCE levels of substrates — treatment failure",
            "Inhibitors (ketoconazole, clarithromycin, ritonavir, grapefruit juice)": "Dramatically INCREASE levels — toxicity",
        }),
        "testing_indications": "Routine genetic testing not standard — focus on drug interactions",
    },
    {
        "gene_name": "Vitamin K Epoxide Reductase Complex Subunit 1",
        "gene_symbol": "VKORC1",
        "chromosome": "16p11.2",
        "enzyme_function": "Vitamin K recycling enzyme — target of warfarin. VKORC1 variants = key determinant of warfarin sensitivity.",
        "affected_drugs": json.dumps(["Warfarin","Acenocoumarol","Phenprocoumon"]),
        "key_variants": json.dumps({"-1639G>A": "A allele = reduced VKORC1 expression = VKOR target less available = lower warfarin dose needed", "AA": "Very sensitive — low dose (~3-4mg/day)", "GA": "Intermediate (~5-6mg/day)", "GG": "Resistant (~6-7mg/day or higher"}),
        "phenotype_consequences": json.dumps({
            "AA homozygous": "Very warfarin sensitive. Standard doses cause supratherapeutic INR. Major bleeds.",
            "GG homozygous": "Warfarin resistant. May need high doses.",
        }),
        "clinical_actions": json.dumps({
            "Warfarin_dosing": "CPIC algorithm: Dose = (Target INR × Age × Height × Weight × VKORC1 × CYP2C9 × CYP4F2) → online calculator",
            "FDA_labelling": "Warfarin label includes PGx dosing table",
        }),
        "testing_indications": "Before warfarin initiation — combined VKORC1 + CYP2C9 testing reduces time to stable INR and bleeding complications",
        "fda_labels_with_pgx": "Warfarin (approved PGx dosing)",
    },
    {
        "gene_name": "Solute Carrier Organic Anion Transporter 1B1",
        "gene_symbol": "SLCO1B1",
        "chromosome": "12p12.2",
        "enzyme_function": "Hepatic uptake transporter. Transports statins into hepatocytes for clearance. *5 variant = reduced transport = higher systemic statin exposure.",
        "affected_drugs": json.dumps(["Simvastatin","Atorvastatin","Pravastatin","Rosuvastatin","Repaglinide","Methotrexate","Rifampicin"]),
        "key_variants": json.dumps({"*1": "Normal transport", "*5 (rs4149056)": "Significantly reduced transport — highest frequency 15% Caucasians, 2% Asians", "*15": "Reduced (= *5 + *1b)"}),
        "phenotype_consequences": json.dumps({
            "*5/*5 homozygous": "VERY HIGH simvastatin myopathy risk (17x increased). Major concern with high-dose simvastatin.",
            "*1/*5 heterozygous": "Moderate increased myopathy risk (~4x).",
        }),
        "clinical_actions": json.dumps({
            "Simvastatin_*5/*5": "AVOID simvastatin — use rosuvastatin or pravastatin (not significantly affected by SLCO1B1).",
            "Simvastatin_*1/*5": "Max simvastatin 20mg. Prefer alternative statin.",
            "Alternative_statins": "Rosuvastatin: minimal SLCO1B1 dependence. Pravastatin: minimal. Fluvastatin: CYP2C9 substrate instead.",
        }),
        "testing_indications": "Before high-dose simvastatin; unexplained statin myopathy/CK elevation",
        "fda_labels_with_pgx": "Simvastatin (FDA label includes SLCO1B1 myopathy risk)",
    },
    {
        "gene_name": "HLA-B allele 15:02",
        "gene_symbol": "HLA-B*15:02",
        "chromosome": "6p21.3",
        "enzyme_function": "HLA class I molecule — presents peptides to CD8+ T cells. Specific allele causes severe cutaneous adverse reactions (SCAR) with aromatic anticonvulsants.",
        "population_frequency": json.dumps({"Han Chinese": "6-8%", "South/Southeast Asians": "2-8%", "Caucasians": "<1%"}),
        "affected_drugs": json.dumps(["Carbamazepine","Oxcarbazepine","Phenytoin (weaker association)","Lamotrigine (weaker)"]),
        "phenotype_consequences": json.dumps({
            "HLA-B*15:02 positive + Carbamazepine": "100x increased risk of Stevens-Johnson Syndrome (SJS) / Toxic Epidermal Necrolysis (TEN) — 10% mortality",
        }),
        "clinical_actions": json.dumps({
            "MANDATORY_screening": "Screen ALL Han Chinese, Thai, Malay, Filipino, other SE/South Asian patients BEFORE carbamazepine/oxcarbazepine. FDA BLACK BOX WARNING.",
            "If_positive": "CONTRAINDICATED — use alternative anticonvulsant (valproate, levetiracetam, phenobarbital).",
            "If_negative": "Carbamazepine may be used but monitor for rash.",
        }),
        "testing_indications": "MANDATORY before carbamazepine in Asian populations per FDA/CPIC",
        "fda_labels_with_pgx": "Carbamazepine (Black Box Warning — Asian patients)",
    },
    {
        "gene_name": "HLA-B allele 57:01",
        "gene_symbol": "HLA-B*57:01",
        "chromosome": "6p21.3",
        "enzyme_function": "HLA class I molecule. Presents abacavir to T cells → immune-mediated hypersensitivity reaction.",
        "population_frequency": json.dumps({"Caucasians": "5-8%", "Asians": "~1%", "Africans": "1-3%"}),
        "affected_drugs": json.dumps(["Abacavir","Flucloxacillin (weak)"]),
        "phenotype_consequences": json.dumps({
            "HLA-B*57:01 positive + Abacavir": "~55% risk of hypersensitivity syndrome — fever, rash, multi-organ involvement, potentially fatal on rechallenge",
        }),
        "clinical_actions": json.dumps({
            "MANDATORY_screening": "Screen ALL patients before abacavir — standard of care globally (WHO, DHHS, EACS guidelines).",
            "If_positive": "CONTRAINDICATED — use tenofovir-based regimen instead.",
            "If_negative": "Abacavir safe to use (NPV ~100%).",
        }),
        "testing_indications": "Before ALL abacavir prescriptions — cost-effective and mandatory",
        "fda_labels_with_pgx": "Abacavir (FDA boxed warning)",
    },
    {
        "gene_name": "Thiopurine S-methyltransferase",
        "gene_symbol": "TPMT",
        "chromosome": "6p22.3",
        "enzyme_function": "Inactivates thiopurine drugs (azathioprine, 6-mercaptopurine, thioguanine) → TPMT deficiency = drug accumulation → bone marrow suppression.",
        "population_frequency": json.dumps({"Low activity (IM)": "10% (1:10 heterozygotes)", "Very low/absent (PM)": "0.3% (1:300 homozygotes)", "Normal (EM)": "~89%"}),
        "affected_drugs": json.dumps(["Azathioprine","6-Mercaptopurine","Thioguanine"]),
        "phenotype_consequences": json.dumps({
            "PM (absent TPMT)": "Thiopurine toxicity — severe, potentially fatal myelosuppression at standard doses",
            "IM (reduced TPMT)": "Intermediate risk — dose reduction needed",
        }),
        "clinical_actions": json.dumps({
            "PM": "Reduce dose by 90% or use alternative (mycophenolate, ciclosporin). Daily low-dose may be feasible but requires weekly CBC.",
            "IM": "Reduce dose by 30-70%.",
            "EM": "Standard dosing.",
        }),
        "testing_indications": "Before ALL azathioprine/6-MP therapy — MANDATORY. Either phenotyping (enzyme activity) or genotyping.",
        "fda_labels_with_pgx": "Azathioprine, 6-Mercaptopurine (FDA labelling)",
    },
    {
        "gene_name": "G6PD (Glucose-6-Phosphate Dehydrogenase)",
        "gene_symbol": "G6PD",
        "chromosome": "Xq28",
        "enzyme_function": "Protects RBCs from oxidative stress. G6PD deficiency = haemolysis with oxidant drugs.",
        "population_frequency": json.dumps({"Sub-Saharan Africans": "10-20%", "South Asians": "3-8%", "Mediterranean": "2-5%", "East Asians": "1-5%"}),
        "affected_drugs": json.dumps(["Primaquine","Chloroquine (high dose)","Dapsone","Nitrofurantoin","Ciprofloxacin","Methylene blue","Rasburicase","Pegloticase","Aspirin (high dose)"]),
        "key_variants": json.dumps({"A-variant": "Common in Africans — moderate deficiency", "Mediterranean variant": "Severe deficiency", "Canton variant": "Common in East Asians — moderate-severe"}),
        "phenotype_consequences": json.dumps({
            "G6PD deficient + oxidant drug": "Haemolytic anaemia — fever, dark urine, jaundice, falling Hb",
        }),
        "clinical_actions": json.dumps({
            "Primaquine": "SCREEN ALL before primaquine (malaria treatment) — especially essential in endemic areas",
            "If_deficient": "Avoid oxidant drugs. Primaquine alternatives or low-dose once-weekly regimen in mild deficiency.",
        }),
        "testing_indications": "Before primaquine, dapsone therapy; endemic malaria areas; unexplained haemolytic anaemia",
    },
    {
        "gene_name": "HLA-B allele 58:01",
        "gene_symbol": "HLA-B*58:01",
        "chromosome": "6p21.3",
        "enzyme_function": "HLA class I molecule. Associated with severe cutaneous adverse reactions (SJS/TEN/DRESS) with allopurinol.",
        "population_frequency": json.dumps({"Han Chinese": "6-8%", "Thai": "8%", "Korean": "12%", "Caucasians": "<1%"}),
        "affected_drugs": json.dumps(["Allopurinol"]),
        "phenotype_consequences": json.dumps({
            "HLA-B*58:01 positive + Allopurinol": "200x increased SJS/TEN risk. Mortality up to 30%.",
        }),
        "clinical_actions": json.dumps({
            "MANDATORY_screening": "Screen Han Chinese, Thai, Korean patients before allopurinol per CPIC/Taiwan guidelines.",
            "If_positive": "CONTRAINDICATED — use febuxostat or benzbromarone instead.",
        }),
        "testing_indications": "Before allopurinol in SE/East Asian populations",
    },
    {
        "gene_name": "Dihydropyrimidine Dehydrogenase",
        "gene_symbol": "DPYD",
        "chromosome": "1p22.1",
        "enzyme_function": "Rate-limiting enzyme in fluoropyrimidine catabolism (5-FU, capecitabine). Deficiency → drug accumulation → severe toxicity.",
        "affected_drugs": json.dumps(["5-Fluorouracil (5-FU)","Capecitabine","Tegafur"]),
        "key_variants": json.dumps({"*2A (IVS14+1G>A)": "No activity — severe deficiency", "c.2846A>T": "Reduced activity", "c.1236G>A/HapB3": "Reduced activity", "c.1679T>G (*13)": "Severe deficiency"}),
        "phenotype_consequences": json.dumps({
            "PM (homozygous *2A)": "Life-threatening 5-FU toxicity: myelosuppression, mucositis, diarrhoea, neurotoxicity",
            "IM (*2A heterozygous)": "Increased toxicity risk — dose reduction required",
        }),
        "clinical_actions": json.dumps({
            "PM": "CONTRAINDICATED with 5-FU/capecitabine. Consider non-fluoropyrimidine regimen.",
            "IM": "Reduce starting dose by 50%. CPIC dosing guidelines available.",
        }),
        "testing_indications": "MANDATORY before 5-FU/capecitabine per CPIC 2022 (European Medicines Agency also mandates testing for *2A in EU)",
        "fda_labels_with_pgx": "5-Fluorouracil, Capecitabine",
    },
    {
        "gene_name": "UGT1A1 (UDP-Glucuronosyltransferase 1A1)",
        "gene_symbol": "UGT1A1",
        "chromosome": "2q37.1",
        "enzyme_function": "Glucuronidation of SN-38 (active irinotecan metabolite). Reduced UGT1A1 = SN-38 accumulation = severe toxicity.",
        "affected_drugs": json.dumps(["Irinotecan","Atazanavir","Raltegravir","Belinostat"]),
        "key_variants": json.dumps({"*28 (TA repeat)": "Reduced transcription → reduced enzyme → Gilbert's-like phenotype → irinotecan toxicity", "*6": "Common in East Asians — reduced activity"}),
        "phenotype_consequences": json.dumps({
            "*28/*28 homozygous": "Severe irinotecan toxicity: febrile neutropenia, severe diarrhoea. FDA guidance recommends dose reduction.",
        }),
        "clinical_actions": json.dumps({
            "Irinotecan_*28/*28": "Reduce starting dose by 25-30% per CPIC. Escalate based on tolerability.",
            "Irinotecan_*28/*6_Asian": "Reduce dose.",
        }),
        "testing_indications": "Before irinotecan therapy — especially high-dose regimens",
        "fda_labels_with_pgx": "Irinotecan",
    },
]


def seed_genetics():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    COLUMNS = [
        "gene_name","gene_symbol","chromosome","enzyme_function",
        "population_frequency","affected_drugs","key_variants",
        "phenotype_consequences","clinical_actions","testing_indications",
        "fda_labels_with_pgx",
    ]

    inserted = skipped = 0
    for g in GENETICS_DATA:
        row = {c: g.get(c) for c in COLUMNS}
        ph = ", ".join(["?"] * len(COLUMNS))
        col_str = ", ".join(COLUMNS)
        try:
            cur.execute(f"INSERT OR IGNORE INTO genetics ({col_str}) VALUES ({ph})",
                        [row[c] for c in COLUMNS])
            if cur.rowcount > 0:
                inserted += 1
                log.info("  ✅ %s", g["gene_symbol"])
            else:
                skipped += 1
        except Exception as e:
            log.error("  ❌ %s: %s", g.get("gene_symbol","?"), e)

    conn.commit()
    conn.close()
    log.info("\n📊 Genetics — Inserted: %d | Skipped: %d", inserted, skipped)


if __name__ == "__main__":
    seed_genetics()
