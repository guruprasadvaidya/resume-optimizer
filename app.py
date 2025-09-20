# app.py — Updated Resume Optimizer (JD-first, Process button, nicer UI, semi-manual updates)
import streamlit as st
from docx import Document
from io import BytesIO
import re
import base64

st.set_page_config(page_title="AI Resume Optimizer", layout="wide", page_icon="📄")

# ---------- Skill bank (canonical + synonyms). Add names you want supported ----------
CANONICAL_SKILLS = [
    "python","sql","pytorch","tensorflow","scikit-learn","pandas","numpy","matplotlib",
    "streamlit","fastapi","docker","kubernetes","react","node.js","nodejs","express.js",
    "mongodb","mysql","git","nlp","natural language processing","computer vision",
    "ocr","onnx","triton","huggingface","transformers","model deployment","data infrastructure",
    "etl","data engineering","prompt engineering","langchain","rag","rest api","api",
    "aws","gcp","google cloud","databricks","streamlit cloud","linux"
]
SYNONYMS = {
    "node.js": ["nodejs","node js"],
    "nlp": ["natural language processing"],
    "rest api": ["restapi","api","rest"],
    "react": ["reactjs","react.js"],
    "google cloud": ["gcp"],
    "model deployment": ["deployment","deploy"],
    "computer vision": ["cv","vision"]
}
# ensure longer multi-word skills are matched first
ALL_SKILLS = sorted(CANONICAL_SKILLS, key=lambda s: -len(s))


# ---------- Helpers ----------
def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())

def find_skills_in_text(text: str):
    """Return set of canonical skill names found in text (case-insensitive)."""
    found = set()
    if not text:
        return found
    t = text.lower()
    for skill in ALL_SKILLS:
        # consider skill + synonyms
        candidates = [skill] + SYNONYMS.get(skill, [])
        for cand in candidates:
            # word-boundary match for multiword phrases
            pattern = r'\b' + re.escape(cand.lower()) + r'\b'
            if re.search(pattern, t):
                found.add(skill)
                break
    return found

def extract_text_from_docx_file(file_obj):
    doc = Document(file_obj)
    texts = [p.text for p in doc.paragraphs]
    return "\n".join(texts)

def create_suggestion_for_skill(skill):
    """Gentle, honest suggestion templates (not fake claims)."""
    return f"Highlight experience with {skill} — e.g., 'Worked with {skill} in project X' or add a short project/example."

def insert_skills_into_docx(doc_file, skills_to_add, suggestions_to_add):
    """
    doc_file: file-like or path
    skills_to_add: list of canonical skill names to insert into existing SKILLS paragraph (inline)
    suggestions_to_add: list of suggestion strings (will be appended in a 'Suggested additions' section)
    Returns BytesIO of updated docx.
    """
    doc = Document(doc_file)
    skills_block_found = False

    # try to find paragraph that looks like a skills header or skills list
    for para in doc.paragraphs:
        if re.search(r'\bskills\b', para.text, flags=re.IGNORECASE):
            # append new skills inline separated by " | "
            append_text = " | " + " | ".join(skills_to_add) if skills_to_add else ""
            # keep styling by adding a run (does not replace existing formatting)
            run = para.add_run(append_text)
            run.bold = True
            skills_block_found = True
            break

    if not skills_block_found and skills_to_add:
        # fallback: add a new 'Skills' heading at the end and add skills
        doc.add_paragraph("\nSKILLS", style='Heading 2')
        p = doc.add_paragraph(" | ".join(skills_to_add))
        p.runs[0].bold = True

    # Append a "Suggested additions" block so we don't ruin other sections
    if suggestions_to_add:
        doc.add_paragraph("\nSuggested additions:", style='Heading 2')
        for s in suggestions_to_add:
            p = doc.add_paragraph()
            p.add_run("• " + s)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ---------- CSS (light) ----------
st.markdown("""
<style>
.badge {
  display:inline-block;
  padding:6px 10px;
  margin:4px 6px 4px 0;
  border-radius:12px;
  font-weight:600;
}
.badge-green { background:#e6ffef; color:#0b6b39; border:1px solid #0b6b39; }
.badge-red { background:#fff0f0; color:#8b0000; border:1px solid #b30000; }
.card { background:#fffdf5; padding:12px; border-radius:10px; border:1px solid #f0e2b6; margin-bottom:10px; }
.small-muted { color:#6b6b6b; font-size:13px; }
</style>
""", unsafe_allow_html=True)


