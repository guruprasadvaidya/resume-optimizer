import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re

# App config + dark theme CSS
st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

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

# Core data and mappings
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

# Helpers
def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

def match_skill(skill, text):
    norm_text = normalize(text)
    if normalize(skill) in norm_text:
        return True
    if any(normalize(syn) in norm_text for syn in SYNONYMS.get(skill, [])):
        return True
    return False

def create_suggestion(skill):
    example = EXAMPLE_TASKS.get(skill.lower())
    if example:
        return f"Implemented {skill}: {example}"
    return f"Worked with {skill}: add a cool project snippet."

def get_jd_skills(jd_text):
    norm_jd = normalize(jd_text)
    return [
        skill for skill in CANONICAL_SKILLS
        if normalize(skill) in norm_jd or any(normalize(syn) in norm_jd for syn in SYNONYMS.get(skill, []))
    ]

def compute_fit_score(jd_skills, resume_text):
    score = 0
    matched = []
    for skill in jd_skills:
        synonyms = [skill] + SYNONYMS.get(skill, [])
        found = False
        for target in synonyms:
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
            matched.append(skill)
            score += 1
    denominator = max(len(jd_skills), 1)
    percentage = round(100.0 * score / denominator, 1)
    return percentage, matched

def get_skills_paragraph(doc):
    for para in doc.paragraphs:
        if "SKILLS" in para.text.upper():
            return para
    return None

def update_resume(docx_file, skills_to_add, bullets_to_add):
    buffer_in = BytesIO(docx_file.getvalue())
    doc = Document(buffer_in)

    skills_para = get_skills_paragraph(doc)
    if skills_para and skills_to_add:
        orig_text = skills_para.text.strip()
        if "|" in orig_text:
            segments = [s.strip() for s in orig_text.split("|")]
            delimiter = " | "
        elif "," in orig_text:
            segments = [s.strip() for s in orig_text.split(",")]
            delimiter = ", "
        else:
            segments = orig_text.split()
            delimiter = " "

        norm_set = set(normalize(s) for s in segments)
        for skill in skills_to_add:
            if normalize(skill) not in norm_set:
                segments.append(skill)
        new_text = delimiter.join(segments)

        # clear all runs, add one run for new text to best preserve format
        for run in skills_para.runs:
            run.text = ""
        skills_para.add_run(new_text)

    # Add new bullets section if any
    if bullets_to_add:
        doc.add_paragraph("")
        doc.add_paragraph("--- Added Skills / Projects ---")
        for bullet in bullets_to_add:
            doc.add_paragraph(bullet, style="List Bullet")

    buf_out = BytesIO()
    doc.save(buf_out)
    buf_out.seek(0)
    return buf_out

def feedback_text(score):
    if score < 40:
        return "☠️ Major gap alert - time to skill up!"
    if score < 65:
        return "Good start, but recruiters want more action."
    if score < 80:
        return "Almost there - polish a few more skills."
    return "🔥 You’re shining, time for interviews!"

# UI

st.title("AI Resume Optimizer")

st.markdown("""
Drop your Job Description & resume to see how you match — then glow-up your resume to land the gig.
""")

st.subheader("Paste the full Job Description here to check your fit.")
job_desc = st.text_area("Paste Job Description", height=130)

st.subheader("Upload your .docx resume")
uploaded_file = st.file_uploader("Select your .docx file", type=["docx"])

if job_desc and uploaded_file:
    if st.button("Check My Fit"):
        doc = Document(uploaded_file)
        resume_text = "\n".join(para.text for para in doc.paragraphs)

        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = compute_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        # Show role fit with progress bar scaled 0–1
        st.markdown(f"""
        <div class="score-bar-container">
            <span class="score-label">Role-Fit Score:</span><br>
            <span style="font-size:2.3rem; color:#33ffe0; font-weight:700;">{role_fit}%</span><br>
            <span style="color:#bebee7; font-size:1.1rem;">{feedback_text(role_fit)}</span>
        </div>
        """, unsafe_allow_html=True)
        st.progress(role_fit / 100)

        # Show matched & missing skills
        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None. Could be better!'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'Full house! You’re set.'}</div>", unsafe_allow_html=True)

        # Suggestions + checkboxes
        st.subheader("Suggested Glow-Ups")
        st.info("Pick the skills you wanna add, where you want ‘em, and then update your resume. Simple!")

        choices = []
        for idx, skill in enumerate(missing_skills):
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {create_suggestion(skill)}</div>", unsafe_allow_html=True)
            checked = st.checkbox(f"Add '{skill}' to resume?", key=f"check_{idx}")
            if checked:
                loc = st.radio(f"Where to put '{skill}'?", ["Skills Section", "Bullet Points (real projects)"], key=f"loc_{idx}")
                choices.append((skill, loc))

        if choices:
            if st.button("Update Resume with Selected Suggestions"):
                updated = update_resume(
                    uploaded_file,
                    [skill for skill, loc in choices if loc == "Skills Section"],
                    [f"Implemented {skill}." for skill, loc in choices if loc == "Bullet Points (real projects)"]
                )
                st.success("Boom! Your resume got a glow-up. Download below.")
                st.download_button(
                    label="📥 Download Updated Resume",
                    data=updated.getvalue(),
                    file_name="resume_updated.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
