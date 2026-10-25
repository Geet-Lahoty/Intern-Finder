import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from database.connection import run_query
from database.queries import (
    get_all_skills,
    get_student_skills,
    add_student_skill,
    update_student_skill_proficiency,
    remove_student_skill,
    get_student_projects,
    add_student_project,
    delete_student_project,
)

st.set_page_config(
    page_title="Student Portfolio Testing",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 Student Skills & Projects")
st.caption("Standalone development testing page")

students = run_query(
    """
    SELECT user_id, full_name, email
    FROM users
    WHERE role = 'student'
      AND is_active = TRUE
    ORDER BY full_name
    """
)

if students.empty:
    st.warning("No students found. Run your seed script first.")
    st.stop()

student_options = {
    f"{row.full_name} ({row.email})": int(row.user_id)
    for row in students.itertuples()
}

selected_student = st.selectbox(
    "Choose a demo student",
    list(student_options.keys()),
)

student_id = student_options[selected_student]

# =========================================================
# SKILLS
# =========================================================

st.divider()
st.header("🛠️ Skills")

skills = get_all_skills()
student_skills = get_student_skills(student_id)

st.subheader("Current Skills")

if student_skills.empty:
    st.info("This student has no skills yet.")
else:
    st.dataframe(
        student_skills,
        width="stretch",
        hide_index=True,
    )

st.subheader("Add a Skill")

if skills.empty:
    st.warning("No skills available. Add some skills to the skills table.")
else:
    skill_options = {
        f"{row.skill_name} ({row.category or 'Uncategorized'})":
        int(row.skill_id)
        for row in skills.itertuples()
    }

    with st.form("add_skill_form"):
        selected_skill = st.selectbox(
            "Skill",
            list(skill_options.keys()),
        )

        proficiency = st.selectbox(
            "Proficiency",
            ["beginner", "intermediate", "advanced"],
        )

        add_skill_clicked = st.form_submit_button("Add Skill")

    if add_skill_clicked:
        try:
            result = add_student_skill(
                student_id,
                skill_options[selected_skill],
                proficiency,
            )

            if result is not None:
                st.success("Skill added successfully!")
                st.rerun()
            else:
                st.warning("This skill is already associated with the student.")

        except Exception as e:
            st.error("Failed to add skill.")
            st.exception(e)

st.subheader("Update Skill Proficiency")

if not student_skills.empty:
    current_skill_options = {
        f"{row.skill_name} — {row.proficiency}":
        int(row.skill_id)
        for row in student_skills.itertuples()
    }

    with st.form("update_skill_form"):
        selected_current_skill = st.selectbox(
            "Choose a skill",
            list(current_skill_options.keys()),
        )

        new_proficiency = st.selectbox(
            "New proficiency",
            ["beginner", "intermediate", "advanced"],
        )

        update_skill_clicked = st.form_submit_button(
            "Update Proficiency"
        )

    if update_skill_clicked:
        try:
            result = update_student_skill_proficiency(
                student_id,
                current_skill_options[selected_current_skill],
                new_proficiency,
            )

            if result is not None:
                st.success("Proficiency updated!")
                st.rerun()
            else:
                st.warning("No matching skill was updated.")

        except Exception as e:
            st.error("Failed to update proficiency.")
            st.exception(e)

st.subheader("Remove a Skill")

if not student_skills.empty:
    remove_options = {
        row.skill_name: int(row.skill_id)
        for row in student_skills.itertuples()
    }

    with st.form("remove_skill_form"):
        selected_remove_skill = st.selectbox(
            "Choose a skill to remove",
            list(remove_options.keys()),
        )

        remove_confirmed = st.checkbox(
            "Confirm removal"
        )

        remove_clicked = st.form_submit_button(
            "Remove Skill",
            disabled=not remove_confirmed,
        )

    if remove_clicked:
        try:
            result = remove_student_skill(
                student_id,
                remove_options[selected_remove_skill],
            )

            if result is not None:
                st.success("Skill removed!")
                st.rerun()
            else:
                st.warning("Skill was not found.")

        except Exception as e:
            st.error("Failed to remove skill.")
            st.exception(e)


# =========================================================
# PROJECTS
# =========================================================

st.divider()
st.header("💻 Projects")

projects = get_student_projects(student_id)

if projects.empty:
    st.info("No projects have been added yet.")
else:
    st.dataframe(
        projects,
        width="stretch",
        hide_index=True,
    )

st.subheader("Add a Project")

with st.form("add_project_form"):
    project_title = st.text_input("Project title")
    project_description = st.text_area("Description")
    project_url = st.text_input("Project URL")

    add_project_clicked = st.form_submit_button("Add Project")

if add_project_clicked:
    try:
        result = add_student_project(
            student_id,
            project_title,
            project_description,
            project_url,
        )

        if result is not None:
            st.success(f"Project added successfully! ID: {result}")
            st.rerun()
        else:
            st.error("Student profile not found. Project was not added.")

    except Exception as e:
        st.error("Failed to add project.")
        st.exception(e)

st.subheader("Delete a Project")

# Refresh the list after adding or deleting a project.
projects = get_student_projects(student_id)

if not projects.empty:
    project_options = {
        f"{row.title} (ID: {row.project_id})": int(row.project_id)
        for row in projects.itertuples()
    }

    with st.form("delete_project_form"):
        selected_project = st.selectbox(
            "Choose a project",
            list(project_options.keys()),
        )

        delete_confirmed = st.checkbox(
            "I confirm that I want to delete this project."
        )

        delete_clicked = st.form_submit_button(
            "Delete Project",
            disabled=not delete_confirmed,
        )

    if delete_clicked:
        try:
            result = delete_student_project(
                student_id,
                project_options[selected_project],
            )

            if result is not None:
                st.success("Project deleted.")
                st.rerun()
            else:
                st.warning("Project not found for this student.")

        except Exception as e:
            st.error("Failed to delete project.")
            st.exception(e)