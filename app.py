import streamlit as st
from docx import Document
import re, difflib
from io import BytesIO

# ----- App Title -----
st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")
st.title("AI Resume Optimizer")
st.markdown("Upload your resume and compare it with a job description to get personalized suggestions!")

# ----- Job Description (user input) -----
st.subheader("Step 1: Paste Job Description")
job_desc_input = st.text_area("Paste the Job Description here...", height=150)

# ----- Upload Resume -----
st.subheader("Step 2: Upload Resume (.docx)")
uploaded_file = st.file_uploader("Upload your resume", type="docx")

# ----- Canonical skills & synonyms -----
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

# ----- Helper Functions -----
def normalize(s): return re.sub(r'[^a-z0-9]','',s.lower())

def text_tokens_and_bigrams(text):
    tokens = re.findall(r'\w+', text.lower())
    bigrams = [' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)]
    return tokens + bigrams

def match_skill(skill, resume_text):
    skill_norm = normalize(skill)
    resume_norm = normalize(resume_text)
    if skill_norm in resume_norm:
        return True
    if any(normalize(syn) in resume_norm for syn in SYNONYMS.get(skill,[])):
        return True
    tokens = text_tokens_and_bigrams(resume_text)
    match = difflib.get_close_matches(skill.lower(), tokens, n=1, cutoff=0.85)
    return bool(match)

def create_suggestion_for_skill(skill):
    task = EXAMPLE_TASKS.get(skill.lower(), None)
    if task:
        return f"- Implemented {skill}: {task}."
    return f"- Worked with {skill}: describe project briefly."

def insert_skills_into_docx(file, skills, bullets):
    file.seek(0)
    doc = Document(file)
    # Add missing skills to skills section
    for p in doc.paragraphs:
        if "SKILLS" in p.text.upper():
            current = p.text
            new_skills = current + " | " + " | ".join(skills)
            p.text = new_skills
            break
    # Add bullets at end
    if bullets:
        doc.add_paragraph("\n--- Added Skills / Projects ---")
        for b in bullets:
            doc.add_paragraph(b)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ----- Process Button -----
if job_desc_input and uploaded_file:
    if st.button("▶️ Process Resume"):
        doc = Document(uploaded_file)
        resume_text = "\n".join([p.text for p in doc.paragraphs])

        # ----- Identify Skills -----
        jd_norm = normalize(job_desc_input)
        jd_skills = [s for s in CANONICAL_SKILLS if normalize(s) in jd_norm or any(normalize(syn) in jd_norm for syn in SYNONYMS.get(s,[]))]
        matched = [s for s in jd_skills if match_skill(s, resume_text)]
        missing = [s for s in jd_skills if s not in matched]
        score = round(len(matched)/ (len(jd_skills) or 1) * 100,2)

        # ----- Display results in cards -----
        st.subheader(f"🔎 Role-fit Score: {score}%")

        st.markdown(
            f"<div style='background-color:#d4edda;padding:12px;border-radius:8px'>"
            f"<b>✅ Matched Skills:</b> {', '.join(matched) if matched else 'None'}</div>", unsafe_allow_html=True)

        st.markdown(
            f"<div style='background-color:#f8d7da;padding:12px;border-radius:8px'>"
            f"<b>⚠️ Missing Skills:</b> {', '.join(missing) if missing else 'None'}</div>", unsafe_allow_html=True)

        # ----- Suggested bullets with selection -----
        suggestion_items = []
        if missing:
            st.subheader("✍️ Suggested improvements")
            for i, skill in enumerate(missing):
                suggestion_text = create_suggestion_for_skill(skill)
                st.markdown(
                    f"<div style='background-color:#fff3cd;padding:12px;border-radius:8px;margin-bottom:8px'>"
                    f"<b>{skill}</b><br>{suggestion_text}</div>", unsafe_allow_html=True)
                selected = st.checkbox(f"Add '{skill}'?", key=f"sel_{i}")
                if selected:
                    choice = st.radio(f"Where to add '{skill}'?", ("Add to Skills", "Add as bullet"), key=f"where_{i}")
                    suggestion_items.append((skill, suggestion_text, choice))

            # confirmation + apply
            if suggestion_items:
                confirm = st.checkbox("✅ I confirm I want to apply these suggestions to my resume.")
                apply_btn = st.button("⬇️ Apply & Download Updated Resume", disabled=not confirm)

                if apply_btn and confirm:
                    updated_buf = insert_skills_into_docx(uploaded_file,
                                                         [s for s, _, c in suggestion_items if c=="Add to Skills"],
                                                         [b for _, b, c in suggestion_items if c=="Add as bullet"])
                    st.success("Resume updated with suggestions!")
                    st.download_button(
                        label="📥 Download updated resume",
                        data=updated_buf.getvalue(),
                        file_name="resume_updated.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
