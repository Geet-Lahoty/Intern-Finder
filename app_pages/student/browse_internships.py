import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_all_internships,
    search_internships,
    apply_for_internship
)


def format_stipend(value):
    """Format a monthly stipend for display."""
    if value is None or pd.isna(value):
        return "Not specified"

    return f"₹{value:,.0f}/month"


def format_deadline(value):
    """Format an internship application deadline."""
    if value is None or pd.isna(value):
        return "Not specified"

    try:
        return pd.to_datetime(value).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value)


def render():
    # Only logged-in students can browse internships.
    require_role("student")

    st.title("💼 Browse Internships")
    st.caption(
        "Discover opportunities, explore companies, "
        "and find your next internship."
    )

    # Search and filter controls.
    st.subheader("🔍 Find Your Internship")

    with st.form("internship_search_form"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input(
                "Internship Title",
                placeholder="e.g. Python Developer",
            )

            location = st.text_input(
                "Location",
                placeholder="e.g. Ahmedabad",
            )

        with col2:
            work_mode = st.selectbox(
                "Work Mode",
                options=[
                    "All",
                    "Remote",
                    "Hybrid",
                    "On-site",
                ],
            )

            min_stipend = st.number_input(
                "Minimum Monthly Stipend (₹)",
                min_value=0,
                value=0,
                step=1000,
            )

        search_clicked = st.form_submit_button(
            "🔎 Search Internships",
            width="stretch",
        )

    # Retrieve internships using existing database queries.
    try:
        if search_clicked:
            internships = search_internships(
                title=title,
                location=location,
                min_stipend=(
                    min_stipend if min_stipend > 0 else None
                ),
                work_mode=(
                    work_mode.lower()
                    if work_mode != "All"
                    else ""
                ),
            )
        else:
            internships = get_all_internships()

    except Exception as e:
        st.error("Unable to load internships.")
        st.exception(e)
        return

    if internships is None or internships.empty:
        st.info(
            "No internships match your search. "
            "Try changing your filters."
        )

        if search_clicked:
            if st.button("Clear Search"):
                st.rerun()

        return

    # Results summary.
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Available Opportunities")

    with col2:
        st.metric("Internships Found", len(internships))

    st.caption("Showing currently open internships.")

    # Display each internship as a card.
    for _, internship in internships.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {internship['title']}")

                st.markdown(
                    f"**🏢 {internship['company_name']}**"
                )

                description = internship.get("description")

                if description is not None and not pd.isna(description):
                    description = str(description).strip()

                    if description:
                        if len(description) > 300:
                            description = description[:300].rstrip() + "..."

                        st.write(description)

            with col2:
                st.markdown(
                    f"### {format_stipend(internship.get('stipend_monthly'))}"
                )

                st.caption(
                    f"📍 {internship.get('location') or 'Not specified'}"
                )

                mode = internship.get("work_mode")

                if mode is not None and not pd.isna(mode):
                    st.caption(f"🏠 {str(mode).replace('_', ' ').title()}")

            st.markdown("---")

            col1, col2, col3 = st.columns(3)

            with col1:
                duration = internship.get("duration_months")

                if duration is None or pd.isna(duration):
                    st.caption("⏳ Duration: Not specified")
                else:
                    st.caption(f"⏳ Duration: {duration} months")

            with col2:
                openings = internship.get("openings")

                if openings is None or pd.isna(openings):
                    st.caption("👥 Openings: Not specified")
                else:
                    st.caption(f"👥 Openings: {openings}")

            with col3:
                deadline = format_deadline(
                    internship.get("deadline")
                )

                st.caption(f"📅 Deadline: {deadline}")
                
                # Application form for this internship.
            internship_id = int(internship["internship_id"])

            with st.expander("📝 Apply for this Internship"):
                st.write(
                    f"You're applying for **{internship['title']}** "
                    f"at **{internship['company_name']}**."
                )

                with st.form(
                    key=f"application_form_{internship_id}"
                ):
                    cover_note = st.text_area(
                        "Cover Note (Optional)",
                        placeholder=(
                            "Introduce yourself and explain why "
                            "you're interested in this internship..."
                        ),
                        max_chars=2000,
                    )

                    submitted = st.form_submit_button(
                        "Submit Application",
                        width="stretch",
                    )

                if submitted:
                    user = require_role("student")
                    student_id = user["user_id"]

                    try:
                        application_id = apply_for_internship(
                            student_id=student_id,
                            internship_id=internship_id,
                            cover_note=cover_note,
                        )

                        if application_id is not None:
                            st.success(
                                "🎉 Application submitted successfully!"
                            )
                        else:
                            st.warning(
                                "Your application could not be submitted. "
                                "You may have already applied, or the "
                                "internship may be closed or past its deadline."
                            )

                    except Exception:
                        st.error(
                            "Something went wrong while submitting "
                            "your application. Please try again."
                        )