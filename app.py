import streamlit as st
import difflib
import docx
from io import BytesIO

# ------------------------------
# Helper Functions
# ------------------------------

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def save_docx_with_updates(original_file, matched_skills, missing_skills, suggestions):
    doc = docx.Document(original_file)
    
    # Insert missing skills into Skills section if found
    for para in doc.paragraphs:
        if "SKILLS" in para.text.upper():
            run = para.add_run("\n" + ", ".join(missing_skills))
            run.bold = True
    
    # Add suggestions at relevant sections
    for para in doc.paragraphs:
        if "EXPERIENCE" in para.text.upper() or "PROJECT" in para.text.upper():
            for s in suggestions:
                para.add_run(f"\n• {s}")
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def analyze_resume(resume_text, jd_text):
    resume_words = set(resume_text.lower().split())
    jd_words = set(jd_text.lower().split())

    matched = list(resume_words & jd_words)
    missing = list(jd_words - resume_words)

    # Create simple suggestions from missing skills
    suggestions = [f"Add experience with {skill}" for skill in missing[:5]]

    # Simple score
    score = (len(matched) / (len(jd_words) + 1)) * 100

    return round(score, 1), matched, missing, suggestions

# ------------------------------
# Streamlit UI
# ------------------------------

st.set_page_config(page_title="AI Resume Optimizer", layout="wide")
st.title("📄 AI Resume Optimizer")

uploaded_file = st.file_uploader("Upload your Resume (.docx)", type=["docx"])
jd_input = st.text_area("Paste the Job Description here:")

if uploaded_file and jd_input:
    resume_text = extract_text_from_docx(uploaded_file)
    score, matched, missing, suggestions = analyze_resume(resume_text, jd_input)

    # Display results
    st.markdown(f"## 🔎 Role-fit Score: **{score}%**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### ✅ Matched Skills")
        if matched:
            st.success(", ".join(matched))
        else:
            st.info("No skills matched.")

    with col2:
        st.markdown("### ⚠️ Missing Skills")
        if missing:
            st.error(", ".join(missing))
        else:
            st.info("No missing skills detected.")

    with col3:
        st.markdown("### ✍️ Suggested Bullets")
        if suggestions:
            for s in suggestions:
                st.write(f"• {s}")
        else:
            st.info("No suggestions available.")

    # Generate updated resume
    if st.button("📥 Download Updated Resume"):
        updated_doc = save_docx_with_updates(uploaded_file, matched, missing, suggestions)
        st.download_button(
            label="Download Resume (.docx)",
            data=updated_doc,
            file_name="Updated_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
