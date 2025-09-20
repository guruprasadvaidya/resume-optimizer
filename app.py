import streamlit as st
from docx import Document
from io import BytesIO
import re, difflib

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")
st.title("AI Resume Optimizer")
st.markdown("Analyze your resume against a Job Description and get suggestions to improve role-fit!")

# --- Step 1: Job Description ---
st.subheader("Step 1: Paste Job Description")
job_desc_input = st.text_area("Paste the Job Description here...", height=150)

# --- Step 2: Upload Resume ---
st.subheader("Step 2: Upload Resume (.docx)")
uploaded_file = st.file_uploader("Upload your resume", type="docx")

# --- Canonical Skills & Synonyms ---
CANONICAL_SKILLS = [
    "python","pytorch","tensorflow","scikit-learn","pandas","numpy","sql","nlp",
    "computer vision","ocr","transformers","huggingface","onnx","triton","docker",
    "streamlit","fastapi","data infrastructure","model deployment"
]

SYNONYMS = {
    "pytorch":["torch"],
    "nlp":["natural language processing"],
    "computer vision":["cv","vision"],
    "transformers":["hugging face"],
    "onnx":["onnxruntime"],
    "ocr":["tesseract","optical character recognition"],
    "model deployment":["deploy","deployment"],
    "data infrastructure":["data pipeline","etl"]
}

EXAMPLE_TASKS = {
    "pytorch": "trained a small CNN on CIFAR-10 using PyTorch and reported accuracy improvements",
    "nlp": "built NER/text-classification pipelines using Hugging Face transformers",
    "computer vision": "implemented a simple object detection pipeline",
    "ocr": "used Tesseract/Donut to extract text from scanned documents",
    "model deployment": "deployed a model as a REST API using FastAPI and Docker",
    "data infrastructure": "created a mini ETL pipeline to clean CSV data"
}

# --- Helper Functions ---
def normalize(s): return re.sub(r'[^a-z0-9]','',s.lower())

def match_skill(skill, text):
    text_norm = normalize(text)
    if normalize(skill) in text_norm:
        return True
    if any(normalize(syn) in text_norm for syn in SYNONYMS.get(skill,[])):
        return True
    return False

def create_suggestion(skill):
    task = EXAMPLE_TASKS.get(skill.lower(), None)
    if task:
        return f"Implemented {skill}: {task}."
    return f"Worked with {skill}: describe project briefly."

def insert_skills_and_bullets(doc_file, skills_to_add, bullets_to_add):
    doc_file.seek(0)
    doc = Document(doc_file)
    # Add missing skills to Skills section
    for p in doc.paragraphs:
        if "SKILLS" in p.text.upper():
            current = p.text
            new_skills = current + " | " + " | ".join(skills_to_add)
            p.text = new_skills
            break
    # Add bullets at end
    if bullets_to_add:
        doc.add_paragraph("\n--- Added Skills / Projects ---")
        for b in bullets_to_add:
            doc.add_paragraph(b)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- Step 3: Process Button ---
if job_desc_input and uploaded_file:
    if st.button("▶️ Process"):
        doc = Document(uploaded_file)
        resume_text = "\n".join([p.text for p in doc.paragraphs])
        
        # --- Match Skills ---
        jd_skills = [s for s in CANONICAL_SKILLS if normalize(s) in normalize(job_desc_input) or any(normalize(syn) in normalize(job_desc_input) for syn in SYNONYMS.get(s,[]))]
        matched_skills = [s for s in jd_skills if match_skill(s, resume_text)]
        missing_skills = [s for s in jd_skills if s not in matched_skills]
        role_fit = round(len(matched_skills) / (len(jd_skills) or 1) * 100, 1)
        
        # --- Display in Cards ---
        st.subheader(f"🔎 Role-fit Score: {role_fit}%")
        st.markdown(
            f"<div style='background-color:#e6ffed;padding:12px;border-radius:10px'>"
            f"<b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None'}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background-color:#ffe6e6;padding:12px;border-radius:10px'>"
            f"<b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'None'}</div>", unsafe_allow_html=True)

        # --- Suggested Improvements Section ---
        st.subheader("✍️ Suggested Improvements")
        selected_for_resume = []
        for i, skill in enumerate(missing_skills):
            suggestion_text = create_suggestion(skill)
            st.markdown(
                f"<div style='background-color:#fff8e6;padding:10px;border-radius:10px;margin-bottom:5px'>"
                f"<b>{skill}</b>: {suggestion_text}</div>", unsafe_allow_html=True)
            if st.checkbox(f"Add '{skill}'?", key=f"sel_{i}"):
                choice = st.radio(f"Add '{skill}' to:", ("Skills Section", "Bullet Points at End"), key=f"choice_{i}")
                selected_for_resume.append((skill, suggestion_text, choice))
        
        if selected_for_resume:
            confirm = st.checkbox("✅ Confirm to apply selected suggestions to your resume")
            if confirm:
                apply_btn = st.button("⬇️ Apply & Download Updated Resume")
                if apply_btn:
                    updated_file = insert_skills_and_bullets(
                        uploaded_file,
                        [s for s, _, c in selected_for_resume if c=="Skills Section"],
                        [b for _, b, c in selected_for_resume if c=="Bullet Points at End"]
                    )
                    st.success("Updated resume ready for download!")
                    st.download_button(
                        "📥 Download Updated Resume",
                        updated_file.getvalue(),
                        file_name="resume_updated.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
