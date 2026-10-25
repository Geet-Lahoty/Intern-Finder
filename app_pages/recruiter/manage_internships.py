import pandas as pd
import streamlit as st

from database import recruiter_queries as rq
from services.auth_service import require_role
from services import recruiter_service as svc

WORK_MODE_LABELS = {"remote": "Remote", "on_site": "On-site", "hybrid": "Hybrid"}


def _date_or_none(value):
    return None if pd.isna(value) else pd.to_datetime(value).date()


def _form_fields(defaults: dict, skills_by_id: dict, key_suffix: str):
    """Shared input widgets for create and edit forms."""
    title = st.text_input("Title", value=defaults["title"], key=f"title_{key_suffix}")
    description = st.text_area("Description", value=defaults["description"],
                               key=f"desc_{key_suffix}")
    location = st.text_input("Location", value=defaults["location"],
                             key=f"loc_{key_suffix}")
    work_mode = st.selectbox(
        "Work mode", list(WORK_MODE_LABELS),
        index=list(WORK_MODE_LABELS).index(defaults["work_mode"]),
        format_func=WORK_MODE_LABELS.get, key=f"mode_{key_suffix}",
    )
    c1, c2, c3 = st.columns(3)
    stipend = c1.number_input("Monthly stipend (0 = unpaid)", min_value=0.0,
                              value=defaults["stipend"], step=500.0,
                              key=f"stip_{key_suffix}")
    duration = c2.number_input("Duration (months)", min_value=1,
                               value=defaults["duration"], step=1,
                               key=f"dur_{key_suffix}")
    openings = c3.number_input("Openings", min_value=1,
                               value=defaults["openings"], step=1,
                               key=f"open_{key_suffix}")

    has_deadline = st.checkbox("Set an application deadline",
                               value=defaults["deadline"] is not None,
                               key=f"hasdl_{key_suffix}")
    deadline = None
    if has_deadline:
        deadline = st.date_input("Deadline", value=defaults["deadline"] or pd.Timestamp.today().date(),
                                 key=f"dl_{key_suffix}")

    skill_ids = st.multiselect(
        "Required skills", options=list(skills_by_id),
        default=defaults["skill_ids"], format_func=skills_by_id.get,
        key=f"skills_{key_suffix}",
    )

    data = {
        "title": title, "description": description, "location": location,
        "work_mode": work_mode, "stipend_monthly": float(stipend),
        "duration_months": int(duration), "openings": int(openings),
        "deadline": deadline,
    }
    return data, skill_ids


def render():
    user = require_role("recruiter")
    recruiter_id = user["user_id"]

    st.title("Manage Internships")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    skills_df = rq.get_all_skills()
    skills_by_id = {int(r.skill_id): r.skill_name for r in skills_df.itertuples()}

    tab_list, tab_create, tab_edit = st.tabs(["My internships", "Create new", "Edit / change status"])

    # ---- Tab 1: list ----
    with tab_list:
        internships = rq.get_recruiter_internships(recruiter_id)
        if internships.empty:
            st.info("You have not posted any internships yet.")
        else:
            st.dataframe(internships, hide_index=True, width="stretch")

    # ---- Tab 2: create ----
    with tab_create:
        blank = {"title": "", "description": "", "location": "", "work_mode": "remote",
                 "stipend": 0.0, "duration": 3, "openings": 1, "deadline": None,
                 "skill_ids": []}
        with st.form("create_form"):
            data, skill_ids = _form_fields(blank, skills_by_id, "create")
            publish = st.checkbox("Publish now (students can see it immediately)", value=True)
            submitted = st.form_submit_button("Create internship")

        if submitted:
            try:
                new_id = svc.create_internship(recruiter_id, data, skill_ids, publish)
                st.session_state["flash"] = f"Internship #{new_id} created."
                st.rerun()
            except svc.ServiceError as error:
                st.error(str(error))

    # ---- Tab 3: edit / status ----
    with tab_edit:
        internships = rq.get_recruiter_internships(recruiter_id)
        if internships.empty:
            st.info("Nothing to edit yet.")
            return

        options = {int(r.internship_id): f"#{r.internship_id} · {r.title} ({r.status})"
                   for r in internships.itertuples()}
        chosen_id = st.selectbox("Choose an internship", list(options),
                                 format_func=options.get)

        # Ownership re-checked in SQL: returns nothing if it is not yours.
        row_df = rq.get_owned_internship(chosen_id, recruiter_id)
        if row_df.empty:
            st.error("Internship not found.")
            return
        row = row_df.iloc[0]
        status = row["status"]

        st.markdown(f"**Current status:** `{status}`")
        targets = sorted(svc.INTERNSHIP_TRANSITIONS.get(status, set()))
        if targets:
            cols = st.columns(len(targets))
            for col, target in zip(cols, targets):
                if col.button(f"Mark as {target}", key=f"status_{chosen_id}_{target}"):
                    try:
                        svc.change_internship_status(recruiter_id, chosen_id, target)
                        st.session_state["flash"] = f"Internship #{chosen_id} is now {target}."
                        st.rerun()
                    except svc.ServiceError as error:
                        st.error(str(error))
        else:
            st.info("This internship is in a final state.")

        if status in svc.EDITABLE_STATUSES:
            st.divider()
            st.subheader("Edit details")
            defaults = {
                "title": row["title"],
                "description": row["description"],
                "location": "" if pd.isna(row["location"]) else row["location"],
                "work_mode": row["work_mode"],
                "stipend": 0.0 if pd.isna(row["stipend_monthly"]) else float(row["stipend_monthly"]),
                "duration": int(row["duration_months"]),
                "openings": int(row["openings"]),
                "deadline": _date_or_none(row["deadline"]),
                "skill_ids": rq.get_internship_skill_ids(chosen_id),
            }
            with st.form(f"edit_form_{chosen_id}"):
                data, skill_ids = _form_fields(defaults, skills_by_id, f"edit{chosen_id}")
                saved = st.form_submit_button("Save changes")

            if saved:
                try:
                    svc.update_internship(recruiter_id, chosen_id, data, skill_ids)
                    st.session_state["flash"] = f"Internship #{chosen_id} updated."
                    st.rerun()
                except svc.ServiceError as error:
                    st.error(str(error))