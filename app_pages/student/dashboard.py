import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_student_applications,
    get_student_profile,
)


def render():
    # Protect the page and identify the logged-in student.
    user = require_role("student")
    student_id = user["user_id"]

    st.title("🎓 Student Dashboard")
    st.caption("Your internship journey starts here.")

    st.markdown(f"### Welcome back, {user['full_name']}! 👋")

    # Fetch the student's data.
    try:
        applications = get_student_applications(student_id)
        profile = get_student_profile(student_id)

    except Exception as e:
        st.error("Unable to load your dashboard data.")
        st.exception(e)
        return

    # Safely handle empty query results.
    if applications is None:
        applications = []

    if profile is None or profile.empty:
        st.warning(
            "Your student profile could not be found. "
            "Please contact the administrator."
        )
        return

    # Calculate application statistics.
    if hasattr(applications, "empty") and not applications.empty:
        statuses = (
            applications["status"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        total_applications = len(applications)
        pending = int((statuses == "pending").sum())
        shortlisted = int((statuses == "shortlisted").sum())
        accepted = int((statuses == "accepted").sum())

    else:
        total_applications = 0
        pending = 0
        shortlisted = 0
        accepted = 0

    # Dashboard metrics.
    st.markdown("---")
    st.subheader("📊 Application Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Applications", total_applications)
    col2.metric("Pending", pending)
    col3.metric("Shortlisted", shortlisted)
    col4.metric("Accepted", accepted)

    # Profile completion.
    st.markdown("---")
    st.subheader("👤 Your Profile")

    student_profile = profile.iloc[0]

    profile_fields = [
        "university",
        "degree",
        "graduation_year",
        "cgpa",
        "city",
        "phone",
        "bio",
        "resume_url",
        "github_url",
        "linkedin_url",
        "portfolio_url",
    ]

    completed_fields = sum(
        1
        for field in profile_fields
        if (
            field in profile.columns
            and student_profile[field] is not None
            and str(student_profile[field]).strip() != ""
            and str(student_profile[field]).lower() != "nan"
        )
    )

    total_fields = len(profile_fields)
    completion = completed_fields / total_fields

    col1, col2 = st.columns([3, 1])

    with col1:
        st.progress(completion)
        st.caption(
            f"{completed_fields} of {total_fields} profile fields completed"
        )

    with col2:
        st.metric("Profile Completion", f"{completion:.0%}")

    if completion < 1:
        st.info(
            "💡 Complete your profile to present your qualifications "
            "and portfolio to recruiters."
        )

    # Recent applications.
    st.markdown("---")
    st.subheader("📋 Recent Applications")

    if (
        hasattr(applications, "empty")
        and not applications.empty
    ):
        recent = applications.head(5).copy()

        recent["status"] = (
            recent["status"]
            .fillna("unknown")
            .astype(str)
            .str.replace("_", " ")
            .str.title()
        )

        display_columns = {
            "internship_title": "Internship",
            "company_name": "Company",
            "status": "Status",
            "applied_at": "Applied On",
        }

        available_columns = {
            key: value
            for key, value in display_columns.items()
            if key in recent.columns
        }

        st.dataframe(
            recent[list(available_columns)].rename(
                columns=available_columns
            ),
            hide_index=True,
            width="stretch",
        )

    else:
        st.info(
            "You haven't applied for any internships yet. "
            "Explore available opportunities to get started!"
        )

    # Quick navigation.
    st.markdown("---")
    st.subheader("🚀 Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "💼 Browse Internships",
            width="stretch",
        ):
            st.switch_page("app_pages/student/browse_internships.py")

    with col2:
        if st.button(
            "👤 My Profile",
            width="stretch",
        ):
            st.switch_page("app_pages/student/profile.py")

    with col3:
        if st.button(
            "📋 My Applications",
            width="stretch",
        ):
            st.switch_page("app_pages/student/my_applications.py")