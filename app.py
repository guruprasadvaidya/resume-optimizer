import streamlit as st
from docx import Document
import pdfplumber
from io import BytesIO
import difflib
import re
from collections import Counter

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

# Dark theme CSS with consistent fonts and buttons
st.markdown("""
    <style>
        html, body, [class*="css"] { background-color: #181a20 !important; color: #eee !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
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

def extract_resume_text(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type == "docx":
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif file_type == "pdf":
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + '\n'
        return text
    else:
        return None

def compute_fit_score(jd_skills, resume_text):
    norm_resume = normalize(resume_text)
    matched = []
    total_score = 0
    for skill in jd_skills:
        synonyms = [skill] + SYNONYMS.get(skill, [])
        skill_score = 0
        for target in synonyms:
            norm_target = normalize(target)
            if norm_target in norm_resume:
                skill_score = 1
                break
            for word in norm_resume.split():
                sim_ratio = difflib.SequenceMatcher(None, word, norm_target).ratio()
                if sim_ratio >= 0.8:
                    skill_score = sim_ratio
                    break
            if skill_score:
                break
        if skill_score:
            matched.append(skill)
        total_score += skill_score
    denom = max(len(jd_skills), 1)
    fit_pct = round(100.0 * total_score / denom, 1)
    return fit_pct, matched

def feedback_text(score):
    if score < 20:
        return "Looks like your current resume doesn’t quite align with this job description yet. No worries — this is your chance to grow and glow! 🌱✨"
    if score < 50:
        return "You're on the way! Focus on these skills to boost your profile and make a stronger impression. 💪🙂"
    if score < 80:
        return "Almost there—polish a few more skills to shine even brighter! ✨"
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
Drop your Job Description and .docx/.pdf resume to see how well you match — then discover personalized improvements to make your resume sparkle.   
No cap, no fluff, just real talk for your job grind.
""")

st.subheader("Paste the full Job Description here to check your fit.")
job_desc = st.text_area("Paste Job Description", height=130)

st.subheader("Upload your .docx or .pdf resume")
uploaded_file = st.file_uploader("Select your .docx or .pdf file", type=["docx", "pdf"])

if job_desc and uploaded_file:
    if st.button("Check My Fit"):
        resume_text = extract_resume_text(uploaded_file)
        if not resume_text:
            st.error("Could not extract text from file. Please ensure the file is valid and not scanned non-selectable PDF image.")
        else:
            jd_skills = get_jd_skills(job_desc)
            role_fit, matched_skills = compute_fit_score(jd_skills, resume_text)
            missing_skills = [s for s in jd_skills if s not in matched_skills]

            st.markdown(f"""
            <div class="score-bar-container">
                <span class="score-label">Role Match Score:</span><br>
                <span style="font-size:2.3rem; color:#33ffe0; font-weight:700;">{role_fit}%</span><br>
                <span style="color:#bebee7; font-size:1.1rem;">{feedback_text(role_fit)}</span>
            </div>""", unsafe_allow_html=True)
            st.progress(role_fit / 100)

            matched_text = ', '.join(matched_skills) if matched_skills else "None detected this time. Don’t be discouraged — every pro starts somewhere! 💪🙂"
            st.markdown(f"<div class='skill-section'><b>✅ Skills Matched:</b> {matched_text}</div>", unsafe_allow_html=True)

            missing_text = ', '.join(missing_skills) if missing_skills else "All key skills matched! You’re looking solid for this role. 🌟"
            st.markdown(f"<div class='missing-section'><b>⚠️ Opportunities to Enhance:</b> {missing_text}</div>", unsafe_allow_html=True)

            st.subheader("Suggested Improvements")
            if missing_skills:
                st.info("Focus on these areas to shine brighter and land that interview! 🌟")
                for skill in missing_skills:
                    st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {create_suggestion(skill)}</div>", unsafe_allow_html=True)
            else:
                st.info("You’re all set! Keep your resume updated and tailored for other roles. 🚀")

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

else:
    st.info("Please paste the Job Description and upload your resume to get started.")
