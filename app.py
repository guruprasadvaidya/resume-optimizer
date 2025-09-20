import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

# -- Custom Dark Theme Styling --
st.markdown("""
    <style>
        html, body, [class*="css"] { background-color: #181a20 !important; color: #eee !important; }
        .score-bar-container {
            background: #242739; border-radius: 13px; padding: 24px 34px;
            margin-bottom: 14px; text-align: center; 
        }
        .score-label {
            color: #65ffb6; font-weight: 700; font-size: 1.25rem;
            letter-spacing: 0.1rem;
        }
        .stProgress > div > div > div > div {
            background-color: #249e79 !important;
        }
        .skill-section {
            background: #1b2430; border-radius: 9px; padding: 12px 19px;
            margin-bottom: 9px; color: #68a6ff; font-size: 1rem;
        }
        .missing-section {
            background: #44252d; border-radius: 9px; padding: 12px 19px;
            margin-bottom: 9px; color: #ff8989;
        }
        .suggest-box {
            background: #1c212d; border-radius: 11px; padding: 17px 23px;
            margin-bottom: 14px; color: #dbdbdb; font-size: 1.02rem;
            box-shadow: 0 2px 12px #1a242b85;
        }
        .stButton>button {
            background-color: #3686e0 !important; color: #fff !important;
            border-radius: 7px !important; font-weight: 500;
            letter-spacing: 0.03em; margin-top: 8px; font-size: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# -- Skill sets
CANONICAL_SKILLS = [
    "python", "pytorch", "tensorflow", "scikit-learn", "pandas",
    "numpy", "sql", "nlp", "computer vision", "ocr", "transformers",
    "huggingface", "onnx", "triton", "docker", "streamlit",
    "fastapi", "data infrastructure", "model deployment"
]

SYNONYMS = {
    "pytorch": ["torch"],
    "nlp": ["natural language processing"],
    "computer vision": ["cv", "vision"],
    "transformers": ["hugging face"],
    "onnx": ["onnxruntime"],
    "ocr": ["tesseract", "optical character recognition"],
    "model deployment": ["deploy", "deployment"],
    "data infrastructure": ["data pipeline", "etl"]
}

EXAMPLE_TASKS = {
    "pytorch": "trained a CNN on some real images—kinda like magic, but nerdier.",
    "nlp": "built text classification pipelines (bots can read, too).",
    "computer vision": "taught a computer to see (‘cause eyes are overrated).",
    "ocr": "converted chaos (scans) into data zen.",
    "model deployment": "shipped models as legit APIs. Recruiters will love it.",
    "data infrastructure": "kept calm and used ETL on ugly CSVs."
}

# -- Helper Functions
def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

def match_skill(skill, text):
    text_norm = normalize(text)
    if normalize(skill) in text_norm:
        return True
    if any(normalize(syn) in text_norm for syn in SYNONYMS.get(skill, [])):
        return True
    return False

def create_suggestion(skill):
    task = EXAMPLE_TASKS.get(skill.lower())
    if task:
        return f"Implemented {skill}: {task}"
    return f"Worked with {skill}: add a spicy project example."

def get_jd_skills(jd):
    jd_norm = normalize(jd)
    return [
        s for s in CANONICAL_SKILLS
        if normalize(s) in jd_norm or any(normalize(syn) in jd_norm for syn in SYNONYMS.get(s, []))
    ]

def improved_role_fit_score(jd_skills, resume_text):
    score = 0
    matched = []
    for s in jd_skills:
        matches = [s] + SYNONYMS.get(s, [])
        found = False
        for target in matches:
            if normalize(target) in normalize(resume_text):
                found = True
                break
            for word in resume_text.split():
                if difflib.SequenceMatcher(None, normalize(word), normalize(target)).ratio() > 0.74:
                    found = True
                    break
            if found:
                break
        if found:
            matched.append(s)
            score += 1
    denom = max(len(jd_skills), 1)
    return round(100.0 * score / denom, 1), matched

def find_skills_section(doc):
    for p in doc.paragraphs:
        if "SKILLS" in p.text.upper():
            return p
    return None

def insert_to_resume(docx_file, skills_to_add, bullets_to_add):
    buf_in = BytesIO(docx_file.getvalue())
    doc = Document(buf_in)

    # Add skills to skills section without breaking format
    p_skill = find_skills_section(doc)
    if p_skill and skills_to_add:
        runs = p_skill.runs
        text = p_skill.text.strip()
        if "|" in text:
            segments = [seg.strip() for seg in text.split("|")]
        elif "," in text:
            segments = [seg.strip() for seg in text.split(",")]
        else:
            segments = text.split()
        current_set = set(normalize(seg) for seg in segments)
        for s in skills_to_add:
            if normalize(s) not in current_set:
                segments.append(s)
        full_line = " | ".join(segments)
        for run in runs:
            run.text = ""
        p_skill.add_run(full_line)

    # Add bullets as new section at the end with bullet formatting
    if bullets_to_add:
        doc.add_paragraph("")
        doc.add_paragraph("--- Added Skills / Projects ---")
        for b in bullets_to_add:
            doc.add_paragraph(b, style="List Bullet")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def get_score_comment(score):
    if score < 40:
        return "☠️ Bruh. Initiate skill rescue."
    if score < 65:
        return "Decent. But recruiters love overachievers."
    if score < 80:
        return "Not bad—few more tweaks and you'll pop."
    return "🔥 You’re basically LinkedIn verified..."

# -- Streamlit App UI/UX ---

st.title("AI Resume Optimizer")
st.markdown("""
Every resume needs a hero arc.  
Drop your JD, upload your docx, let this *savage AI* tell you if you pass the vibe check (and what’s missing).
""")

st.subheader("Paste the Job Description")
job_desc = st.text_area("_Ctrl+V JD here and see what skills you’re missing (no judgment... mostly)._", height=100)

st.subheader("Upload your Résumé (.docx)")
file_up = st.file_uploader("Upload the docx. Pinky promise: No cringe.", type=["docx"])

if job_desc and file_up:
    if st.button("Run the Roast 🔥"):
        doc = Document(file_up)
        resume_text = "\n".join([p.text for p in doc.paragraphs])
        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = improved_role_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        st.markdown(f"""
        <div class="score-bar-container">
            <span class="score-label">Role-Fit Score:</span><br>
            <span style="font-size:2.2rem;color:#33ffe0;font-weight:700">{role_fit}%</span><br>
            <span style="color:#bebee7;font-size:1.07rem">{get_score_comment(role_fit)}</span>
        </div>""", unsafe_allow_html=True)
        st.progress(role_fit)

        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None (Oof).'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'All there. You’re a unit!'}</div>", unsafe_allow_html=True)

        st.subheader("Suggested Glow-Ups 🧠")
        st.info("Check a suggestion, pick where it lands, and hit update. Resume gets a level-up. Zero formatting drama.")

        selected_for_resume = []
        for i, skill in enumerate(missing_skills):
            suggest = create_suggestion(skill)
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {suggest}</div>", unsafe_allow_html=True)
            sel = st.checkbox(f"Add `{skill}` to resume", key=f"sel_{i}")
            if sel:
                opt = st.radio(f"Where to drop `{skill}`?", ["Skills Section (for robots)", "Bullet Points (for humans)"], key=f"opt_{i}")
                selected_for_resume.append((skill, suggest, opt))

        if selected_for_resume and st.button("Update My Resume 🚀"):
            with st.spinner("Injecting upgrades..."):
                buf_out = insert_to_resume(
                    file_up,
                    [s for s, _, pos in selected_for_resume if pos.startswith("Skills")],
                    [desc for _, desc, pos in selected_for_resume if pos.startswith("Bullet")]
                )
                st.success("Done! Download below, upload, conquer.")
                st.download_button(
                    "📥 Download Updated Résumé",
                    buf_out.getvalue(),
                    file_name="resume_UPDATED.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
