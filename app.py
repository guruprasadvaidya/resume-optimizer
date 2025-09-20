import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re
from collections import Counter

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

# Dark theme CSS
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
        .keyword-density-table th, .keyword-density-table td {
            padding: 6px 12px;
            border-bottom: 1px solid #444;
        }
        .keyword-density-table th {
            color: #65ffb6;
        }
        .keyword-density-good {
            color: #70ea98;
            font-weight: 600;
        }
        .keyword-density-low {
            color: #e5e020;
            font-weight: 600;
        }
        .keyword-density-high {
            color: #ff5c5c;
            font-weight: 700;
        }
        .stButton>button {
            background-color: #3686e0 !important; color: #fff !important;
            border-radius: 7px !important; font-weight: 500;
            letter-spacing: 0.03em; margin-top: 8px; font-size: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

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

def create_suggestion(skill):
    ex = EXAMPLE_TASKS.get(skill.lower())
    return f"Implemented {skill}: {ex}" if ex else f"Worked with {skill}: add a project snippet."

def get_jd_skills(jd_text):
    norm_jd = normalize(jd_text)
    return [s for s in CANONICAL_SKILLS if normalize(s) in norm_jd or any(normalize(syn) in norm_jd for syn in SYNONYMS.get(s, []))]

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
    denom = max(len(jd_skills), 1)
    return round(100.0 * score / denom, 1), matched

def feedback_text(score):
    if score < 40:
        return "☠️ Major gap alert - time to skill up!"
    if score < 65:
        return "Good start, but recruiters want more action."
    if score < 80:
        return "Almost there - polish a few more skills."
    return "🔥 You’re shining, time for interviews!"

def compute_keyword_density(jd_skills, resume_text):
    words = normalize(resume_text).split()
    counts = Counter(words)
    total_words = len(words)
    density_info = []
    for skill in jd_skills:
        norm_skill = normalize(skill)
        cnt = counts[norm_skill]
        for syn in SYNONYMS.get(skill, []):
            cnt += counts[normalize(syn)]
        density = (cnt / total_words) * 100 if total_words > 0 else 0
        density_info.append((skill, cnt, density))
    return density_info

st.title("AI Resume Optimizer")

st.markdown("""
Drop your Job Description and .docx resume to see how well you match — then discover personalized improvements to make your resume sparkle.  
No cap, no fluff, just real talk for your job grind.
""")

st.subheader("Paste the full Job Description here to check your fit.")
job_desc = st.text_area("Paste Job Description", height=130)

st.subheader("Upload your .docx resume")
uploaded_file = st.file_uploader("Select your .docx file", type=["docx"])

if job_desc and uploaded_file:
    if st.button("Check My Fit"):
        doc = Document(uploaded_file)
        resume_text = "\n".join(p.text for p in doc.paragraphs)

        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = compute_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        st.markdown(f"""
        <div class="score-bar-container">
            <span class="score-label">Role-Fit Score:</span><br>
            <span style="font-size:2.3rem; color:#33ffe0; font-weight:700;">{role_fit}%</span><br>
            <span style="color:#bebee7; font-size:1.1rem;">{feedback_text(role_fit)}</span>
        </div>""", unsafe_allow_html=True)
        st.progress(role_fit / 100)

        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None. Could be better!'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'Solid set! You’re good to go.'}</div>", unsafe_allow_html=True)

        st.subheader("Suggested Improvements")
        st.info("Focus on these missing skills to level up your resume and grab recruiters’ attention.")

        for skill in missing_skills:
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {create_suggestion(skill)}</div>", unsafe_allow_html=True)

        # Keyword Density Section
        st.subheader("Keyword Density & ATS Compatibility Check")
        density_data = compute_keyword_density(jd_skills, resume_text)

        st.markdown("""
        <style>
        .keyword-density-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .keyword-density-table th, .keyword-density-table td {
            text-align: left; padding: 8px; border-bottom: 1px solid #444; font-size: 14px;
        }
        .keyword-density-good { color: #70ea98; font-weight: 600; }
        .keyword-density-low { color: #e5e020; font-weight: 600; }
        .keyword-density-high { color: #ff5c5c; font-weight: 700; }
        </style>
        """, unsafe_allow_html=True)

        if density_data:
            table_html = """
            <table class='keyword-density-table'>
            <tr><th>Skill</th><th>Mentions</th><th>Density (%)</th><th>ATS Feedback</th></tr>
            """
            for skill, mentions, density in density_data:
                if mentions == 0:
                    status = "<span class='keyword-density-low'>Missing - add it!</span>"
                elif mentions > 5 or density > 1.0:
                    status = "<span class='keyword-density-high'>Too high - avoid ATS flag</span>"
                else:
                    status = "<span class='keyword-density-good'>Good</span>"
                table_html += f"<tr><td>{skill}</td><td>{mentions}</td><td>{density:.2f}</td><td>{status}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.write("No JD skills detected for density analysis.")
