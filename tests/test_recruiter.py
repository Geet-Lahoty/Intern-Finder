import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from database.connection import run_query
from database.queries import (
    get_recruiter_internships,
    get_internship_applicants,
    update_application_status,
)

st.title("Recruiter Query Testing")

# Recruiter selection
recruiters = run_query(
    """
    SELECT user_id, full_name, email
    FROM users
    WHERE role = 'recruiter'
      AND is_active = TRUE
    ORDER BY full_name
    """
)

if recruiters.empty:
    st.warning("No recruiters found. Run the seed script first.")
    st.stop()

recruiter_options = {
    f"{r.full_name} ({r.email})": int(r.user_id)
    for r in recruiters.itertuples()
}

selected_recruiter = st.selectbox(
    "Select recruiter",
    list(recruiter_options.keys()),
)

recruiter_id = recruiter_options[selected_recruiter]

# Section 1: Recruiter internships
st.divider()
st.subheader("1. My Internships")

try:
    internships = get_recruiter_internships(recruiter_id)

    if internships.empty:
        st.info("This recruiter has not posted any internships.")
    else:
        st.dataframe(
            internships,
            width="stretch",
            hide_index=True,
        )

        st.metric("Total internships", len(internships))

except Exception as e:
    st.error("Failed to load internships.")
    st.exception(e)

# Section 2: View applicants
st.divider()
st.subheader("2. View Applicants")

if not internships.empty:
    internship_options = {
        f"{r.title} (ID: {r.internship_id})": int(r.internship_id)
        for r in internships.itertuples()
    }

    selected_internship = st.selectbox(
        "Choose internship",
        list(internship_options.keys()),
    )

    internship_id = internship_options[selected_internship]

    if st.button("Load Applicants"):
        try:
            applicants = get_internship_applicants(
                internship_id,
                recruiter_id,
            )

            if applicants.empty:
                st.info("No applicants found for this internship.")
            else:
                st.dataframe(
                    applicants,
                    width="stretch",
                    hide_index=True,
                )
        except Exception as e:
            st.error("Failed to load applicants.")
            st.exception(e)

    # Section 3: Update status
    st.divider()
    st.subheader("3. Update Application Status")

    try:
        applicants = get_internship_applicants(
            internship_id,
            recruiter_id,
        )

        if applicants.empty:
            st.info("No applications available to update.")
        else:
            applicant_options = {
                f"{r.full_name} — Application #{r.application_id} "
                f"({r.application_status})": int(r.application_id)
                for r in applicants.itertuples()
            }

            with st.form("update_status_form"):
                selected_application = st.selectbox(
                    "Select application",
                    list(applicant_options.keys()),
                )

                new_status = st.selectbox(
                    "New status",
                    [
                        "pending",
                        "shortlisted",
                        "rejected",
                        "accepted",
                        "withdrawn",
                    ],
                )

                confirm = st.checkbox(
                    "Confirm this status change"
                )

                submitted = st.form_submit_button("Update Status")

                if submitted:
                    if not confirm:
                        st.warning("Please confirm the status change.")
                    else:
                        try:
                            updated_id = update_application_status(
                                applicant_options[selected_application],
                                recruiter_id,
                                new_status,
                            )

                            if updated_id is not None:
                                st.success(
                                    f"Application #{updated_id} updated to "
                                    f"'{new_status}'."
                                )
                                st.rerun()
                            else:
                                st.warning(
                                    "No change was made. The application may already "
                                    "have this status or may not belong to this recruiter."
                                )

                        except Exception as e:
                            st.error("Failed to update application status.")
                            st.exception(e)

    except Exception as e:
        st.error("Failed to update application status.")
        st.exception(e)
