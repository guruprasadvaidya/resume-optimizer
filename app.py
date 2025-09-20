import streamlit as st
from docx import Document
import difflib
import re
import os
import tempfile

st.set_page_config(page_title="AI Resume Optimizer", layout="wide", page_icon="📝")

# --- Function to extract text from DOCX ---
def extract_text_from_docx(file):
    doc = Document(file)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return "\n".join(fullText)

# --- Function to calculate matched & missing skills ---
def get_skills_match(resume_text, jd_text):
    resume_words = set(re.findall(r'\w+', resume_text.lower()))
    jd_words = set(re.findall(r'\w+', jd_text.lower()))
    
    matched_skills = list(resume_words & jd_words)
    missing_skills = list(jd_words - resume_words)
    
    return matched_skills, missing_skills

# --- Function to generate suggested bullets ---
def generate_suggestions(missing_skills):
    suggestions = [f"Consider highlighting {skill}" for skill in missing_skills]
    return suggestions

# --- Function to update DOCX resume ---
def update_resume(file, selected_suggestions):
    doc = Document(file)
    # Find Skills section and update
    skills_updated = False
    for para in doc.paragraphs:
        if "Skills" in para.text or "SKILLS" in para.text:
            if not skills_updated:
                for skill in selected_suggestions:
                    para.add_run(f", {skill}")
                skills_updated = True
    # If no skills section, add at end
    if not skills_updated:
        doc.add_paragraph("Skills: " + ", ".join(selected_suggestions))
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp_file.name)
    return tmp_file.name

# --- UI Layout ---
st.title("📝 AI Resume Optimizer")
st.markdown("Optimize your resume according to Job Description (JD) automatically!")

# JD Input first
jd_text = st.text_area("Paste Job Description here", height=200)

# Resume Upload second
uploaded_file = st.file_uploader("Upload your resume (.docx)", type=["docx"])

# Process Button
if st.button("Process") and uploaded_file and jd_text:
    resume_text = extract_text_from_docx(uploaded_file)
    
    # Skills matching
    matched_skills, missing_skills = get_skills_match(resume_text, jd_text)
    
    # Role fit score (simple ratio)
    role_fit = round(len(matched_skills) / (len(matched_skills) + len(missing_skills) + 1e-5) * 100, 2)
    
    # --- Display Results ---
    col1, col2, col3 = st.columns([1,1,1])
    
    with col1:
        st.markdown(f"<div style='background-color:#33ffe0;padding:10px;border-radius:8px'>"
                    f"<b>✅ Matched Skills:</b><br>{', '.join(matched_skills)}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background-color:#ff4d4d;padding:10px;border-radius:8px'>"
                    f"<b>⚠️ Missing Skills:</b><br>{', '.join(missing_skills)}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background-color:#ffe633;padding:10px;border-radius:8px'>"
                    f"<b>Role Fit Score:</b> {role_fit}%</div>", unsafe_allow_html=True)
        st.progress(role_fit / 100)  # Corrected here
    
    # Suggestions Section
    suggestions = generate_suggestions(missing_skills)
    st.markdown("<h4 style='color:#33ccff'>💡 Suggested Improvements:</h4>", unsafe_allow_html=True)
    selected_suggestions = st.multiselect("Select suggestions to add to your resume", suggestions)
    
    # Button to update resume
    if selected_suggestions:
        if st.button("Update Resume with selected suggestions"):
            updated_resume_path = update_resume(uploaded_file, selected_suggestions)
            with open(updated_resume_path, "rb") as f:
                st.download_button(
                    label="Download Updated Resume",
                    data=f,
                    file_name="Updated_Resume.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            st.success("✅ Resume updated successfully!")
