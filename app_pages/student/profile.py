import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_student_profile,
    update_student_profile,
)


def _get_text(value):
    """Convert database values into safe strings for Streamlit inputs."""
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _get_number(value):
    """Convert an optional database number into a string."""
    if value is None or pd.isna(value):
        return ""
    return str(value)


def render():
    # Protect the page and identify the logged-in student.
    user = require_role("student")
    student_id = user["user_id"]

    st.title("👤 My Profile")
    st.caption("Keep your academic details and portfolio up to date.")

    # Load the student's profile.
    try:
        profile = get_student_profile(student_id)
    except Exception as e:
        st.error("Unable to load your profile.")
        st.exception(e)
        return

    if profile is None or profile.empty:
        st.error(
            "Your student profile was not found. "
            "Please contact the administrator."
        )
        return

    student = profile.iloc[0]

    # Account information is displayed but cannot be edited here.
    st.subheader("Account Information")

    col1, col2 = st.columns(2)

    with col1:
        st.text_input(
            "Full Name",
            value=_get_text(student["full_name"]),
            disabled=True,
        )

    with col2:
        st.text_input(
            "Email Address",
            value=_get_text(student["email"]),
            disabled=True,
        )

    st.info(
        "Your name and email are account details. "
        "They cannot be changed from this page."
    )

    st.markdown("---")

    # Profile editing form.
    st.subheader("Academic Information")

    with st.form("student_profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            university = st.text_input(
                "University / College",
                value=_get_text(student["university"]),
                placeholder="e.g. Gujarat University",
            )

            degree = st.text_input(
                "Degree / Course",
                value=_get_text(student["degree"]),
                placeholder="e.g. B.Tech Computer Engineering",
            )

            graduation_year = st.text_input(
                "Graduation Year",
                value=_get_number(student["graduation_year"]),
                placeholder="e.g. 2027",
                help="Leave blank if not applicable.",
            )

        with col2:
            cgpa = st.text_input(
                "CGPA",
                value=_get_number(student["cgpa"]),
                placeholder="e.g. 8.5",
                help="Enter your CGPA as a number.",
            )

            city = st.text_input(
                "City",
                value=_get_text(student["city"]),
                placeholder="e.g. Ahmedabad",
            )

            phone = st.text_input(
                "Phone Number",
                value=_get_text(student["phone"]),
                placeholder="Your contact number",
            )

        st.markdown("---")
        st.subheader("Professional Links")

        resume_url = st.text_input(
            "Resume URL",
            value=_get_text(student["resume_url"]),
            placeholder="https://...",
        )

        col1, col2 = st.columns(2)

        with col1:
            github_url = st.text_input(
                "GitHub URL",
                value=_get_text(student["github_url"]),
                placeholder="https://github.com/username",
            )

        with col2:
            linkedin_url = st.text_input(
                "LinkedIn URL",
                value=_get_text(student["linkedin_url"]),
                placeholder="https://linkedin.com/in/username",
            )

        portfolio_url = st.text_input(
            "Portfolio URL",
            value=_get_text(student["portfolio_url"]),
            placeholder="https://...",
        )

        st.markdown("---")
        st.subheader("About Me")

        bio = st.text_area(
            "Professional Bio",
            value=_get_text(student["bio"]),
            placeholder=(
                "Tell recruiters about your interests, "
                "experience, and career goals..."
            ),
            height=150,
        )

        submitted = st.form_submit_button(
            "💾 Save Profile",
            width="stretch",
        )

    # Save only after the student submits the form.
    if submitted:
        # Validate and convert optional numeric values.
        graduation_year_value = None
        cgpa_value = None

        if graduation_year.strip():
            try:
                graduation_year_value = int(graduation_year.strip())
            except ValueError:
                st.error("Graduation year must be a whole number.")
                return

            if not 1900 <= graduation_year_value <= 2100:
                st.error("Enter a valid graduation year.")
                return

        if cgpa.strip():
            try:
                cgpa_value = float(cgpa.strip())
            except ValueError:
                st.error("CGPA must be a valid number.")
                return

            if cgpa_value < 0:
                st.error("CGPA cannot be negative.")
                return

        try:
            updated_student_id = update_student_profile(
                student_id=student_id,
                university=university,
                degree=degree,
                graduation_year=graduation_year_value,
                cgpa=cgpa_value,
                city=city,
                phone=phone,
                github_url=github_url,
                linkedin_url=linkedin_url,
                portfolio_url=portfolio_url,
                resume_url=resume_url,
                bio=bio,
            )

            if updated_student_id is not None:
                st.success("✅ Your profile has been updated!")
                st.rerun()
            else:
                st.error(
                    "No profile was updated. "
                    "Please check that your student profile exists."
                )

        except Exception as e:
            st.error("Unable to save your profile.")
            st.exception(e)