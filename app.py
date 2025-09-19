import streamlit as st
from docx import Document
import re, difflib

# ----- App Title -----
st.title("AI Resume Optimizer")
st.markdown("Upload your resume and see how it fits the job description!")

# ----- Job Description (example) -----
JOB_DESC = """
Looking for a Machine Learning Engineer Intern with skills in Python, PyTorch, NLP, OCR,
computer vision, data infrastructure, and model deployment.
"""

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

# ----- Functions -----
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

# ----- Upload Resume -----
uploaded_file = st.file_uploader("Upload your resume (.docx)", type="docx")

if uploaded_file:
    doc = Document(uploaded_file)
    resume_text = "\n".join([p.text for p in doc.paragraphs])

    # ----- Identify Skills -----
    jd_norm = normalize(JOB_DESC)
    jd_skills = [s for s in CANONICAL_SKILLS if normalize(s) in jd_norm or any(normalize(syn) in jd_norm for syn in SYNONYMS.get(s,[]))]
    matched = [s for s in jd_skills if match_skill(s, resume_text)]
    missing = [s for s in jd_skills if s not in matched]
    score = round(len(matched)/ (len(jd_skills) or 1) * 100,2)

    # ----- Generate Suggested Bullets -----
    suggested_bullets = []
    for s in missing[:6]:
        task = EXAMPLE_TASKS.get(s.lower(), None)
        if task: suggested_bullets.append(f"- Implemented {s}: {task}.")
        else: suggested_bullets.append(f"- Worked with {s}: describe project briefly.")

    # ----- Show Results -----
    st.subheader(f"🔎 Role-fit Score: {score}%")
    st.write("✅ Matched Skills:", matched)
    st.write("⚠️ Missing Skills:", missing)
    st.write("✍️ Suggested bullets to add:")
    for b in suggested_bullets:
        st.write(b)

    # ----- Save Optimized Resume -----
    if suggested_bullets:
        doc.add_paragraph("\n--- Added Skills / Projects for Role Fit ---")
        for b in suggested_bullets:
            doc.add_paragraph(b)
        doc.save("resume_optimized.docx")
        st.success("💾 Optimized resume saved! Download below:")
        with open("resume_optimized.docx", "rb") as f:
            st.download_button("Download Resume", f, file_name="resume_optimized.docx")
