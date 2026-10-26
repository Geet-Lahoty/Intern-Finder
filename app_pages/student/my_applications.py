import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_student_applications,
    get_application_history,
)


def format_date(value):
    """Format a date safely for display."""
    if value is None or pd.isna(value):
        return "Not available"

    try:
        return pd.to_datetime(value).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value)


def render():
    # Only logged-in students can access their applications.
    user = require_role("student")
    student_id = user["user_id"]

    st.title("📋 My Applications")
    st.caption(
        "Track your internship applications and follow their progress."
    )

    # Fetch only the current student's applications.
    try:
        applications = get_student_applications(student_id)

    except Exception as e:
        st.error("Unable to load your applications.")
        st.exception(e)
        return

    if applications is None or applications.empty:
        st.info(
            "You haven't applied for any internships yet."
        )

        st.write(
            "Explore available internships and submit your first application!"
        )

        if st.button("💼 Browse Internships", width="stretch"):
            st.switch_page(
                "app_pages/student/browse_internships.py"
            )

        return

    # Normalize statuses for consistent counting.
    statuses = (
        applications["status"]
        .fillna("unknown")
        .astype(str)
        .str.lower()
    )

    total = len(applications)
    pending = int((statuses == "pending").sum())
    shortlisted = int((statuses == "shortlisted").sum())
    accepted = int((statuses == "accepted").sum())
    rejected = int((statuses == "rejected").sum())

    # Overview metrics.
    st.subheader("📊 Application Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total", total)
    col2.metric("Pending", pending)
    col3.metric("Shortlisted", shortlisted)
    col4.metric("Accepted", accepted)
    col5.metric("Rejected", rejected)

    st.markdown("---")

    # Optional status filter.
    available_statuses = sorted(
        statuses.unique().tolist()
    )

    selected_status = st.selectbox(
        "Filter by application status",
        options=["All"] + available_statuses,
        format_func=lambda value: (
            value.replace("_", " ").title()
            if value != "All"
            else value
        ),
    )

    if selected_status != "All":
        displayed_applications = applications[
            statuses == selected_status
        ]
    else:
        displayed_applications = applications

    st.subheader(
        f"Your Applications ({len(displayed_applications)})"
    )

    if displayed_applications.empty:
        st.info("No applications match this status.")
        return

    # Display each application.
    for _, application in displayed_applications.iterrows():
        application_id = int(application["application_id"])

        status = str(
            application["status"] or "unknown"
        ).lower()

        status_labels = {
            "pending": "🟡 Pending",
            "shortlisted": "🔵 Shortlisted",
            "accepted": "🟢 Accepted",
            "rejected": "🔴 Rejected",
            "withdrawn": "⚪ Withdrawn",
        }

        status_label = status_labels.get(
            status,
            status.replace("_", " ").title(),
        )

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(
                    f"### {application['internship_title']}"
                )

                st.markdown(
                    f"🏢 **{application['company_name']}**"
                )

            with col2:
                st.markdown(f"**{status_label}**")

            st.caption(
                f"📅 Applied on: "
                f"{format_date(application['applied_at'])}"
            )

            cover_note = application.get("cover_note")

            with st.expander("📝 View Cover Note"):
                if (
                    cover_note is not None
                    and not pd.isna(cover_note)
                    and str(cover_note).strip()
                ):
                    st.write(cover_note)
                else:
                    st.caption(
                        "No cover note was submitted."
                    )

            with st.expander("🕒 Application Status History"):
                try:
                    history = get_application_history(
                        application_id
                    )

                    if history is None or history.empty:
                        st.info(
                            "No status history is available yet."
                        )
                    else:
                        history_display = history.copy()

                        history_display["changed_at"] = (
                            history_display["changed_at"]
                            .apply(format_date)
                        )

                        history_display["old_status"] = (
                            history_display["old_status"]
                            .fillna("Initial")
                            .astype(str)
                            .str.replace("_", " ")
                            .str.title()
                        )

                        history_display["new_status"] = (
                            history_display["new_status"]
                            .fillna("")
                            .astype(str)
                            .str.replace("_", " ")
                            .str.title()
                        )

                        history_display = history_display.rename(
                            columns={
                                "old_status": "Previous Status",
                                "new_status": "New Status",
                                "changed_at": "Changed At",
                            }
                        )

                        columns = [
                            "Previous Status",
                            "New Status",
                            "Changed At",
                        ]

                        st.dataframe(
                            history_display[columns],
                            hide_index=True,
                            width="stretch",
                        )

                except Exception:
                    st.error(
                        "Unable to retrieve application history."
                    )

    st.markdown("---")

    if st.button(
        "💼 Find More Internships",
        width="stretch",
    ):
        st.switch_page(
            "app_pages/student/browse_internships.py"
        )