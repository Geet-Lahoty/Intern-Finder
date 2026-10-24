import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from database.connection import run_query
from database.queries import (
    apply_for_internship,
    get_student_applications,
    get_application_history,
)

st.title("Application Query Testing")

students = run_query(
    """
    SELECT user_id, full_name, email
    FROM users
    WHERE role = 'student'
    ORDER BY full_name
    """
)

if students.empty:
    st.warning("No demo students found. Run the seed script first.")
    st.stop()

student_options = {
    f"{row.full_name} ({row.email})": int(row.user_id)
    for row in students.itertuples()
}

selected_student = st.selectbox(
    "Choose a student",
    list(student_options.keys()),
)

student_id = student_options[selected_student]

st.divider()
st.subheader("1. Existing Applications")

if st.button("Load Applications"):
    applications = get_student_applications(student_id)

    if applications.empty:
        st.info("This student has no applications.")
    else:
        st.dataframe(
            applications,
            width="stretch",
            hide_index=True,
        )

st.divider()
st.subheader("2. Apply for an Internship")

internships = run_query(
    """
    SELECT
        i.internship_id,
        i.title,
        c.name AS company_name,
        i.stipend_monthly,
        i.location
    FROM internships AS i
    JOIN companies AS c ON i.company_id = c.company_id
    WHERE i.status = 'open'
      AND (i.deadline IS NULL OR i.deadline >= CURRENT_DATE)
    ORDER BY i.title
    """
)

if internships.empty:
    st.info("No open internships are available.")
else:
    internship_options = {
        f"{row.title} — {row.company_name}": int(row.internship_id)
        for row in internships.itertuples()
    }

    with st.form("apply_form"):
        selected_internship = st.selectbox(
            "Internship",
            list(internship_options.keys()),
        )

        cover_note = st.text_area(
            "Cover note",
            placeholder="Why are you interested in this internship?",
        )

        submit = st.form_submit_button("Submit Application")

    if submit:
        try:
            application_id = apply_for_internship(
                student_id,
                internship_options[selected_internship],
                cover_note,
            )

            if application_id is not None:
                st.success(
                    f"Application submitted! ID: {application_id}"
                )
            else:
                st.warning(
                    "Application was not created. You may have already "
                    "applied, or the internship may no longer be available."
                )

        except Exception as e:
            st.error("Application failed.")
            st.exception(e)

st.divider()
st.subheader("3. Application Status History")

application_id_input = st.number_input(
    "Application ID",
    min_value=1,
    step=1,
    value=1,
)

if st.button("Load Status History"):
    history = get_application_history(int(application_id_input))

    if history.empty:
        st.info("No status history records found for this application.")
    else:
        st.dataframe(
            history,
            width="stretch",
            hide_index=True,
        )
