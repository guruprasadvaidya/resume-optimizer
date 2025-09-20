import streamlit as st
from docx import Document
from io import BytesIO
import difflib
import re

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📝", layout="wide")

# ----- MODERN DARK + ENGAGING COPY -----
st.markdown("""
    <style>
        html, body, [class*="css"]  { background-color: #15161b !important; color: #ededed !important; }
        .score-bar-container { background: #23232b; border-radius:15px; padding:20px 30px;margin-bottom:15px;text-align:center;}
        .score-label { color:#7de291; font-weight:600; font-size:1.4rem; }
        .stProgress>div>div>div>div { background-color: #348e75; }
        .skill-section { background: #233547; border-radius: 10px; padding: 10px 18px; margin-bottom: 8px; color:#45bcff;font-size:1rem;}
        .missing-section { background: #3e1a24; border-radius: 10px; padding: 10px 18px; margin-bottom: 8px; color:#ff9494;font-size:1rem;}
        .suggest-box { background: #25282e; border-radius: 10px; padding: 16px 22px; margin-bottom: 12px; color: #e2e2e2;font-size:1.04rem;box-shadow:0 2px 9px #1c202680;}
        .stButton>button {
            background-color: #3976fa !important; color: #fff !important;
            border-radius: 6px !important; font-weight: 600;
            margin-top:10px; font-size: 1.09rem; padding:7px 18px 7px 18px;
        }
    </style>
""", unsafe_allow_html=True)

# --------- GENZ-PROFESSIONAL COPY ----------
st.title("AI Resume Optimizer")
st.markdown("""
Feeling “99 Problems But My Resume Ain’t One”?  
Paste the JD. Drop your doc. Let AI roast your skills, serve tailor-made fixes, and (finally) upgrade that hustle.  
_Level up. Get interviews. Don’t let a boring resume block your vibe._
""")

CANONICAL_SKILLS = [
    "python","pytorch","tensorflow","scikit-learn","pandas","numpy","sql","nlp","computer vision","ocr","transformers","huggingface","onnx","triton","docker","streamlit","fastapi","data infrastructure","model deployment"
]
SYNONYMS = {
    "pytorch":["torch"], "nlp":["natural language processing"], "computer vision":["cv","vision"], "transformers":["hugging face"], "onnx":["onnxruntime"], "ocr":["tesseract","optical character recognition"], "model deployment":["deploy","deployment"], "data infrastructure":["data pipeline","etl"]
}
EXAMPLE_TASKS = {
    "pytorch":"trained a CNN on real images, looked smart on GitHub.",
    "nlp":"built text-class pipelines—spoiler: even bots need to read.",
    "computer vision":"taught a computer to see like a human (almost).",
    "ocr":"converted messy scans into copy-paste flex.",
    "model deployment":"deployed models as APIs. Résumé status: ‘production-ready’.",
    "data infrastructure":"looked at a messy CSV—and didn’t panic."
}

def normalize(s): return re.sub(r'[^a-z0-9]','',s.lower())
def match_skill(skill, text):
    text_norm = normalize(text)
    if normalize(skill) in text_norm: return True
    if any(normalize(syn) in text_norm for syn in SYNONYMS.get(skill,[])): return True
    return False
def create_suggestion(skill):
    task = EXAMPLE_TASKS.get(skill.lower())
    if task: return f"Implemented {skill}: {task}"
    return f"Worked with {skill}: drop your best project/app example."
def get_jd_skills(jd):
    norm_jd = normalize(jd)
    return [s for s in CANONICAL_SKILLS if normalize(s) in norm_jd or any(normalize(syn) in norm_jd for syn in SYNONYMS.get(s, []))]
def improved_role_fit_score(jd_skills, resume_text):
    score, matched = 0, []
    for s in jd_skills:
        matches = [s] + SYNONYMS.get(s, [])
        found = False
        for target in matches:
            if normalize(target) in normalize(resume_text): found = True; break
            for word in resume_text.split():
                if difflib.SequenceMatcher(None, normalize(word), normalize(target)).ratio() > 0.74:
                    found = True; break
            if found: break
        if found: matched.append(s); score += 1
    denom = max(len(jd_skills), 1)
    return round(100. * score / denom, 1), matched
def find_skills_section(doc):
    for p in doc.paragraphs:
        if "SKILLS" in p.text.upper(): return p
    return None
