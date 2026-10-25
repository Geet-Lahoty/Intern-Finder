import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from database.connection import run_query
from database.queries import (
    get_student_profile,
    update_student_profile,
)

st.title("Student Profile Testing")

students = run_query(
    """
    SELECT user_id, full_name, email
    FROM users
    WHERE role = 'student'
      AND is_active = TRUE
    ORDER BY full_name
    """
)

if students.empty:
    st.warning("No students found. Run the seed script first.")
    st.stop()

student_options = {
    f"{row.full_name} ({row.email})": int(row.user_id)
    for row in students.itertuples()
}

selected_student = st.selectbox(
    "Choose a demo student",
    list(student_options.keys()),
)

student_id = student_options[selected_student]
profile = get_student_profile(student_id)

if profile.empty:
    st.error("Student profile not found.")
    st.stop()

student = profile.iloc[0]

st.divider()
st.subheader("Current Profile")

col1, col2 = st.columns(2)

with col1:
    st.write("**Name:**", student["full_name"])
    st.write("**Email:**", student["email"])
    st.write("**University:**", student["university"] or "Not provided")
    st.write("**Degree:**", student["degree"] or "Not provided")

with col2:
    st.write("**Graduation year:**", student["graduation_year"] or "Not provided")
    st.write("**CGPA:**", student["cgpa"] if student["cgpa"] is not None else "Not provided")
    st.write("**City:**", student["city"] or "Not provided")
    st.write("**Account active:**", student["is_active"])

st.divider()
st.subheader("Edit Student Profile")

with st.form("edit_profile"):
    university = st.text_input(
        "University",
        value=student["university"] or "",
    )

    degree = st.text_input(
        "Degree",
        value=student["degree"] or "",
    )

    graduation_year = st.number_input(
        "Graduation year (0 = not provided)",
        min_value=0,
        max_value=2100,
        value=int(student["graduation_year"] or 0),
        step=1,
    )

    cgpa_value = float(student["cgpa"]) if student["cgpa"] is not None else 0.0

    cgpa = st.number_input(
        "CGPA (0 = not provided)",
        min_value=0.0,
        max_value=10.0,
        value=cgpa_value,
        step=0.1,
    )

    city = st.text_input("City", value=student["city"] or "")
    phone = st.text_input("Phone", value=student["phone"] or "")
    github_url = st.text_input("GitHub URL", value=student["github_url"] or "")
    linkedin_url = st.text_input("LinkedIn URL", value=student["linkedin_url"] or "")
    portfolio_url = st.text_input("Portfolio URL", value=student["portfolio_url"] or "")
    resume_url = st.text_input("Resume URL", value=student["resume_url"] or "")
    bio = st.text_area("Bio", value=student["bio"] or "")

    submitted = st.form_submit_button(
        "Save Profile",
        type="primary",
    )

if submitted:
    try:
        # Convert the zero placeholders into SQL NULL values.
        saved_id = update_student_profile(
            student_id=student_id,
            university=university,
            degree=degree,
            graduation_year=graduation_year or None,
            cgpa=cgpa or None,
            city=city,
            phone=phone,
            github_url=github_url,
            linkedin_url=linkedin_url,
            portfolio_url=portfolio_url,
            resume_url=resume_url,
            bio=bio,
        )

        if saved_id is not None:
            st.success("Student profile updated successfully!")
            st.rerun()
        else:
            st.error("Profile was not updated.")

    except Exception as e:
        st.error("Failed to update profile.")
        st.exception(e)
