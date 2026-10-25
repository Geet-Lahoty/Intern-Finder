import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import get_student_applications


def render():
    # --------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------
    user = require_role("student")

    if not user:
        return

    student_id = user["user_id"]

    # --------------------------------------------------
    # PAGE HEADER
    # --------------------------------------------------
    st.title("🎓 Student Dashboard")
    st.write("Welcome back! Here's your internship application overview.")

    st.divider()

    # --------------------------------------------------
    # FETCH APPLICATIONS
    # --------------------------------------------------
    try:
        applications = get_student_applications(student_id)

        if applications is None:
            applications = pd.DataFrame()

    except Exception as e:
        st.error(f"Unable to load your applications: {e}")
        applications = pd.DataFrame()

    # --------------------------------------------------
    # APPLICATION METRICS
    # --------------------------------------------------
    if not applications.empty and "status" in applications.columns:
        statuses = (
            applications["status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        total_applications = len(applications)
        pending = int(statuses.eq("pending").sum())
        shortlisted = int(statuses.eq("shortlisted").sum())
        accepted = int(statuses.eq("accepted").sum())
        rejected = int(statuses.eq("rejected").sum())
    else:
        total_applications = 0
        pending = 0
        shortlisted = 0
        accepted = 0
        rejected = 0

    # --------------------------------------------------
    # METRICS DISPLAY
    # --------------------------------------------------
    st.subheader("📊 Application Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Applications", total_applications)
    col2.metric("Pending", pending)
    col3.metric("Shortlisted", shortlisted)
    col4.metric("Accepted", accepted)
    col5.metric("Rejected", rejected)

    st.divider()

    # --------------------------------------------------
    # QUICK ACTIONS
    # --------------------------------------------------
    st.subheader("⚡ Quick Actions")
    st.caption("Jump straight to the section you need.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "🔍 Browse Internships",
            use_container_width=True,
            key="dashboard_browse",
        ):
            st.switch_page("app_pages/student/browse_internships.py")

    with col2:
        if st.button(
            "👤 My Profile",
            use_container_width=True,
            key="dashboard_profile",
        ):
            st.switch_page("app_pages/student/profile.py")

    with col3:
        if st.button(
            "📄 My Applications",
            use_container_width=True,
            key="dashboard_applications",
        ):
            st.switch_page("app_pages/student/my_applications.py")

    col4, col5 = st.columns(2)

    with col4:
        if st.button(
            "🛠️ My Skills",
            use_container_width=True,
            key="dashboard_skills",
        ):
            st.switch_page("app_pages/student/my_skills.py")

    with col5:
        if st.button(
            "🚀 My Projects",
            use_container_width=True,
            key="dashboard_projects",
        ):
            st.switch_page("app_pages/student/my_projects.py")

    st.divider()

    # --------------------------------------------------
    # RECENT APPLICATIONS
    # --------------------------------------------------
    st.subheader("🕒 Recent Applications")

    if applications.empty:
        st.info(
            "You haven't applied to any internships yet. "
            "Browse available internships to get started!"
        )

        if st.button(
            "Explore Internships",
            use_container_width=True,
            key="dashboard_explore_empty",
        ):
            st.switch_page("app_pages/student/browse_internships.py")

    else:
        recent_applications = applications.head(5)

        for _, application in recent_applications.iterrows():
            internship_title = application.get(
                "internship_title", "Untitled Internship"
            )
            company_name = application.get(
                "company_name", "Unknown Company"
            )
            status = str(
                application.get("status", "Unknown")
            ).replace("_", " ").title()

            applied_at = application.get("applied_at")

            if pd.notna(applied_at):
                try:
                    applied_date = pd.to_datetime(applied_at).strftime(
                        "%d %b %Y"
                    )
                except (ValueError, TypeError):
                    applied_date = str(applied_at)
            else:
                applied_date = "Date unavailable"

            with st.container(border=True):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**{internship_title}**")
                    st.caption(f"🏢 {company_name}")
                    st.caption(f"Applied on: {applied_date}")

                with col2:
                    st.write("**Status**")
                    st.write(status)

        if st.button(
            "View All Applications →",
            use_container_width=True,
            key="dashboard_view_all",
        ):
            st.switch_page("app_pages/student/my_applications.py")

    st.divider()

    st.caption("Keep your profile updated and continue exploring opportunities!")