def insert_to_resume(docx_file, skills_to_add, bullets_to_add):
    buf_in = BytesIO(docx_file.getvalue())
    doc = Document(buf_in)
    # Add skills to skill section (format safe)
    p_skill = find_skills_section(doc)
    if p_skill and skills_to_add:
        runs = p_skill.runs
        text = p_skill.text.strip()
        if "|" in text: segments = [seg.strip() for seg in text.split("|")]
        elif "," in text: segments = [seg.strip() for seg in text.split(",")]
        else: segments = text.split()
        current_set = set([normalize(seg) for seg in segments])
        for s in skills_to_add:
            if normalize(s) not in current_set: segments.append(s)
        full_line = " | ".join(segments)
        for run in runs: run.text = ""
        p_skill.add_run(full_line)
    # Add new bullets at the end in matching style
    if bullets_to_add:
        doc.add_paragraph("")
        header = doc.add_paragraph("--- Added Skills / Projects ---")
        for b in bullets_to_add:
            doc.add_paragraph(b, style="List Bullet")
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ----------- MAIN APP WORKFLOW ------------------
st.subheader("Paste the Job Description")
job_desc = st.text_area("_Ctrl+V the target JD and find out where you shine—and where your skills ghosted you._", height=110, placeholder="Paste the JD here. Don’t be shy.")

st.subheader("Upload your Résumé (.docx)")
file_up = st.file_uploader("Pick your .docx file. We pinky swear not to judge… much.", type=["docx"])

if job_desc and file_up:
    if st.button("Analyze Me 🔥"):
        doc = Document(file_up)
        resume_text = "\n".join([p.text for p in doc.paragraphs])
        jd_skills = get_jd_skills(job_desc)
        role_fit, matched_skills = improved_role_fit_score(jd_skills, resume_text)
        missing_skills = [s for s in jd_skills if s not in matched_skills]

        st.markdown(f"""<div class="score-bar-container">
            <span class="score-label">Role-Fit Score:</span>
            <br>
            <span style="font-size:2.3rem;color:#45bcff;font-weight:700">{role_fit}%</span>
            {f'<br><span style=\"color:#e4977a;font-size:1.1rem\">{get_score_comment(role_fit)}</span>' if role_fit < 90 else '<br><span style="color:#70ea98;font-size:1.1rem">Yaass! You’re interview-ready.</span>'}
            </div>""", unsafe_allow_html=True)

        st.progress(role_fit)

        st.markdown(f"<div class='skill-section'><b>✅ Matched Skills:</b> {', '.join(matched_skills) if matched_skills else 'None (wow).'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='missing-section'><b>⚠️ Missing Skills:</b> {', '.join(missing_skills) if missing_skills else 'Nada, you’re golden!'}</div>", unsafe_allow_html=True)

        st.subheader("Suggested Glow-Ups 🧠")
        st.info("Check the suggestions you vibe with, add them with one click, and download your Level–2 resume—even HR will be impressed!")

        selected_for_resume = []
        for i, skill in enumerate(missing_skills):
            suggest = create_suggestion(skill)
            st.markdown(f"<div class='suggest-box'><b>{skill}:</b> {suggest}</div>", unsafe_allow_html=True)
            sel = st.checkbox(f"Add `{skill}` to my resume", key=f"sel_{i}")
            if sel:
                opt = st.radio(f"Where should I sneak `{skill}` in?", ["Skills Section (flex for scanners)", "Bullet Points (show real work)"], key=f"opt_{i}")
                selected_for_resume.append((skill, suggest, opt))

        if selected_for_resume:
            if st.button("Update My Resume 🚀"):
                with st.spinner("Injecting awesomeness..."):
                    buf_out = insert_to_resume(
                        file_up,
                        [s for s, _, pos in selected_for_resume if pos.startswith("Skills")],
                        [desc for _, desc, pos in selected_for_resume if pos.startswith("Bullet")]
                    )
                    st.success("Prepared your glow-up! Download, flex, repeat.")
                    st.download_button(
                        "📥 Download Updated Résumé",
                        buf_out.getvalue(),
                        file_name="resume_UPDATED.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
def get_score_comment(score):
    if score < 40: return "Application needs some serious TLC 🏗️"
    if score < 65: return "Good start; recruiters will spot some gaps."
    if score < 80: return "Solid—but let's tune up those missing skills."
    return "Nearly there! One or two tweaks for max results."