# ---------- UI Layout ----------
st.title("📄 AI Resume Optimizer")
st.write("Paste the Job Description first, then upload your resume. Click **Process** to analyze. Select suggestions to include in the updated resume.")

# JD first (as requested)
jd_input = st.text_area("1) Paste Job Description (any format):", height=220, placeholder="Paste a job description — paragraphs, bullets, anything.")
st.write("")  # spacing

col1, col2 = st.columns([1,1])
with col1:
    uploaded_file = st.file_uploader("2) Upload Resume (.docx)", type=["docx"])
with col2:
    st.write("UI Tip")
    st.info("Order: JD → Resume → Process. After process: select suggestions, confirm then apply.")

# Process button (better UX than Ctrl+Enter)
if st.button("Process"):
    if not jd_input or not uploaded_file:
        st.error("Please provide both Job Description and Resume (.docx).")
    else:
        # extract texts
        jd_text = normalize_text(jd_input)
        resume_text = normalize_text(extract_text_from_docx_file(uploaded_file))

        # extract skills robustly
        jd_skills = find_skills_in_text(jd_text)
        resume_skills = find_skills_in_text(resume_text)

        matched = sorted(list(jd_skills & resume_skills))
        missing = sorted(list(jd_skills - resume_skills))

        # role-fit (avoid division by zero)
        role_fit = round((len(matched) / (len(jd_skills) if jd_skills else 1)) * 100, 1)

        # display summary
        st.markdown(f"### 🔎 Role-fit score: **{role_fit}%**")
        st.markdown("<div class='small-muted'>Breakdown: matched / required skills</div>", unsafe_allow_html=True)

        # badges for matched
        st.write("**✅ Matched skills:**")
        if matched:
            for s in matched:
                st.markdown(f"<span class='badge badge-green'>{s}</span>", unsafe_allow_html=True)
        else:
            st.info("No matched skills found (expected for very different JD).")

        st.write("**⚠️ Missing skills (from JD):**")
        if missing:
            for s in missing:
                st.markdown(f"<span class='badge badge-red'>{s}</span>", unsafe_allow_html=True)
        else:
            st.info("No missing skills found.")

        # suggestions cards with checkboxes (semi-manual)
        st.write("**✍️ Suggested resume improvements**")
        suggestion_items = []
        for i, skill in enumerate(missing):
            suggestion_text = create_suggestion_for_skill(skill)
            # show as card with checkbox
            st.markdown(f"<div class='card'><b>{skill}</b><div class='small-muted' style='margin-top:6px'>{suggestion_text}</div></div>", unsafe_allow_html=True)
            selected = st.checkbox(f"Add suggestion for '{skill}'", key=f"sel_{i}")
            if selected:
                # allow choice: add to Skills (inline) or add a bullet in Suggested additions
                choice = st.radio(f"Where to add '{skill}'?", ("Add to Skills", "Add as bullet"), key=f"where_{i}")
                suggestion_items.append((skill, suggestion_text, choice))

        if not missing:
            st.success("No suggestions needed — your resume already includes the JD skills!")

        # confirmation + apply
        if suggestion_items:
            st.write("")
            confirm = st.checkbox("I confirm I want to add the selected items to my resume (semi-manual, you'll get updated file).")
            if confirm:
                if st.button("Apply selected to resume and download updated .docx"):
                    # Re-open uploaded_file (stream)
                    uploaded_file.seek(0)
                    skills_to_add = [s for s, _, choice in suggestion_items if choice == "Add to Skills"]
                    bullets_to_add = [template for _, template, choice in suggestion_items if choice == "Add as bullet"]

                    updated_buf = insert_skills_into_docx(uploaded_file, skills_to_add, bullets_to_add)

                    st.success("Updated resume ready — file preserves original formatting as much as possible.")
                    st.download_button(
                        label="⬇️ Download updated resume (.docx)",
                        data=updated_buf.getvalue(),
                        file_name="resume_updated.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
