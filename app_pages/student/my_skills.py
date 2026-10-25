import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_all_skills,
    get_student_skills,
    add_student_skill,
    update_student_skill_proficiency,
    remove_student_skill,
)


PROFICIENCY_LEVELS = [
    "beginner",
    "intermediate",
    "advanced",
]


def render():
    # Only authenticated students can manage their skills.
    user = require_role("student")
    student_id = user["user_id"]

    st.title("🛠️ My Skills")
    st.caption(
        "Show recruiters what you know and how proficient you are."
    )

    # Fetch available skills and the student's current skills.
    try:
        all_skills = get_all_skills()
        student_skills = get_student_skills(student_id)

    except Exception as e:
        st.error("Unable to load your skills.")
        st.exception(e)
        return

    if all_skills is None:
        all_skills = pd.DataFrame(
            columns=["skill_id", "skill_name", "category"]
        )

    if student_skills is None:
        student_skills = pd.DataFrame(
            columns=[
                "skill_id",
                "skill_name",
                "category",
                "proficiency",
            ]
        )

    # Current skill statistics.
    st.subheader("📊 Your Skills Overview")

    total_skills = len(student_skills)

    advanced_count = (
        int(
            (
                student_skills["proficiency"]
                .fillna("")
                .str.lower()
                == "advanced"
            ).sum()
        )
        if not student_skills.empty
        else 0
    )

    col1, col2 = st.columns(2)

    col1.metric("Skills Added", total_skills)
    col2.metric("Advanced Skills", advanced_count)

    st.markdown("---")

    # Add a skill.
    st.subheader("➕ Add a Skill")

    if all_skills.empty:
        st.info(
            "No skills are available in the database yet. "
            "Please ask the administrator to populate the skills table."
        )

    else:
        existing_skill_ids = (
            set(student_skills["skill_id"].tolist())
            if not student_skills.empty
            else set()
        )

        available_skills = all_skills[
            ~all_skills["skill_id"].isin(existing_skill_ids)
        ]

        if available_skills.empty:
            st.success("You've added all available skills!")

        else:
            skill_options = {
                int(row["skill_id"]): (
                    f"{row['skill_name']}"
                    + (
                        f" ({row['category']})"
                        if pd.notna(row["category"])
                        and str(row["category"]).strip()
                        else ""
                    )
                )
                for _, row in available_skills.iterrows()
            }

            with st.form("add_skill_form"):
                selected_skill_id = st.selectbox(
                    "Choose a skill",
                    options=list(skill_options.keys()),
                    format_func=lambda skill_id: (
                        skill_options[skill_id]
                    ),
                )

                proficiency = st.selectbox(
                    "Proficiency Level",
                    options=PROFICIENCY_LEVELS,
                    index=0,
                    format_func=lambda value: value.title(),
                )

                add_clicked = st.form_submit_button(
                    "➕ Add Skill",
                    width="stretch",
                )

            if add_clicked:
                try:
                    result = add_student_skill(
                        student_id=student_id,
                        skill_id=selected_skill_id,
                        proficiency=proficiency,
                    )

                    if result is not None:
                        st.success("Skill added successfully!")
                        st.rerun()
                    else:
                        st.warning(
                            "This skill may already be in your profile. "
                            "Refresh and try again."
                        )

                except Exception as e:
                    st.error("Unable to add this skill.")
                    st.exception(e)

        # Display and manage current skills in a grid.
        st.markdown("---")
        st.subheader("📚 Your Current Skills")

        if student_skills.empty:
            st.info(
                "You haven't added any skills yet. "
                "Add your first skill using the form above!"
            )
            return

        # Three cards per row.
        cards_per_row = 3

        for start in range(0, len(student_skills), cards_per_row):
            row_skills = student_skills.iloc[
                start:start + cards_per_row
            ]

            columns = st.columns(cards_per_row)

            for column, (_, skill) in zip(columns, row_skills.iterrows()):
                with column:
                    skill_id = int(skill["skill_id"])
                    skill_name = skill["skill_name"]
                    category = skill.get("category")

                    current_proficiency = str(
                        skill["proficiency"] or "beginner"
                    ).lower()

                    if current_proficiency not in PROFICIENCY_LEVELS:
                        current_proficiency = "beginner"

                    # Individual skill card.
                    with st.container(border=True):
                        # Skill title and compact remove button.
                        title_col, remove_col = st.columns([5, 1])

                        with title_col:
                            st.markdown(f"### {skill_name}")

                        with remove_col:
                            if st.button(
                                "🗑️",
                                key=f"remove_skill_{skill_id}",
                                help=f"Remove {skill_name} from your skills",
                                type="secondary",
                            ):
                                try:
                                    result = remove_student_skill(
                                        student_id=student_id,
                                        skill_id=skill_id,
                                    )

                                    if result is not None:
                                        st.toast(f"{skill_name} removed!")
                                        st.rerun()
                                    else:
                                        st.warning("Skill not found in your profile.")

                                except Exception as e:
                                    st.error("Unable to remove skill.")
                                    st.exception(e)

                        if (
                            category is not None
                            and not pd.isna(category)
                            and str(category).strip()
                        ):
                            st.caption(f"📂 {category}")

                        st.markdown(
                            f"**Level:** {current_proficiency.title()}"
                        )

                        # Update proficiency.
                        with st.form(
                            key=f"update_skill_form_{skill_id}"
                        ):
                            new_proficiency = st.selectbox(
                                "Proficiency",
                                options=PROFICIENCY_LEVELS,
                                index=PROFICIENCY_LEVELS.index(
                                    current_proficiency
                                ),
                                format_func=lambda value: value.title(),
                                key=f"proficiency_{skill_id}",
                            )

                            update_clicked = st.form_submit_button(
                                "💾 Update",
                                width="stretch",
                            )

                        if update_clicked:
                            try:
                                result = update_student_skill_proficiency(
                                    student_id=student_id,
                                    skill_id=skill_id,
                                    proficiency=new_proficiency,
                                )

                                if result is not None:
                                    st.success("Skill updated!")
                                    st.rerun()
                                else:
                                    st.warning(
                                        "No changes were saved. "
                                        "Check whether this skill still "
                                        "exists in your profile."
                                    )

                            except Exception as e:
                                st.error("Unable to update skill.")
                                st.exception(e)

                       