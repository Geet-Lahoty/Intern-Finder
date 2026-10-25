import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_student_projects,
    add_student_project,
    delete_student_project,
)


def render():
    # Restrict access to logged-in students.
    user = require_role("student")
    student_id = user["user_id"]

    st.title("🚀 My Projects")
    st.caption(
        "Showcase your work and build a portfolio recruiters can explore."
    )

    # Fetch projects belonging to the current student.
    try:
        projects = get_student_projects(student_id)
    except Exception as e:
        st.error("Unable to load your projects.")
        st.exception(e)
        return

    if projects is None:
        projects = pd.DataFrame(
            columns=[
                "project_id",
                "title",
                "description",
                "project_url",
                "created_at",
            ]
        )

    # Project overview.
    st.subheader("📊 Portfolio Overview")

    col1, col2 = st.columns(2)

    col1.metric("Total Projects", len(projects))

    linked_projects = (
        projects["project_url"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
        if not projects.empty
        else 0
    )

    col2.metric("Projects With Links", int(linked_projects))

    st.markdown("---")

    # Add a project.
    st.subheader("➕ Add a Project")

    with st.expander("Create a new project", expanded=projects.empty):
        with st.form("add_project_form"):
            title = st.text_input(
                "Project Title *",
                placeholder="e.g. Internship Finder",
                max_chars=150,
            )

            description = st.text_area(
                "Project Description",
                placeholder=(
                    "Describe what you built, the technologies used, "
                    "and the problem your project solves..."
                ),
                max_chars=3000,
                height=120,
            )

            project_url = st.text_input(
                "Project URL",
                placeholder="https://github.com/username/project",
            )

            submitted = st.form_submit_button(
                "➕ Add Project",
                width="stretch",
            )

        if submitted:
            if not title.strip():
                st.error("Project title is required.")

            elif project_url.strip() and not (
                project_url.strip().startswith("https://")
                or project_url.strip().startswith("http://")
            ):
                st.error(
                    "Enter a valid project URL beginning with "
                    "https:// or http://."
                )

            else:
                try:
                    project_id = add_student_project(
                        student_id=student_id,
                        title=title,
                        description=description,
                        project_url=project_url,
                    )

                    if project_id is not None:
                        st.success("🎉 Project added successfully!")
                        st.rerun()
                    else:
                        st.error(
                            "The project could not be added. "
                            "Please try again."
                        )

                except Exception as e:
                    st.error("Unable to add your project.")
                    st.exception(e)

    # Display projects.
    st.markdown("---")
    st.subheader("📂 Your Portfolio")

    if projects.empty:
        st.info(
            "Your portfolio is empty. Add your first project above!"
        )
        return

    # Two cards per row.
    cards_per_row = 2

    for start in range(0, len(projects), cards_per_row):
        row_projects = projects.iloc[
            start:start + cards_per_row
        ]

        columns = st.columns(cards_per_row)

        for column, (_, project) in zip(
            columns,
            row_projects.iterrows(),
        ):
            with column:
                project_id = int(project["project_id"])
                project_title = str(project["title"])

                with st.container(border=True):
                    # Title and compact delete button.
                    title_col, delete_col = st.columns([5, 1])

                    with title_col:
                        st.markdown(f"### {project_title}")

                    with delete_col:
                        if st.button(
                            "🗑️",
                            key=f"delete_project_{project_id}",
                            help=f"Delete {project_title}",
                        ):
                            st.session_state[
                                f"confirm_delete_project_{project_id}"
                            ] = True

                    # Optional deletion confirmation.
                    confirm_key = (
                        f"confirm_delete_project_{project_id}"
                    )

                    if st.session_state.get(confirm_key, False):
                        st.warning("Delete this project permanently?")

                        confirm_col, cancel_col = st.columns(2)

                        with confirm_col:
                            if st.button(
                                "Yes, delete",
                                key=f"confirm_yes_{project_id}",
                                type="primary",
                            ):
                                try:
                                    deleted_id = delete_student_project(
                                        student_id=student_id,
                                        project_id=project_id,
                                    )

                                    st.session_state.pop(
                                        confirm_key, None
                                    )

                                    if deleted_id is not None:
                                        st.success("Project deleted.")
                                        st.rerun()
                                    else:
                                        st.warning(
                                            "Project not found."
                                        )

                                except Exception as e:
                                    st.error(
                                        "Unable to delete the project."
                                    )
                                    st.exception(e)

                        with cancel_col:
                            if st.button(
                                "Cancel",
                                key=f"confirm_no_{project_id}",
                            ):
                                st.session_state.pop(
                                    confirm_key, None
                                )
                                st.rerun()

                    # Description.
                    description = project.get("description")

                    if (
                        description is not None
                        and not pd.isna(description)
                        and str(description).strip()
                    ):
                        st.write(str(description))
                    else:
                        st.caption("No description provided.")

                    # Project link.
                    project_url = project.get("project_url")

                    if (
                        project_url is not None
                        and not pd.isna(project_url)
                        and str(project_url).strip()
                    ):
                        st.link_button(
                            "🔗 View Project",
                            str(project_url),
                            width="stretch",
                        )
                    else:
                        st.caption("No project link added.")

                    # Creation date.
                    created_at = project.get("created_at")

                    if (
                        created_at is not None
                        and not pd.isna(created_at)
                    ):
                        try:
                            formatted_date = pd.to_datetime(
                                created_at
                            ).strftime("%d %b %Y")

                            st.caption(
                                f"📅 Added on {formatted_date}"
                            )
                        except (ValueError, TypeError):
                            pass