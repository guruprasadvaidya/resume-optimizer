import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

# Dark theme styling
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

# Skills and synonyms data
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
    # Load doc file content
    buf_in = BytesIO(docx_file.getvalue())
    doc = Document(buf_in)

    # Safely edit Skills section
    p_skill = find_skills_section(doc)
    if p_skill and skills_to_add:
        original_text = p_skill.text.strip()
        # Try splitting by | or commas or spaces
        if "|" in original_text:
            segments = [seg.strip() for seg in original_text.split("|")]
            delimiter = " | "
        elif "," in original_text:
            segments = [seg.strip() for seg in original_text.split(",")]
            delimiter = ", "
        else:
            segments = original_text.split()
            delimiter = " "
        current_bool_set = {normalize(seg) for seg in segments}
        # Append new skills without duplicates
        for skill in skills_to_add:
            if normalize(skill) not in current_bool_set:
                segments.append(skill)
        new_text = delimiter.join(segments)
        # Clear all runs and add new text in one run to preserve formatting as best as possible
        for run in p_skill.runs:
            run.text = ""
        p_skill.add_run(new_text)

    # Add new bullet points in a new section at the end
    if bullets_to_add:
        # Add a separating blank line
        doc.add_paragraph("")
        doc.add_paragraph("--- Added Skills / Projects ---")
        for bullet in bullets_to_add:
            doc.add_paragraph(bullet, style="List Bullet")

    # Save edited doc to buffer and return
    buf_out = BytesIO()
    doc.save(buf_out)
    buf_out.seek(0)
    return buf_out

def get_score_comment(score):
    if score < 40:
        return "☠️ Bruh. Initiate skill rescue."
    if score < 65:
        return "Decent. But recruiters love overachievers."
    if score < 80:
        return "Not bad—few more tweaks and you'll pop."
    return "🔥 You’re basically LinkedIn verified..."

# HEADER
st.title("AI Resume Optimizer")
st.markdown("""
Every resume needs a hero arc.  
Drop your JD, upload your docx file, and this AI will help level up your application.
""")

# INPUTS
st.subheader("Paste the Job Description")
job_desc = st.text_area("Paste the full Job Description here to check your fit.", height=130)

st.subheader("Upload your Résumé (.docx)")
file_up = st.file_uploader("Upload your .docx resume", type=["docx"])

# PROCESS FLOW
if job_desc and file_up:
    if st.button("Analyze Fit"):
        # Read resume content
        doc = Document(file_up)
        resume_text = "\n".join([p.text for p in doc.paragraphs])

        # Extract skills from JD and match
        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = improved_role_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        # Display role fit score with progress bar scaled [0,1]
        st.markdown(f"""
        <div class="score-bar-container">
            <span class="score-label">Role-Fit Score:</span><br>
            <span style="font-size:2.3rem;color:#33ffe0;font-weight:700">{role_fit}%</span><br>
            <span style="color:#bebee7;font-size:1.1rem">{get_score_comment(role_fit)}</span>
        </div>""", unsafe_allow_html=True)
        st.progress(role_fit / 100)

        # Show matched and missing skills
        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None (Oof).'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'All there. You’re a unit!'}</div>", unsafe_allow_html=True)

        # Show suggestions and options for updating resume
        st.subheader("Suggested Improvements")
        st.info("Select which suggestions to add to your resume. Choose where each goes. Then update your file below.")

        selected_for_resume = []
        for i, skill in enumerate(missing_skills):
            suggest = create_suggestion(skill)
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {suggest}</div>", unsafe_allow_html=True)
            add_skill = st.checkbox(f"Add '{skill}' to my resume", key=f"sel_{i}")
            if add_skill:
                location = st.radio(f"Add '{skill}' to:", ["Skills Section", "Bullet Points (show real projects)"], key=f"loc_{i}")
                selected_for_resume.append((skill, suggest, location))

        # Button to update and download resume only if any chosen
        if selected_for_resume:
            if st.button("Update Resume"):
                updated_file = insert_to_resume(
                    file_up,
                    [s for s, _, loc in selected_for_resume if loc == "Skills Section"],
                    [desc for _, desc, loc in selected_for_resume if loc == "Bullet Points (show real projects)"]
                )
                st.success("Resume updated with your selected suggestions!")
                st.download_button(
                    label="Download Updated Resume",
                    data=updated_file.getvalue(),
                    file_name="resume_updated.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
