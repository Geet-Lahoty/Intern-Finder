import pandas as pd
import streamlit as st

from database.recruiter_queries import (
    get_dashboard_stats,
    get_recruiter_internships,
    get_recruiter_profile,
)
from services.auth_service import require_role


def render():
    user = require_role("recruiter")
    recruiter_id = user["user_id"]  # from the server-side session, never a form

    profile = get_recruiter_profile(recruiter_id)
    if profile.empty:
        st.error("Your account has no recruiter profile. Contact the administrator.")
        st.stop()

    p = profile.iloc[0]
    job_title = "Recruiter" if pd.isna(p["job_title"]) else p["job_title"]
    company = "No company assigned" if pd.isna(p["company_name"]) else p["company_name"]

    st.title("Recruiter Dashboard")
    st.caption(f"{p['full_name']} · {job_title} · {company}")

    stats = get_dashboard_stats(recruiter_id).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total internships", int(stats["total_internships"]))
    c2.metric("Open internships", int(stats["open_internships"]))
    c3.metric("Total applications", int(stats["total_applications"]))
    c4.metric("Awaiting review", int(stats["awaiting_review"]))

    st.subheader("Your internships")
    internships = get_recruiter_internships(recruiter_id)
    if internships.empty:
        st.info("You have not posted any internships yet.")
    else:
        st.dataframe(internships, hide_index=True, width="stretch")