import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

def set_custom_theme():
    # For robust dark UI
    st.markdown("""
        <style>
            html, body, [class*="css"]  { background-color: #181818 !important; color: #ededed !important; }
            .score-card {
                background: #23272a;
                color: #40c463;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                font-size: 2rem;
                text-align: center;
            }
            .skill-section {
                background: #222b38;
                border-radius: 10px;
                padding: 12px 20px;
                margin-bottom: 12px;
                color: #7cdfff;
                font-weight: bold;
                font-size: 1.1rem;
            }
            .missing-section {
                background: #3e1a24;
                border-radius: 10px;
                padding: 12px 20px;
                margin-bottom: 12px;
                color: #ff7272;
                font-weight: bold;
                font-size: 1.1rem;
            }
            .suggest-box {
                background: #232323;
                border-radius: 10px;
                padding: 12px 20px;
                margin-bottom: 16px;
                color: #bdbdbd;
                font-size: 1rem;
                box-shadow: 0 2px 8px rgba(50,50,50,0.5);
            }
            .stButton>button {
                background-color: #2676c9 !important;
                color: #fff !important;
                border-radius: 6px !important;
                padding: 8px 20px !important;
                border:none;
                font-weight: bold;
                margin-top:10px;
                font-size: 1.1rem;
            }
        </style>
    """, unsafe_allow_html=True)

set_custom_theme()
st.title("📝 AI Resume Optimizer")
st.markdown("Analyze your resume against a job description, see fit, and get precise resume upgrade suggestions!")

# --- Data
CANONICAL_SKILLS = [
    "python", "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "sql", "nlp",
    "computer vision", "ocr", "transformers", "huggingface", "onnx", "triton", "docker",
    "streamlit", "fastapi", "data infrastructure", "model deployment"
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
    "pytorch": "trained and evaluated a CNN on CIFAR-10 using PyTorch, reporting test accuracy.",
    "nlp": "built NER or text-classification pipelines using Hugging Face transformers.",
    "computer vision": "implemented image classification or basic object detection.",
    "ocr": "used Tesseract to extract text from scanned docs.",
    "model deployment": "deployed ML models as REST APIs with FastAPI and Docker.",
    "data infrastructure": "built small batch ETL pipelines to clean CSV data."
}

# --- Helper functions
def normalize(s): return re.sub(r'[^a-z0-9]', '', s.lower())
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
    return f"Worked with {skill}: describe project or application."

def get_jd_skills(jd):
    norm_jd = normalize(jd)
    return [
        s for s in CANONICAL_SKILLS
        if normalize(s) in norm_jd or any(normalize(syn) in norm_jd for syn in SYNONYMS.get(s, []))
    ]

def improved_role_fit_score(jd_skills, resume_text):
    # Partial similarity (not binary) using difflib for subtler match
    score = 0
    matched = []
    for s in jd_skills:
        matches = [s] + SYNONYMS.get(s, [])
        found = False
        for target in matches:
            if normalize(target) in normalize(resume_text):
                found = True
                break
            # fuzzy match by ratio
            for word in resume_text.split():
                if difflib.SequenceMatcher(None, normalize(word), normalize(target)).ratio() > 0.74:
                    found = True
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
    # load doc
    buf_in = BytesIO(docx_file.getvalue())
    doc = Document(buf_in)

    # Find skill section and add, but preserve format
    p_skill = find_skills_section(doc)
    if p_skill and skills_to_add:
        # Split by pipe or comma, reconstruct line with new skills, preserve runs
        runs = p_skill.runs
        text = p_skill.text.strip()
        if "|" in text:
            segments = [seg.strip() for seg in text.split("|")]
        elif "," in text:
            segments = [seg.strip() for seg in text.split(",")]
        else:
            segments = text.split()
        current_set = set([normalize(seg) for seg in segments])
        for s in skills_to_add:
            if normalize(s) not in current_set:
                segments.append(s)
        full_line = " | ".join(segments)
        # Clear old and rewrite with runs (preserve style for entire paragraph)
        for run in runs:
            run.text = ""
        p_skill.add_run(full_line)

    # Add bullets to a new "Added Projects/Skills" section with same style as past bullets
    if bullets_to_add:
        doc.add_paragraph("")  # spacing
        header = doc.add_paragraph("--- Added Skills / Projects ---")
        for b in bullets_to_add:
            p = doc.add_paragraph(b, style="List Bullet")
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- UI and Functionality
st.subheader("1️⃣ Paste Job Description")
job_desc = st.text_area("Job Description", height=120, placeholder="Paste the full JD here...")

st.subheader("2️⃣ Upload Resume (.docx only)")
file_up = st.file_uploader("Upload resume", type=["docx"])

if job_desc and file_up:
    if st.button("🔍 Analyze & Suggest"):
        doc = Document(file_up)
        resume_text = "\n".join([p.text for p in doc.paragraphs])
        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = improved_role_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        st.markdown(f"<div class='score-card'>Role-fit Score: {role_fit} %</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'None'}</div>", unsafe_allow_html=True)

        st.subheader("3️⃣ Suggested Improvements")
        selected_for_resume = []
        for i, skill in enumerate(missing_skills):
            suggest = create_suggestion(skill)
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {suggest}</div>", unsafe_allow_html=True)
            sel = st.checkbox(f"Add '{skill}' to resume", key=f"sel_{i}")
            if sel:
                opt = st.radio(f"Where to add '{skill}'?", ["Skills Section", "Bullet Points (at end)"], key=f"opt_{i}")
                selected_for_resume.append((skill, suggest, opt))

        if selected_for_resume:
            if st.button("✏️ Update Resume with Selected Suggestions"):
                buf_out = insert_to_resume(
                    file_up,
                    [s for s, _, pos in selected_for_resume if pos == "Skills Section"],
                    [desc for _, desc, pos in selected_for_resume if pos.startswith("Bullet")]
                )
                st.success("Resume updated with selected suggestions!")
                st.download_button(
                    "📥 Download Updated Resume",
                    buf_out.getvalue(),
                    file_name="resume_updated.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
