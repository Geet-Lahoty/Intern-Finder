import pandas as pd
import streamlit as st

from database import recruiter_queries as rq
from services import recruiter_service as svc
from services.auth_service import require_role

ACTION_LABELS = {"shortlisted": "Shortlist", "rejected": "Reject", "accepted": "Accept"}


def _show(value):
    return "—" if value is None or pd.isna(value) else value


def render():
    user = require_role("recruiter")
    recruiter_id = user["user_id"]

    st.title("Applications")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    # ---- summary by status (GROUP BY) ----
    counts = rq.get_application_status_counts(recruiter_id)
    if counts.empty:
        st.info("No students have applied to your internships yet.")
        return
    count_map = dict(zip(counts["status"], counts["total"]))
    cols = st.columns(len(rq.APPLICATION_STATUSES))
    for col, s in zip(cols, rq.APPLICATION_STATUSES):
        col.metric(s.capitalize(), int(count_map.get(s, 0)))

    # ---- filters ----
    internships = rq.get_recruiter_internships(recruiter_id)
    options = {None: "All internships"}
    options.update({int(r.internship_id): f"#{r.internship_id} · {r.title}"
                    for r in internships.itertuples()})

    f1, f2 = st.columns(2)
    internship_id = f1.selectbox("Internship", list(options), format_func=options.get)
    status = f2.selectbox("Status", [None, *rq.APPLICATION_STATUSES],
                          format_func=lambda s: "All statuses" if s is None else s)

    apps = rq.get_recruiter_applications(recruiter_id, internship_id, status)
    st.caption(f"{len(apps)} application(s)")
    if apps.empty:
        st.info("No applications match these filters.")
        return

    st.dataframe(apps.drop(columns=["internship_id"]), hide_index=True, width="stretch")

    # ---- detail ----
    st.divider()
    st.subheader("Application details")
    labels = {int(r.application_id): f"#{r.application_id} · {r.student_name} → {r.internship_title}"
              for r in apps.itertuples()}
    chosen = st.selectbox("Choose an application", list(labels),
                          format_func=labels.get, key="app_detail_select")

    detail_df = rq.get_application_detail(chosen, recruiter_id)  # ownership checked in SQL
    if detail_df.empty:
        st.error("Application not found.")
        return
    d = detail_df.iloc[0]

    left, right = st.columns(2)
    with left:
        st.markdown(f"**Student:** {d['student_name']}  \n**Email:** {d['student_email']}")
        st.markdown(f"**University:** {_show(d['university'])}  \n**Degree:** {_show(d['degree'])}  \n"
                    f"**Graduation year:** {_show(d['graduation_year'])}  \n**CGPA:** {_show(d['cgpa'])}  \n"
                    f"**City:** {_show(d['city'])}  \n**Phone:** {_show(d['phone'])}")
    with right:
        st.markdown(f"**Internship:** {d['internship_title']}  \n**Status:** `{d['status']}`  \n"
                    f"**Applied:** {d['applied_at']}")
        st.markdown(f"**Skills:** {_show(d['student_skills'])}")
        for label, key in [("GitHub", "github_url"), ("LinkedIn", "linkedin_url"),
                           ("Portfolio", "portfolio_url"), ("Resume", "resume_url")]:
            if not pd.isna(d[key]):
                st.markdown(f"[{label}]({d[key]})")

    st.markdown("**Cover note**")
    st.write(_show(d["cover_note"]))
    st.markdown("**Bio**")
    st.write(_show(d["bio"]))

    # ---- review (Step 4) ----
    st.divider()
    st.subheader("Review")
    current_status = d["status"]
    targets = [s for s in rq.APPLICATION_STATUSES
               if s in svc.APPLICATION_TRANSITIONS.get(current_status, set())]

    st.markdown(f"Current status: `{current_status}`")
    if not targets:
        st.info(f"This application is '{current_status}', which is a final status for recruiters.")
    else:
        button_cols = st.columns(len(targets))
        for col, target in zip(button_cols, targets):
            if col.button(ACTION_LABELS[target], key=f"review_{chosen}_{target}"):
                try:
                    svc.change_application_status(recruiter_id, chosen, target)
                    st.session_state["flash"] = f"Application #{chosen} is now {target}."
                    st.rerun()
                except svc.ServiceError as error:
                    st.error(str(error))

    st.markdown("**Status history**")
    history = rq.get_application_history(chosen, recruiter_id)
    if history.empty:
        st.caption("No history recorded for this application.")
    else:
        st.dataframe(history, hide_index=True, width="stretch")