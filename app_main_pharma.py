"""
VERSION v3.1
Multi-role UI: Doctor | Pharmacist | Nurse | Patient | Medical Student

ENHANCEMENTS:
  - Drug Database: new "🧑 Patient Guide" tab with AI-powered plain-English
    explanation of the medication AND the conditions it treats
  - AI Chat: dedicated, full-page chat that works for any user; role-aware presets;
  - Standalone AI Chat page with separate "Ask about a drug" quick mode
"""

import streamlit as st
import streamlit.components.v1 as components
import sqlite3, json, pandas as pd, numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os, requests

from db_config import DB_PATH
from clinical_engine import ClinicalCalculator, DoseAdjustmentEngine, SafetyChecker, Gender
from ml_models import PatientRiskModel, DietRecommendationEngine, VisualisationEngine
from lab_interpreter import LabInterpreter
from seed_emergency_protocols import seed_emergency_protocols
from deepseek_config import (
    CREATOR_RESPONSE,
    available_providers,
    build_pharmacist_messages,
    consensus_chat_sync,
    deepseek_chat_sync,
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DrugD clinic pharmacology/pathophysiology Pro",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-header{background:linear-gradient(90deg,#1a1a2e,#16213e,#0f3460);
    padding:1.2rem 2rem;border-radius:10px;margin-bottom:1.5rem;color:white;}
  .premium-glass{background:linear-gradient(135deg,rgba(15,52,96,.96),rgba(32,62,114,.96));
    color:#fff;border:1px solid rgba(255,255,255,.15);border-radius:14px;padding:1rem 1.1rem;
    box-shadow:0 8px 24px rgba(15,52,96,.22);margin-bottom:1rem;}
  .premium-note{background:#f8fbff;border:1px solid #d7e3f4;border-radius:12px;padding:.85rem 1rem;margin:.5rem 0;}
  .badge-pill{display:inline-block;background:#e8f1ff;color:#18406f;border:1px solid #c9ddf7;
    border-radius:999px;padding:.2rem .55rem;font-size:.78rem;margin-right:.35rem;}
  .metric-card{background:#f8f9fa;border-left:4px solid #0f3460;
    padding:1rem;border-radius:8px;margin:.5rem 0;}
  .drug-card{background:white;border:1px solid #dee2e6;border-radius:10px;
    padding:1.2rem;box-shadow:0 2px 4px rgba(0,0,0,.05);margin:.5rem 0;}
  .patient-guide-box{background:#fff8e1;border-left:4px solid #f9a825;
    border-radius:8px;padding:1rem;margin:.5rem 0;}
  .alert-red{background:#ffe8e8;border-left:4px solid #e74c3c;padding:.8rem;border-radius:6px;}
  .alert-yellow{background:#fff9e6;border-left:4px solid #f39c12;padding:.8rem;border-radius:6px;}
  .alert-green{background:#e8f5e9;border-left:4px solid #27ae60;padding:.8rem;border-radius:6px;}
  .chat-user{background:#e3f2fd;border-radius:12px;padding:0.8rem 1rem;margin:.3rem 0;}
  .chat-ai{background:#f3e5f5;border-radius:12px;padding:0.8rem 1rem;margin:.3rem 0;}
</style>
""", unsafe_allow_html=True)


# ─── DB helpers ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(sql: str, params: tuple = ()):
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def parse_json_fields(d: dict) -> dict:
    for k, v in d.items():
        if isinstance(v, str) and v.startswith(("[", "{")):
            try: d[k] = json.loads(v)
            except: pass
    return d


def is_creator_question(text: str) -> bool:
    if not text:
        return False
    q = text.strip().lower()
    phrases = [
        "who created you",
        "who made you",
        "who made this chatbot",
        "who made this bot",
        "who built you",
        "who is your creator",
        "who developed you",
        "who designed you",
    ]
    return any(phrase in q for phrase in phrases)


def build_prompt_preview(role: str, topic: str, mode: str, extra_notes: str = "") -> str:
    topic = (topic or "").strip()
    extra_notes = (extra_notes or "").strip()

    templates = {
        "Clinical summary": (
            "Give a professional clinical summary with mechanism of action, main indications, usual dosing, "
            "important contraindications, interactions, monitoring, and key counselling points."
        ),
        "Patient-friendly explanation": (
            "Explain it in simple everyday language for a non-clinician. Use short sentences, friendly tone, "
            "and include what the medicine treats, how it helps, common side effects, and when to seek help."
        ),
        "Safety / interaction review": (
            "Focus on safety. Summarise major interactions, contraindications, red flags, and what must be monitored."
        ),
        "Teaching note": (
            "Teach this topic clearly for a learner. Include definitions, how the medicine works, and a memorable analogy."
        ),
    }

    base = templates.get(mode, templates["Clinical summary"])
    lines = [
        f"You are answering as a senior medical AI for a {role.lower()}.",
        f"Topic: {topic or 'General pharmacology'}",
        f"Task: {base}",
        "Use bullet points where helpful.",
        "Be accurate, concise, and professional.",
        "If uncertain, say so and recommend checking a trusted reference.",
    ]
    if extra_notes:
        lines.append(f"Extra instructions: {extra_notes}")
    return "\n".join(lines)


def render_copy_button(text: str, key: str = "copy_prompt"):
    payload = json.dumps(text or "")
    html = f"""
    <div style="margin-top:0.35rem;">
      <button id="{key}" style="
        background:#0f3460;color:white;border:none;border-radius:8px;
        padding:0.55rem 0.8rem;font-size:0.92rem;cursor:pointer;width:100%;
      ">📋 Copy prompt</button>
      <script>
        const btn = document.getElementById("{key}");
        btn.addEventListener('click', async () => {{
          try {{
            await navigator.clipboard.writeText({payload});
            const old = btn.innerText;
            btn.innerText = '✅ Copied';
            setTimeout(() => btn.innerText = old, 1400);
          }} catch (err) {{
            btn.innerText = 'Copy unavailable';
          }}
        }});
      </script>
    </div>
    """
    components.html(html, height=56)


def navigate_to(page_name: str, hint: str = ""):
    st.session_state.current_page = page_name
    if hint:
        st.session_state.page_hint = hint
    st.rerun()


def chat_transcript(history: list[dict]) -> str:
    lines = []
    for i, msg in enumerate(history, 1):
        role = str(msg.get("role", "assistant")).upper()
        content = str(msg.get("content", "")).strip()
        lines.append(f"[{i}] {role}\n{content}\n")
    return "\n".join(lines).strip()


def render_section_ai_assistant(
    section_key: str,
    section_title: str,
    context_text: str = "",
    suggestions: list[str] | None = None,
):
    suggestions = suggestions or []
    st.markdown("### 🤖 AI Assistant")
    st.caption(f"Ask anything about {section_title.lower()} and get one final clinical explanation.")

    if suggestions:
        cols = st.columns(min(3, len(suggestions)))
        for idx, suggestion in enumerate(suggestions[:3]):
            with cols[idx]:
                if st.button(suggestion[:28] + ("..." if len(suggestion) > 28 else ""), key=f"{section_key}_s_{idx}"):
                    st.session_state[f"{section_key}_q"] = suggestion

    st.text_area(
        "Ask AI",
        key=f"{section_key}_q",
        height=95,
        placeholder=f"Ask AI about {section_title.lower()}...",
    )

    if st.button("Get AI explanation", key=f"{section_key}_ask", use_container_width=True):
        prompt = st.session_state.get(f"{section_key}_q", "").strip()
        if not prompt:
            st.warning("Please enter a question first.")
        else:
            guided_prompt = (
                f"Section: {section_title}\n"
                f"User role: {st.session_state.role}\n"
                f"Context:\n{context_text or 'General clinical context'}\n\n"
                f"User question:\n{prompt}\n\n"
                "Give one concise, professional response with practical guidance and safety points."
            )
            msgs = build_pharmacist_messages(guided_prompt, role=st.session_state.role)
            with st.spinner("🤖 AI is preparing your answer..."):
                st.session_state[f"{section_key}_a"] = consensus_chat_sync(msgs, max_tokens=1400, temperature=0.2)

    answer = st.session_state.get(f"{section_key}_a", "")
    if answer:
        st.markdown(answer)
        render_copy_button(answer, key=f"copy_{section_key}_answer")
        st.download_button(
            "Download answer",
            data=answer,
            file_name=f"{section_key}_ai_answer.txt",
            mime="text/plain",
            key=f"{section_key}_dl",
            use_container_width=True,
        )


# ─── Session state init ───────────────────────────────────────────────────────
for key, default in [
    ("role", "Doctor"), ("selected_patient_id", None),
    ("chat_history", []), ("interaction_drugs", []),
    ("ai_chat_history", []),
    ("ai_chat_topic", ""),
    ("ai_chat_notes", ""),
    ("ai_chat_style", "Clinical summary"),
    ("ai_pasted_prompt", ""),
    ("current_page", "🏠 Dashboard"),
    ("page_hint", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1rem 0;'>
      <h2 style='color:#0f3460;'>💊 PharmaCliniq Pro</h2>
      <p style='color:#666;font-size:.85rem;'>Hospital Pharmacology System</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.subheader("👤 Select Role")
    roles = ["Doctor", "Pharmacist", "Nurse", "Patient", "Medical Student"]
    role = st.selectbox("Your Role", roles,
                        index=roles.index(st.session_state.role))
    st.session_state.role = role

    icons = {"Doctor":"🩺","Pharmacist":"💊","Nurse":"👩‍⚕️","Patient":"🧑","Medical Student":"📚"}
    st.markdown(f"**Active:** {icons.get(role,'')} {role}")
    st.divider()

    st.subheader("📋 Navigation")
    nav_pages = [
        "🏠 Dashboard", "💊 Drug Database", "⚠️ Interaction Checker",
        "🧑 Patient Manager", "🔬 Lab Interpreter", "🍎 Diet & Ayurveda",
        "🧬 Pharmacogenomics", "🚨 Emergency Protocols",
        "📊 Analytics", "🤖 AI Chat",
    ]
    if st.session_state.current_page not in nav_pages:
        st.session_state.current_page = "🏠 Dashboard"
    selected_page = st.radio("Go to:", nav_pages, index=nav_pages.index(st.session_state.current_page))
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
    st.divider()
    st.caption(f"DB: {DB_PATH}")
    st.caption(f"v3.1 | {datetime.now().strftime('%d %b %Y')}")

page = st.session_state.current_page


# ─────────────────────────────────────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    if st.session_state.page_hint:
        st.info(st.session_state.page_hint)
        st.session_state.page_hint = ""

    st.markdown("""
    <div class='main-header'>
      <h1>🏥 Hospital Pharmacology System</h1>
      <p>Clinical Decision Support | AI-Powered (By Bain Oduwo Ai developer) | Evidence-Based</p>
    </div>
    """, unsafe_allow_html=True)

    conn = get_connection()
    total_meds = conn.execute("SELECT COUNT(*) FROM medications").fetchone()[0]
    who_meds = conn.execute("SELECT COUNT(*) FROM medications WHERE who_essential=1").fetchone()[0]
    total_ix = conn.execute("SELECT COUNT(*) FROM drug_interactions").fetchone()[0]
    total_pts = conn.execute("SELECT COUNT(*) FROM patient_profiles").fetchone()[0]
    ayur = conn.execute("SELECT COUNT(*) FROM ayurveda_diet").fetchone()[0]
    labs = conn.execute("SELECT COUNT(*) FROM lab_reference_ranges").fetchone()[0]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("💊 Medications", total_meds, f"{who_meds} WHO")
    c2.metric("⚠️ Interactions", total_ix)
    c3.metric("🧑 Patients", total_pts)
    c4.metric("🌿 Ayurveda/Diet", ayur)
    c5.metric("🔬 Lab Tests", labs)
    c6.metric("🤖 AI", "DrugD by Bain", "Live")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        cat_data = pd.read_sql("SELECT category, COUNT(*) as count FROM medications GROUP BY category", conn)
        fig = px.bar(cat_data.sort_values("count"), x="count", y="category", orientation="h",
                     color="count", color_continuous_scale="Blues", title="Medications by Category")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        sev_data = pd.read_sql("SELECT severity, COUNT(*) as count FROM drug_interactions GROUP BY severity", conn)
        colours = {"Contraindicated":"#e74c3c","Major":"#e67e22","Moderate":"#f39c12","Minor":"#27ae60"}
        fig2 = px.pie(sev_data, values="count", names="severity",
                      color="severity", color_discrete_map=colours, title="Interaction Severity")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader(f"⚡ Quick Actions — {role}")
    role_actions = {
        "Doctor": ["Check Drug Interactions","Calculate Renal Doses","Risk Score","AI Consultation"],
        "Pharmacist": ["Drug Monograph","Interaction Checker","TDM Calculations","Substitutions"],
        "Nurse": ["Medication Admin","Lab Interpretation","Emergency Protocols","Patient Meds"],
        "Patient": ["Understand My Meds","Ayurveda Guide","Diet Planner","Ask AI a Question"],
        "Medical Student": ["Drug Database","Pharmacogenomics","Clinical Calculator","AI Chat"],
    }
    action_routes = {
        "Check Drug Interactions": ("⚠️ Interaction Checker", "Opened Interaction Checker."),
        "Calculate Renal Doses": ("💊 Drug Database", "Opened Drug Database. Use dosing/renal sections per medication."),
        "Risk Score": ("🧑 Patient Manager", "Opened Patient Manager. Select or add a patient to continue risk workflows."),
        "AI Consultation": ("🤖 AI Chat", "Opened AI Chat for clinical consultation."),
        "Drug Monograph": ("💊 Drug Database", "Opened Drug Database monographs."),
        "Interaction Checker": ("⚠️ Interaction Checker", "Opened Interaction Checker."),
        "TDM Calculations": ("📊 Analytics", "Opened Analytics. Use PK simulation for dose/monitoring support."),
        "Substitutions": ("💊 Drug Database", "Opened Drug Database for alternatives and class comparisons."),
        "Medication Admin": ("🚨 Emergency Protocols", "Opened Emergency Protocols and practical medication guidance."),
        "Lab Interpretation": ("🔬 Lab Interpreter", "Opened Lab Interpreter."),
        "Emergency Protocols": ("🚨 Emergency Protocols", "Opened Emergency Protocols."),
        "Patient Meds": ("🧑 Patient Manager", "Opened Patient Manager."),
        "Understand My Meds": ("💊 Drug Database", "Opened Drug Database with patient-friendly guides."),
        "Ayurveda Guide": ("🍎 Diet & Ayurveda", "Opened Diet & Ayurveda guide."),
        "Diet Planner": ("🍎 Diet & Ayurveda", "Opened Diet Plan Generator."),
        "Ask AI a Question": ("🤖 AI Chat", "Opened AI Chat."),
        "Pharmacogenomics": ("🧬 Pharmacogenomics", "Opened Pharmacogenomics."),
        "Clinical Calculator": ("📊 Analytics", "Opened Analytics with calculation tools."),
        "AI Chat": ("🤖 AI Chat", "Opened AI Chat."),
    }
    cols = st.columns(4)
    for i, action in enumerate(role_actions.get(role, [])):
        with cols[i]:
            if st.button(f"→ {action}", key=f"qa_{i}", use_container_width=True):
                target, hint = action_routes.get(action, ("🏠 Dashboard", "Opened Dashboard."))
                navigate_to(target, hint)

    render_section_ai_assistant(
        "dash_ai",
        "Dashboard",
        context_text=(
            f"Medication count: {total_meds}; Interaction count: {total_ix}; Patient count: {total_pts}; "
            f"Ayurveda entries: {ayur}; Lab tests: {labs}."
        ),
        suggestions=[
            "Summarize today's key clinical risks",
            "What should a doctor check first?",
            "Give role-specific next steps",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  DRUG DATABASE  — with Patient Guide tab (AI condition explanations)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "💊 Drug Database":
    st.header("💊 Medication Database")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search = st.text_input("🔍 Search name, class, or category",
                               placeholder="e.g. metformin, beta-blocker, cardiac")
    with col2:
        cats = ["All"] + [r["category"] for r in query_db("SELECT DISTINCT category FROM medications ORDER BY category")]
        sel_cat = st.selectbox("Category", cats)
    with col3:
        who_only = st.checkbox("WHO Essential Only")

    sql = """SELECT id, name, generic_name, category, drug_class, dose_adult,
                    route_admin, pregnancy_category, who_essential,
                    indications, conditions_treated, mechanism_simple
             FROM medications WHERE 1=1"""
    params = []
    if search:
        sql += " AND (name LIKE ? OR generic_name LIKE ? OR drug_class LIKE ? OR category LIKE ?)"
        s = f"%{search}%"; params += [s, s, s, s]
    if sel_cat != "All":
        sql += " AND category=?"; params.append(sel_cat)
    if who_only:
        sql += " AND who_essential=1"
    sql += " ORDER BY category, name LIMIT 200"

    meds = query_db(sql, tuple(params))
    st.caption(f"Found **{len(meds)}** medications")

    render_section_ai_assistant(
        "drugdb_ai",
        "Drug Database",
        context_text=f"Current filter category: {sel_cat}. Search: {search or 'none'}. Results shown: {len(meds)} medications.",
        suggestions=[
            "Compare two drugs for safety",
            "Explain a drug in patient language",
            "Give monitoring checklist",
        ],
    )

    for med in meds:
        med = parse_json_fields(med)
        who_badge = " 🌍 WHO Essential" if med.get("who_essential") else ""
        routes = (", ".join(med["route_admin"]) if isinstance(med.get("route_admin"), list)
                  else str(med.get("route_admin", "")))

        with st.expander(f"**{med['name']}** — {med.get('drug_class','')} {who_badge}"):
            # Pull full record only when expanded monograph needed
            tabs = st.tabs(["📋 Overview", "💊 Dosing & PK", "⚠️ Safety", "🔗 Interactions", "🧬 Genetics", "🧑 Patient Guide"])

            with tabs[0]:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Generic:** {med.get('generic_name','')}")
                    st.markdown(f"**Category:** {med.get('category','')}")
                    st.markdown(f"**Class:** {med.get('drug_class','')}")
                    st.markdown(f"**Routes:** {routes}")
                    st.markdown(f"**Pregnancy:** {med.get('pregnancy_category','')}")
                with c2:
                    st.markdown(f"**Mechanism:** {med.get('mechanism_simple') or 'See full monograph'}")
                    indications = med.get("indications", [])
                    if indications:
                        st.markdown("**Treats:**")
                        for ind in (indications if isinstance(indications, list) else [indications]):
                            st.markdown(f"  - {ind}")

            with tabs[1]:
                full = parse_json_fields(query_db("SELECT * FROM medications WHERE id=?", (med["id"],))[0]) if query_db("SELECT id FROM medications WHERE id=?", (med["id"],)) else {}
                st.markdown(f"**Adult Dose:** {full.get('dose_adult','N/A')}")
                st.markdown(f"**Paediatric:** {full.get('dose_pediatric','N/A')}")
                st.markdown(f"**Geriatric:** {full.get('dose_geriatric','N/A')}")
                if full.get("dose_renal_adj"):
                    st.markdown("**Renal Adjustment:**")
                    renal = full["dose_renal_adj"]
                    st.json(renal if isinstance(renal, dict) else {"info": renal})
                for pk in ["bioavailability","protein_binding","half_life","metabolism","excretion"]:
                    if full.get(pk):
                        st.markdown(f"**{pk.replace('_',' ').title()}:** {full[pk]}")

            with tabs[2]:
                full = parse_json_fields(query_db("SELECT * FROM medications WHERE id=?", (med["id"],))[0]) if query_db("SELECT id FROM medications WHERE id=?", (med["id"],)) else {}
                if full.get("black_box_warning"):
                    st.error(f"⬛ BLACK BOX WARNING: {full['black_box_warning']}")
                aes = full.get("adverse_effects_common", [])
                aes_s = full.get("adverse_effects_serious", [])
                if aes:
                    st.markdown("**Common Side Effects:**")
                    for a in (aes if isinstance(aes, list) else [aes]):
                        st.markdown(f"  - {a}")
                if aes_s:
                    st.markdown("**⚠️ Serious Side Effects:**")
                    for a in (aes_s if isinstance(aes_s, list) else [aes_s]):
                        st.markdown(f"  - {a}")
                contra = full.get("contraindications", [])
                if contra:
                    st.markdown("**🚫 Contraindications:**")
                    for c in (contra if isinstance(contra, list) else [contra]):
                        st.markdown(f"  - {c}")

            with tabs[3]:
                full = parse_json_fields(query_db("SELECT * FROM medications WHERE id=?", (med["id"],))[0]) if query_db("SELECT id FROM medications WHERE id=?", (med["id"],)) else {}
                di = full.get("drug_interactions_list", [])
                if di:
                    st.markdown("**Drug Interactions:**")
                    for d in (di if isinstance(di, list) else [di]):
                        st.markdown(f"  - {d}")
                fi = full.get("food_interactions","")
                if fi: st.markdown(f"**Food Interactions:** {fi}")
                mon = full.get("monitoring_params", [])
                if mon:
                    st.markdown("**Monitoring Parameters:**")
                    for m in (mon if isinstance(mon, list) else [mon]):
                        st.markdown(f"  - ✅ {m}")

            with tabs[4]:
                full = parse_json_fields(query_db("SELECT * FROM medications WHERE id=?", (med["id"],))[0]) if query_db("SELECT id FROM medications WHERE id=?", (med["id"],)) else {}
                st.markdown(f"**CYP Substrate:** {full.get('cyp_substrate','None')}")
                st.markdown(f"**CYP Inhibitor:** {full.get('cyp_inhibitor','None')}")
                st.markdown(f"**CYP Inducer:** {full.get('cyp_inducer','None')}")
                gv = full.get("gene_variants", {})
                if gv and isinstance(gv, dict):
                    st.markdown("**Gene Variants:**"); st.json(gv)

            # ─ NEW: Patient Guide tab ─────────────────────────────────────
            with tabs[5]:
                st.markdown("""
                <div class='patient-guide-box'>
                  <b>🧑 Patient Guide</b> — Plain English explanation of this medication
                  and the conditions it treats. No medical jargon!
                </div>
                """, unsafe_allow_html=True)

                # Try stored conditions_treated first
                stored_guide = med.get("conditions_treated") or ""
                if stored_guide:
                    st.markdown(stored_guide)
                else:
                    indications_str = ", ".join(
                        med.get("indications", []) if isinstance(med.get("indications"), list)
                        else [str(med.get("indications",""))]
                    ) or "various conditions"
                    gen_key = f"guide_{med['id']}"
                    if gen_key not in st.session_state:
                        st.session_state[gen_key] = None

                    if st.session_state[gen_key]:
                        st.markdown(st.session_state[gen_key])
                    else:
                        st.info("🤖 Click below to get an AI explanation powered by Bain Oduwo")
                        if st.button(f"🤖 Explain this medicine for me", key=f"btn_{med['id']}"):
                            prompt_msgs = [
                                {"role": "system", "content": "You are a friendly pharmacist explaining medicines to patients with no medical background. Use simple everyday language, short sentences, and emojis. Be warm and reassuring."},
                                {"role": "user", "content": f"""Explain {med['name']} to someone who is NOT a doctor or nurse:

1. 💊 What is this medicine? (in 1-2 simple sentences)
2. 🏥 What health problems does it treat? 
   For EACH condition ({indications_str}): explain in very simple terms what that condition is, what happens in the body, and why it's a problem.
3. ⚙️ How does this medicine help? (use a simple analogy — like "it's like...")
4. 📅 How should you take it? (key points from: {med.get('dose_adult','')[:100]})
5. ⚠️ What should you watch out for? (most important warnings in simple language)"""}
                            ]
                            with st.spinner("🤖 AI is preparing your explanation..."):
                                response = deepseek_chat_sync(prompt_msgs, max_tokens=1200)
                                st.session_state[gen_key] = response
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  INTERACTION CHECKER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚠️ Interaction Checker":
    st.header("⚠️ Drug Interaction Checker")
    st.markdown("Add 2 or more medications to check for interactions.")

    all_meds = [r["name"] for r in query_db("SELECT name FROM medications ORDER BY name")]
    selected_drugs = st.multiselect("Select medications (2-10):", all_meds,
                                    default=st.session_state.interaction_drugs, max_selections=10)
    st.session_state.interaction_drugs = selected_drugs

    if len(selected_drugs) >= 2 and st.button("🔍 Check Interactions", type="primary"):
        results = []
        for i in range(len(selected_drugs)):
            for j in range(i + 1, len(selected_drugs)):
                a, b = selected_drugs[i], selected_drugs[j]
                rows = query_db(
                    "SELECT * FROM drug_interactions WHERE (drug_a LIKE ? AND drug_b LIKE ?) OR (drug_a LIKE ? AND drug_b LIKE ?)",
                    (f"%{a}%", f"%{b}%", f"%{b}%", f"%{a}%")
                )
                if rows:
                    results.extend([parse_json_fields(r) for r in rows])
                else:
                    results.append({
                        "drug_a": a,
                        "drug_b": b,
                        "severity": "Needs clinical review",
                        "mechanism": "Use pharmacology principles and patient-specific risk assessment.",
                    })

        qt_flags = SafetyChecker.check_qt_risk(selected_drugs)
        beers = SafetyChecker.check_beers_criteria(selected_drugs, age=70)

        st.divider()
        st.subheader(f"Results: {', '.join(selected_drugs)}")

        sev_order = {"Contraindicated": 4, "Major": 3, "Moderate": 2, "Minor": 1}
        if results:
            highest = max(results, key=lambda r: sev_order.get(r.get("severity",""), 0))
            hs = highest.get("severity","Unknown")
            if hs == "Contraindicated": st.error("🚨 CONTRAINDICATED INTERACTION DETECTED")
            elif hs == "Major": st.error("🔴 MAJOR interaction detected — consider alternative")
            elif hs == "Moderate": st.warning("🟡 MODERATE interaction — monitor closely")
            else: st.success("✅ No major interactions detected")

        for r in results:
            sev = r.get("severity","Unknown")
            icon = {"Contraindicated":"🚨","Major":"🔴","Moderate":"🟡","Minor":"🟢"}.get(sev,"⚪")
            with st.expander(f"{icon} {r['drug_a']} ✕ {r['drug_b']} — {sev}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Mechanism:** {r.get('mechanism','N/A')}")
                    st.markdown(f"**Effect:** {r.get('clinical_effect') or r.get('effect','N/A')}")
                with c2:
                    st.markdown(f"**Management:** {r.get('management','N/A')}")
                    if r.get("onset"): st.markdown(f"**Onset:** {r['onset']}")

        if qt_flags:
            st.divider(); st.subheader("🔔 QT Prolongation Alerts")
            for flag in qt_flags:
                if "MULTIPLE" in flag or "CRITICAL" in flag: st.error(flag)
                elif "⚠️" in flag: st.warning(flag)
                else: st.info(flag)

        if beers:
            st.subheader("👴 Beers Criteria Flags (Elderly)")
            for b in beers: st.warning(b)

    render_section_ai_assistant(
        "interaction_ai",
        "Interaction Checker",
        context_text=f"Selected drugs: {', '.join(selected_drugs) if selected_drugs else 'none'}.",
        suggestions=[
            "Explain this interaction simply",
            "Suggest safer alternatives",
            "Give monitoring plan",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PATIENT MANAGER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🧑 Patient Manager":
    st.header("🧑 Patient Manager")
    tab1, tab2 = st.tabs(["📋 Patient List", "➕ Add Patient"])

    with tab1:
        search_pt = st.text_input("Search patients by name or diagnosis")
        # FIXED: name and diagnoses columns exist in fixed schema
        sql = "SELECT id, name, age, gender, diagnoses, created_at FROM patient_profiles WHERE 1=1"
        params = []
        if search_pt:
            sql += " AND (name LIKE ? OR diagnoses LIKE ?)"; s = f"%{search_pt}%"; params += [s, s]
        sql += " ORDER BY created_at DESC LIMIT 50"
        patients = query_db(sql, tuple(params))

        if not patients:
            st.info("No patients found. Add patients using the 'Add Patient' tab.")
        else:
            for pt in patients:
                pt = parse_json_fields(pt)
                diags = pt.get("diagnoses", [])
                diag_str = ", ".join(diags) if isinstance(diags, list) else str(diags)
                with st.expander(f"🧑 **{pt.get('name','Unknown')}** — {pt.get('age','')}y {pt.get('gender','')} | {diag_str[:60]}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Age:** {pt.get('age')} | **Gender:** {pt.get('gender')}")
                        st.markdown(f"**Blood Group:** {pt.get('blood_group','Not recorded')}")
                        st.markdown(f"**Diagnoses:** {diag_str or 'None recorded'}")
                    with c2:
                        st.markdown(f"**Registered:** {str(pt.get('created_at',''))[:10]}")
                        if st.button("📋 View Full Profile", key=f"pt_{pt['id']}"):
                            st.session_state.selected_patient_id = pt["id"]

    with tab2:
        st.subheader("➕ Register New Patient")
        with st.form("add_patient"):
            c1, c2 = st.columns(2)
            with c1:
                pt_name = st.text_input("Full Name *")
                pt_age = st.number_input("Age *", 0, 120, 30)
                pt_gender = st.selectbox("Gender *", ["male","female","other"])
                pt_weight = st.number_input("Weight (kg)", 20.0, 300.0, 70.0)
                pt_height = st.number_input("Height (cm)", 50.0, 250.0, 165.0)
            with c2:
                pt_bg = st.selectbox("Blood Group", ["Unknown","A+","A-","B+","B-","AB+","AB-","O+","O-"])
                pt_scr = st.number_input("Serum Creatinine (mg/dL)", 0.0, 20.0, 0.0)
                pt_hba1c = st.number_input("HbA1c (%)", 0.0, 20.0, 0.0)
                pt_diag = st.text_area("Diagnoses (one per line)")
                pt_allergy = st.text_area("Allergies (one per line)")

            submitted = st.form_submit_button("➕ Register Patient", type="primary")

        if submitted and pt_name:
            conn = get_connection()
            diag_list = [d.strip() for d in pt_diag.split("\n") if d.strip()]
            allergy_list = [a.strip() for a in pt_allergy.split("\n") if a.strip()]
            conn.execute(
                """INSERT INTO patient_profiles
                   (name, age, gender, weight_kg, height_cm, blood_group,
                    diagnoses, allergies, serum_creatinine, hba1c, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pt_name, pt_age, pt_gender, pt_weight, pt_height, pt_bg,
                 json.dumps(diag_list), json.dumps(allergy_list),
                 pt_scr or None, pt_hba1c or None, datetime.now().isoformat())
            )
            conn.commit()
            st.success(f"✅ Patient {pt_name} registered successfully!")

    render_section_ai_assistant(
        "patient_ai",
        "Patient Manager",
        context_text="Use patient profile fields (age, diagnoses, creatinine, HbA1c, allergies) for guidance.",
        suggestions=[
            "Create a medication safety checklist",
            "How to prioritize patient risks",
            "What labs should be monitored",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  LAB INTERPRETER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔬 Lab Interpreter":
    st.header("🔬 Lab Result Interpreter")
    tab1, tab2 = st.tabs(["🧪 Single Test", "📋 Full Panel"])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        with c1: test_name = st.text_input("Test Name", "Hb")
        with c2: test_value = st.number_input("Value", 0.0, 10000.0, 10.5, step=0.1)
        with c3: lab_gender = st.selectbox("Gender", ["male","female"], key="lg")
        with c4: lab_age = st.number_input("Age", 0, 120, 40, key="la")

        if st.button("🔍 Interpret", type="primary"):
            result = LabInterpreter().interpret(test_name, test_value, lab_gender, lab_age)
            result = parse_json_fields(result)
            status = result.get("status","")
            if "CRITICAL" in status: st.error(f"{status}: {test_name} = {test_value}")
            elif "HIGH" in status or "LOW" in status: st.warning(f"{status}: {test_name} = {test_value} {result.get('unit','')}")
            else: st.success(f"{status}: {test_name} = {test_value} {result.get('unit','')}")
            st.markdown(f"**Reference Range:** {result.get('reference_range','N/A')}")
            if result.get("clinical_meaning"): st.info(f"**Clinical Meaning:** {result['clinical_meaning']}")

    with tab2:
        panel_input = st.text_area("Lab Results (one per line: TestName=Value)",
            "Hb=10.5\nWBC=12.5\nPLT=450\nSodium=138\nPotassium=5.2\nCreatinine=1.8\nGlucose=320\nALT=85",
            height=200)
        p_gender = st.selectbox("Gender", ["male","female"], key="pg")
        p_age = st.number_input("Age", 0, 120, 55, key="pa")

        if st.button("📋 Interpret Panel", type="primary"):
            interpreter = LabInterpreter()
            summary = []
            for line in [l.strip() for l in panel_input.split("\n") if "=" in l]:
                try:
                    name, val = line.split("=", 1)
                    r = interpreter.interpret(name.strip(), float(val.strip()), p_gender, p_age)
                    summary.append({"Test": r.get("test",""), "Value": r.get("value",""),
                                    "Unit": r.get("unit",""), "Reference": r.get("reference_range",""),
                                    "Status": r.get("status","")})
                except Exception as e:
                    st.warning(f"Could not parse: {line}")

            df = pd.DataFrame(summary)
            def color_status(val):
                if "CRITICAL" in str(val): return "background-color:#ffcccc;color:#c0392b;font-weight:bold"
                if "HIGH" in str(val) or "LOW" in str(val): return "background-color:#fff3cd"
                if "Normal" in str(val): return "background-color:#d4edda"
                return ""
            st.dataframe(df.style.applymap(color_status, subset=["Status"]), use_container_width=True)

    render_section_ai_assistant(
        "lab_ai",
        "Lab Interpreter",
        context_text="Interpret clinical meaning, urgency, and medication implications of abnormal laboratory values.",
        suggestions=[
            "Explain this abnormal panel",
            "Which values are most urgent?",
            "Medication implications of these labs",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  DIET & AYURVEDA
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🍎 Diet & Ayurveda":
    st.header("🍎 Diet, Nutrition & Ayurveda")
    tab1, tab2, tab3 = st.tabs(["🌿 Ayurveda & Foods","🍽️ Diet Plan Generator","💊 Herb-Drug Interactions"])

    with tab1:
        e_type = st.selectbox("Filter by Type", ["All","Ayurveda","Vegetable","Fruit","Food","Spice"])
        search_a = st.text_input("Search", placeholder="e.g. turmeric, diabetes, antioxidant")
        sql = "SELECT * FROM ayurveda_diet WHERE 1=1"; params = []
        if e_type != "All": sql += " AND entry_type=?"; params.append(e_type)
        if search_a:
            sql += " AND (name LIKE ? OR health_benefits LIKE ? OR traditional_uses LIKE ? OR category LIKE ?)"
            s = f"%{search_a}%"; params += [s, s, s, s]
        sql += " ORDER BY entry_type, name LIMIT 60"
        items = query_db(sql, tuple(params))
        st.caption(f"{len(items)} items found")
        for item in items:
            item = parse_json_fields(item)
            icon = {"Ayurveda":"🌿","Vegetable":"🥦","Fruit":"🍎","Food":"🍚","Spice":"🌶️"}.get(item.get("entry_type",""),"🌱")
            with st.expander(f"{icon} **{item['name']}** — {item.get('category','')}"):
                c1, c2 = st.columns(2)
                with c1:
                    if item.get("botanical_name"): st.markdown(f"*{item['botanical_name']}*")
                    if item.get("dosha_effect"): st.markdown(f"**Dosha:** {item['dosha_effect']}")
                    uses = item.get("traditional_uses", [])
                    if uses: st.markdown("**Uses:** " + (", ".join(uses) if isinstance(uses, list) else uses))
                    if item.get("calories_per_100g"): st.markdown(f"**Calories:** {item['calories_per_100g']} kcal/100g")
                with c2:
                    di = item.get("drug_interactions", [])
                    if di:
                        st.markdown("⚠️ **Drug Interactions:**")
                        for d in (di if isinstance(di, list) else [di])[:4]: st.markdown(f"  - {d}")
                    if item.get("health_benefits"):
                        bens = item["health_benefits"]
                        st.markdown("**Benefits:** " + (", ".join(bens[:4]) if isinstance(bens, list) else bens))

    with tab2:
        st.subheader("🍽️ Personalised Diet Plan Generator")
        with st.form("diet_plan"):
            c1, c2 = st.columns(2)
            with c1:
                dp_age = st.number_input("Age", 18, 90, 45)
                dp_gender = st.selectbox("Gender", ["male","female"])
                dp_weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)
                dp_height = st.number_input("Height (cm)", 100.0, 220.0, 165.0)
            with c2:
                dp_activity = st.selectbox("Activity Level", ["sedentary","light","moderate","active","very_active"])
                dp_conditions = st.multiselect("Medical Conditions", ["diabetes","hypertension","chronic_kidney_disease","anaemia","obesity","cardiac"])
                dp_goal = st.selectbox("Goal", ["maintain","lose","gain"])
            gen_plan = st.form_submit_button("🍽️ Generate Plan", type="primary")

        if gen_plan:
            plan = DietRecommendationEngine().generate_plan({
                "age": dp_age, "gender": dp_gender, "weight_kg": dp_weight,
                "height_cm": dp_height, "activity_level": dp_activity,
                "conditions": dp_conditions, "goal": dp_goal,
            })
            c1, c2 = st.columns(2)
            with c1:
                st.metric("🔥 Daily Calories", f"{plan['calories_target']} kcal")
                st.metric("BMR", f"{plan['bmr']} kcal")
                st.metric("TDEE", f"{plan['tdee']} kcal")
            with c2:
                macros = plan["macros"]
                fig = px.pie(values=[macros["carbohydrates_g"]*4, macros["protein_g"]*4, macros["fat_g"]*9],
                             names=["Carbohydrates","Protein","Fat"],
                             color_discrete_sequence=["#3498db","#e74c3c","#f39c12"],
                             title="Macronutrient Distribution")
                st.plotly_chart(fig, use_container_width=True)
            st.divider()
            meal_icons = {"breakfast":"🌅","morning_snack":"☕","lunch":"☀️","evening_snack":"🫖","dinner":"🌙"}
            for meal, icon in meal_icons.items():
                if plan.get("meals",{}).get(meal):
                    st.markdown(f"**{icon} {meal.replace('_',' ').title()}:** {plan['meals'][meal]}")
            if plan.get("condition_specific"):
                st.divider(); st.subheader("🏥 Condition-Specific Guidance")
                for cond, guide in plan["condition_specific"].items():
                    with st.expander(f"📋 {cond.replace('_',' ').title()}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("✅ **Include:**")
                            for f in guide.get("include",[]): st.markdown(f"  - {f}")
                        with c2:
                            st.markdown("❌ **Avoid:**")
                            for f in guide.get("avoid",[]): st.markdown(f"  - {f}")
                        st.info(guide.get("note",""))

    with tab3:
        drug_to_check = st.text_input("Enter drug to check for herb/food interactions",
                                       placeholder="e.g. Warfarin, Metformin, Phenytoin")
        if drug_to_check:
            items = query_db("SELECT name, entry_type, drug_interactions, safety_notes FROM ayurveda_diet WHERE drug_interactions LIKE ?",
                             (f"%{drug_to_check}%",))
            if items:
                st.warning(f"⚠️ Found {len(items)} herb/food interactions with **{drug_to_check}**")
                for item in items:
                    item = parse_json_fields(item)
                    icon = {"Ayurveda":"🌿","Vegetable":"🥦","Fruit":"🍎","Food":"🍚","Spice":"🌶️"}.get(item.get("entry_type",""),"🌱")
                    with st.expander(f"{icon} {item['name']}"):
                        di = item.get("drug_interactions",[])
                        for d in (di if isinstance(di, list) else [di]):
                            if drug_to_check.lower() in str(d).lower(): st.markdown(f"⚠️ {d}")
                        if item.get("safety_notes"): st.markdown(f"ℹ️ {item['safety_notes']}")
            else:
                st.success(f"✅ No herb/food interactions found for {drug_to_check}")

    render_section_ai_assistant(
        "diet_ai",
        "Diet & Ayurveda",
        context_text="Provide evidence-aware lifestyle, nutrition, and herb-drug interaction support.",
        suggestions=[
            "Build a practical one-day meal guide",
            "Explain herb-drug safety",
            "Patient-friendly nutrition advice",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PHARMACOGENOMICS  — FIXED column names
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🧬 Pharmacogenomics":
    st.header("🧬 Pharmacogenomics — Precision Medicine")
    tab1, tab2, tab3 = st.tabs(["🔬 Gene Database","💊 Drug-Gene Guide","🧬 Patient PGx Profile"])

    with tab1:
        # FIXED: correct column names from schema
        genes = query_db("SELECT * FROM genetics ORDER BY gene_name")
        if not genes:
            st.info("No genetics data. Run: python seed_genetics.py")
        for g in genes:
            g = parse_json_fields(g)
            with st.expander(f"🧬 **{g.get('gene_name','')}** ({g.get('gene_symbol','')}) — {g.get('enzyme_function','')[:60]}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Function:** {g.get('enzyme_function','')}")
                    st.markdown(f"**Chromosome:** {g.get('chromosome','')}")
                    affected = g.get("affected_drugs",[])
                    if affected:
                        st.markdown("**Affected Drugs:**")
                        for d in (affected if isinstance(affected, list) else [affected])[:8]:
                            st.markdown(f"  - {d}")
                with c2:
                    consequences = g.get("phenotype_consequences",{})
                    if consequences and isinstance(consequences, dict):
                        st.markdown("**Phenotype Effects:**")
                        for phenotype, effect in list(consequences.items())[:4]:
                            st.markdown(f"  - **{phenotype}:** {str(effect)[:120]}")
                    variants = g.get("key_variants",{})
                    if variants and isinstance(variants, dict):
                        st.markdown("**Key Variants:**")
                        for variant, meaning in list(variants.items())[:4]:
                            st.markdown(f"  - *{variant}*: {str(meaning)[:80]}")

    with tab2:
        st.subheader("Drug + Gene Clinical Actions")
        pgx_table = [
            ("Warfarin","CYP2C9 + VKORC1","PM","Reduce dose 50-60%; lower INR target"),
            ("Clopidogrel","CYP2C19","PM","🚨 No antiplatelet effect — use prasugrel/ticagrelor"),
            ("Codeine/Tramadol","CYP2D6","UM","🚨 CONTRAINDICATED — fatal opioid toxicity"),
            ("Codeine/Tramadol","CYP2D6","PM","Reduced analgesia; use morphine/oxycodone"),
            ("Tamoxifen","CYP2D6","PM","Reduced endoxifen; consider aromatase inhibitor"),
            ("Simvastatin","SLCO1B1","*5/*5","🚨 High myopathy risk; switch to rosuvastatin"),
            ("Abacavir","HLA-B*57:01","+ve","🚨 CONTRAINDICATED — fatal hypersensitivity"),
            ("Carbamazepine","HLA-B*15:02","+ve","🚨 Stevens-Johnson risk — screen SE Asian patients"),
            ("Azathioprine","TPMT","PM","🚨 Severe myelosuppression — reduce dose 90%"),
            ("Metoprolol","CYP2D6","PM","5-10x higher levels; start 12.5-25mg"),
            ("Phenytoin","CYP2C9","PM","Higher levels → toxicity; reduce dose"),
            ("Allopurinol","HLA-B*58:01","+ve","🚨 SJS/TEN risk — mandatory screen SE Asian"),
        ]
        df = pd.DataFrame(pgx_table, columns=["Drug","Gene","Phenotype/Variant","Clinical Action"])
        def pgx_color(val):
            if "🚨" in str(val): return "background-color:#ffcccc"
            if "reduce" in str(val).lower(): return "background-color:#fff3cd"
            return ""
        st.dataframe(df.style.applymap(pgx_color, subset=["Clinical Action"]),
                     use_container_width=True, height=400)

    with tab3:
        st.subheader("Patient PGx Profile Interpreter")
        c1, c2 = st.columns(2)
        with c1:
            cyp2d6 = st.selectbox("CYP2D6", ["EM (Normal)","IM (Intermediate)","PM (Poor)","UM (Ultra-rapid)"])
            cyp2c19 = st.selectbox("CYP2C19", ["EM (Normal)","IM (Intermediate)","PM (Poor)","UM (Ultra-rapid)"])
            cyp2c9 = st.selectbox("CYP2C9", ["*1/*1 (Normal)","*1/*2 (Reduced)","*1/*3 (Reduced)","*2/*3 (PM)","*3/*3 (PM)"])
        with c2:
            vkorc1 = st.selectbox("VKORC1", ["GG (Normal)","GA (Reduced)","AA (Very sensitive)"])
            hla_b = st.selectbox("HLA-B", ["Not tested","HLA-B*57:01 Positive","HLA-B*15:02 Positive","HLA-B*58:01 Positive"])
            slco1b1 = st.selectbox("SLCO1B1", ["Normal","*5 carrier (Reduced)","*5/*5 (Poor — statin risk)"])

        drugs_of_interest = st.multiselect("Drugs being considered:", [
            "Warfarin","Clopidogrel","Codeine","Tramadol","Tamoxifen",
            "Simvastatin","Abacavir","Carbamazepine","Azathioprine",
            "Fluoxetine","Metoprolol","Phenytoin","Allopurinol",
        ])
        if st.button("🧬 Generate PGx Report", type="primary"):
            st.markdown("### 🧬 Pharmacogenomics Report")
            alerts = []
            if cyp2d6.startswith("PM") and any(d in drugs_of_interest for d in ["Codeine","Tramadol"]):
                alerts.append("🚨 CYP2D6 PM + Codeine/Tramadol: CONTRAINDICATED — use alternative")
            if cyp2d6.startswith("UM") and any(d in drugs_of_interest for d in ["Codeine","Tramadol"]):
                alerts.append("🚨 CYP2D6 UM + Codeine/Tramadol: FATAL toxicity risk — AVOID")
            if cyp2c19.startswith("PM") and "Clopidogrel" in drugs_of_interest:
                alerts.append("🔴 CYP2C19 PM + Clopidogrel: Use prasugrel or ticagrelor")
            if "HLA-B*57:01 Positive" in hla_b and "Abacavir" in drugs_of_interest:
                alerts.append("🚨 HLA-B*57:01 + Abacavir: CONTRAINDICATED")
            if "*5/*5" in slco1b1 and "Simvastatin" in drugs_of_interest:
                alerts.append("🚨 SLCO1B1*5/*5 + Simvastatin: Very high myopathy risk")
            for a in alerts:
                if "🚨" in a: st.error(a)
                else: st.warning(a)
            if not alerts: st.success("✅ No critical PGx interactions detected")

    render_section_ai_assistant(
        "pgx_ai",
        "Pharmacogenomics",
        context_text="Use gene-phenotype and drug-gene relationships to guide safer medication decisions.",
        suggestions=[
            "Explain this gene-drug risk",
            "Dose implications by phenotype",
            "PGx counseling points",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EMERGENCY PROTOCOLS  — FIXED column name
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🚨 Emergency Protocols":
    st.header("🚨 Emergency Protocols & ACLS")
    st.error("⚠️ Reference only. Always follow local hospital guidelines and consult seniors.")

    # FIXED: query uses 'name' (not 'protocol_name')
    protocols = query_db("SELECT * FROM emergency_protocols ORDER BY category, name")
    if not protocols:
        st.warning("Emergency protocols are being initialized for first-time use.")
        try:
            seed_emergency_protocols()
            protocols = query_db("SELECT * FROM emergency_protocols ORDER BY category, name")
            if protocols:
                st.success("Emergency protocols loaded successfully.")
        except Exception as e:
            st.error(f"Could not initialize emergency protocols: {e}")
            st.caption("Run `python startup.py` to complete initialization.")
    if protocols:
        categories = list(set(p.get("category","") for p in protocols))
        sel_cat = st.selectbox("Protocol Category", ["All"] + sorted(categories))
        for p in protocols:
            p = parse_json_fields(p)
            if sel_cat != "All" and p.get("category") != sel_cat: continue
            with st.expander(f"🚨 **{p.get('name','')}** — {p.get('category','')}"):
                if p.get("steps"):
                    st.markdown("**Steps:**")
                    steps = p["steps"]
                    for i, s in enumerate(steps if isinstance(steps, list) else [steps], 1):
                        st.markdown(f"{i}. {s}")
                drugs = p.get("drugs") or p.get("medications")
                if drugs:
                    st.markdown("**Key Drugs:**")
                    for d in (drugs if isinstance(drugs, list) else [drugs]):
                        st.markdown(f"  - 💊 {d}")
                if p.get("doses"): st.markdown(f"**Doses:** {p['doses']}")
                if p.get("notes"): st.info(p["notes"])

    render_section_ai_assistant(
        "emergency_ai",
        "Emergency Protocols",
        context_text="Provide concise emergency support steps, safety flags, and escalation reminders.",
        suggestions=[
            "Give a rapid response checklist",
            "Explain first-line emergency meds",
            "What to monitor immediately",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📊 Analytics":
    st.header("📊 Analytics Dashboard")
    conn = get_connection()
    c1, c2 = st.columns(2)
    with c1:
        cat_df = pd.read_sql("SELECT category, COUNT(*) as count FROM medications GROUP BY category ORDER BY count DESC", conn)
        fig = px.treemap(cat_df, path=["category"], values="count", color="count",
                         color_continuous_scale="Blues", title="Medication Distribution")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        sev_df = pd.read_sql("SELECT severity, COUNT(*) as count FROM drug_interactions GROUP BY severity", conn)
        colours = {"Contraindicated":"#e74c3c","Major":"#e67e22","Moderate":"#f39c12","Minor":"#27ae60"}
        fig2 = px.bar(sev_df, x="severity", y="count", color="severity",
                      color_discrete_map=colours, title="Drug Interaction Severity")
        st.plotly_chart(fig2, use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        ayur_df = pd.read_sql("SELECT entry_type, COUNT(*) as count FROM ayurveda_diet GROUP BY entry_type", conn)
        fig3 = px.pie(ayur_df, values="count", names="entry_type", title="Ayurveda/Diet by Type")
        st.plotly_chart(fig3, use_container_width=True)
    with c4:
        st.subheader("🔬 PK Simulation")
        sim_drug = st.text_input("Drug", "Vancomycin")
        c1b, c2b, c3b = st.columns(3)
        with c1b: dose = st.number_input("Dose (mg)", 100.0, 5000.0, 1000.0)
        with c2b: vd = st.number_input("Vd (L)", 5.0, 200.0, 50.0)
        with c3b: cl = st.number_input("CL (L/h)", 0.5, 20.0, 4.0)
        interval = st.slider("Interval (h)", 6, 24, 12)
        ke = cl / vd; t_half = 0.693 / ke
        time = np.linspace(0, interval * 6, 300); conc = np.zeros(len(time))
        for dn in range(6):
            t0 = dn * interval
            for i, t in enumerate(time):
                if t >= t0: conc[i] += (dose / vd) * np.exp(-ke * (t - t0))
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=time, y=conc, fill="tozeroy", name=sim_drug,
                                  line=dict(color="#2980b9", width=2)))
        fig4.update_layout(title=f"{sim_drug} PK (t½={t_half:.1f}h)",
                           xaxis_title="Time (h)", yaxis_title="Conc (mg/L)")
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("⬇️ Export Analytics Data")
    tab_a, tab_b, tab_c, tab_d = st.tabs(["Medication Counts", "Interaction Severity", "Ayurveda Types", "PK Simulation"])
    with tab_a:
        st.dataframe(cat_df, use_container_width=True)
        st.download_button("Download medication counts CSV", cat_df.to_csv(index=False), "medication_counts.csv", "text/csv")
    with tab_b:
        st.dataframe(sev_df, use_container_width=True)
        st.download_button("Download interaction severity CSV", sev_df.to_csv(index=False), "interaction_severity.csv", "text/csv")
    with tab_c:
        st.dataframe(ayur_df, use_container_width=True)
        st.download_button("Download ayurveda type CSV", ayur_df.to_csv(index=False), "ayurveda_types.csv", "text/csv")
    with tab_d:
        pk_df = pd.DataFrame({"time_h": time, "concentration_mg_per_l": conc})
        st.dataframe(pk_df.head(40), use_container_width=True)
        st.download_button("Download PK simulation CSV", pk_df.to_csv(index=False), "pk_simulation.csv", "text/csv")

    render_section_ai_assistant(
        "analytics_ai",
        "Analytics",
        context_text=(
            f"Medication categories tracked: {len(cat_df)}; interaction severities tracked: {len(sev_df)}; "
            f"Ayurveda entry types tracked: {len(ayur_df)}; PK simulation drug: {sim_drug}."
        ),
        suggestions=[
            "Summarize these analytics",
            "Top safety insights from charts",
            "What action should the team take?",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  AI CHAT  — Enhanced full-page AI chat with role-awareness + quick drug ask
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🤖 AI Chat":
    st.markdown(f"""
    <div class='main-header premium-glass'>
      <h2>🤖 AI Clinical Chat</h2>
      <p>Professional pharmacology assistant for {st.session_state.role} mode.</p>
      <div>
        <span class='badge-pill'>Medical Context</span>
        <span class='badge-pill'>Medication Safety</span>
        <span class='badge-pill'>Clinical Clarity</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    available = available_providers()

    presets = {
        "Doctor": [
            "Dose adjustment for metformin in CKD stage 3b?",
            "Compare SGLT2 inhibitors in heart failure with reduced ejection fraction.",
            "Management of warfarin over-anticoagulation (INR >8).",
            "First-line antibiotics for CAP in a penicillin-allergic patient.",
        ],
        "Pharmacist": [
            "Counselling points for a patient starting warfarin.",
            "Drug interactions between warfarin and common antibiotics — full list.",
            "Generic substitution options for unavailable clopidogrel.",
            "Explain therapeutic drug monitoring for vancomycin.",
        ],
        "Nurse": [
            "Signs of digoxin toxicity to watch for.",
            "IV vancomycin administration guidelines and rate.",
            "Morphine dose titration for acute pain — nursing guide.",
            "How to identify and manage anaphylaxis.",
        ],
        "Patient": [
            "What does metformin do and when should I take it?",
            "Can I take ibuprofen with my blood pressure medicine?",
            "What foods should I avoid while taking warfarin?",
            "Explain type 2 diabetes to me in simple terms.",
            "What side effects should I watch for with my new medication?",
            "Is it safe to take two medications at the same time?",
        ],
        "Medical Student": [
            "Explain the mechanism of beta-blockers in heart failure.",
            "Pharmacokinetics of aminoglycosides — clinical importance.",
            "CYP enzyme interactions — full clinical guide.",
            "Explain the renin-angiotensin-aldosterone system and where drugs act.",
        ],
    }

    def run_chat(prompt: str) -> str:
        if is_creator_question(prompt):
            return CREATOR_RESPONSE

        messages = build_pharmacist_messages(
            prompt,
            role=st.session_state.role,
            history=st.session_state.ai_chat_history[:-1],
        )
        return consensus_chat_sync(messages, max_tokens=1600, temperature=0.2)

    def submit_prompt(prompt: str):
        prompt = (prompt or "").strip()
        if not prompt:
            st.warning("Please enter or paste a prompt first.")
            return

        st.session_state.ai_chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("⏳ Preparing your final answer...")
            with st.spinner("🤖 AI thinking..."):
                response = run_chat(prompt)
            placeholder.markdown(response)

        st.session_state.ai_chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    col_presets, col_chat = st.columns([1.15, 2.85])

    with col_presets:
        st.subheader("⚙️ AI mode")
        st.markdown(
            """
            <div class='premium-note'>
              <b>Enhanced reasoning is enabled.</b><br/>
              The chatbot returns one final clinical answer with a concise, professional format.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if all(k in available for k in ["openai", "deepseek"]):
            st.caption("Enhanced answer quality is active.")
        elif available:
            st.caption("Enhanced mode is active with fallback based on available key(s).")
        else:
            st.warning("No API keys detected. Add `OPENAI_API_KEY` and/or `DEEPSEEK_API_KEY`.")

        st.subheader("✍️ Prompt composer")
        composer_mode = st.selectbox(
            "Prompt style",
            ["Clinical summary", "Patient-friendly explanation", "Safety / interaction review", "Teaching note"],
            index=["Clinical summary", "Patient-friendly explanation", "Safety / interaction review", "Teaching note"].index(st.session_state.ai_chat_style),
            key="ai_chat_style",
        )
        composer_topic = st.text_input(
            "Topic / drug / condition",
            placeholder="e.g. warfarin, asthma, CKD dosing, metformin",
            key="ai_chat_topic",
        )
        extra_notes = st.text_area(
            "Extra instructions",
            placeholder="Add patient age, tone, focus areas, or any special instruction.",
            height=100,
            key="ai_chat_notes",
        )

        prompt_preview = build_prompt_preview(st.session_state.role, composer_topic, composer_mode, extra_notes)
        st.text_area("Prompt preview", value=prompt_preview, height=220)
        render_copy_button(prompt_preview, key="prompt_copy_button")
        st.download_button(
            "⬇️ Download prompt",
            data=prompt_preview,
            file_name="pharmacology_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )

        if st.button("➕ Send composed prompt", use_container_width=True):
            submit_prompt(prompt_preview)

        st.subheader("📥 Paste prompt")
        st.text_area(
            "Paste your prompt here (multi-line supported)",
            key="ai_pasted_prompt",
            height=130,
            placeholder="Paste any full prompt here, then click Send pasted prompt.",
        )
        if st.button("🚀 Send pasted prompt", use_container_width=True):
            submit_prompt(st.session_state.ai_pasted_prompt)

        st.divider()
        st.markdown(f"**💡 Quick Questions for {st.session_state.role}:**")
        for preset in presets.get(st.session_state.role, []):
            label = preset[:52] + "..." if len(preset) > 52 else preset
            if st.button(label, key=f"preset_{preset[:30]}", use_container_width=True):
                st.session_state.ai_chat_topic = preset
                submit_prompt(preset)

        st.divider()
        st.markdown("**💊 Ask about a specific drug:**")
        quick_drug = st.text_input("Drug name", placeholder="e.g. Metoprolol")
        quick_mode = st.radio("Mode", ["Clinical info", "Patient-friendly explanation", "Side effects summary"])

        if quick_drug and st.button("🔍 Generate drug prompt", use_container_width=True):
            mode_prompts = {
                "Clinical info": f"Give me a comprehensive clinical summary of {quick_drug}: mechanism, indications, dosing, key interactions, monitoring.",
                "Patient-friendly explanation": f"Explain {quick_drug} to a patient with no medical background. Use simple language, analogies, and emojis. Include what conditions it treats and explain those conditions simply.",
                "Side effects summary": f"List all important side effects of {quick_drug} organized by frequency (common, uncommon, rare, serious). Include what to do if they occur.",
            }
            prompt = mode_prompts.get(quick_mode, f"Tell me about {quick_drug}")
            st.session_state.ai_chat_topic = prompt
            submit_prompt(prompt)

        st.divider()
        if st.session_state.ai_chat_history and st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.ai_chat_history = []
            st.rerun()

        if st.session_state.ai_chat_history:
            st.subheader("📤 Chat export")
            transcript = chat_transcript(st.session_state.ai_chat_history)
            latest_assistant = next(
                (m.get("content", "") for m in reversed(st.session_state.ai_chat_history) if m.get("role") == "assistant"),
                "",
            )
            st.text_area("Latest assistant answer", value=latest_assistant, height=110)
            render_copy_button(latest_assistant, key="copy_latest_answer")
            st.download_button(
                "Download full chat (.txt)",
                data=transcript,
                file_name="pharmacliniq_chat.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.download_button(
                "Download full chat (.json)",
                data=json.dumps(st.session_state.ai_chat_history, indent=2),
                file_name="pharmacliniq_chat.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown(
            """
            <div style='font-size:0.75rem;color:#666;'>
            ⚠️ <b>Disclaimer:</b> AI responses are for educational purposes only.
            Always consult a qualified healthcare professional for clinical decisions.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_chat:
        if not st.session_state.ai_chat_history:
            st.markdown(
                """
                <div class='premium-note' style='text-align:center;padding:2.2rem;color:#3e4a59;'>
                  <h3>👋 Welcome to AI Clinical Chat</h3>
                  <p>I can help with medication guidance, interactions, dosing, patient counselling, and teaching support.</p>
                  <p>Use the prompt composer on the left to build a polished prompt you can copy or send.</p>
                  <br/>
                  <p><i>Type your question below to chat live.</i></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.ai_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_input = st.chat_input(
            f"Ask anything — {st.session_state.role} mode (e.g. 'What is metformin for?', 'Explain hypertension simply')"
        )

        if user_input:
            st.session_state.ai_chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown("⏳ Preparing your final answer...")
                if is_creator_question(user_input):
                    full_response = CREATOR_RESPONSE
                    placeholder.markdown(full_response)
                else:
                    msgs = build_pharmacist_messages(
                        user_input,
                        role=st.session_state.role,
                        history=st.session_state.ai_chat_history[:-1],
                    )
                    with st.spinner("🤖 AI thinking..."):
                        full_response = consensus_chat_sync(msgs, max_tokens=1600, temperature=0.2)
                    placeholder.markdown(full_response)

            st.session_state.ai_chat_history.append({"role": "assistant", "content": full_response})
