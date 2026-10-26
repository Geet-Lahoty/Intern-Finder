import pandas as pd
import streamlit as st

from services.auth_service import require_role
from database.queries import (
    get_all_internships,
    search_internships,
    get_student_skills,
    get_internship_skills,
    apply_for_internship,
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


def is_missing(value):
    """Safely check whether a value is missing."""
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def get_skill_names(skills):
    """Extract skill names from a collection of skill records."""
    if skills is None or skills.empty:
        return set()

    return {
        str(skill).strip()
        for skill in skills["skill_name"]
        if not is_missing(skill) and str(skill).strip()
    }


def calculate_skill_matches(internships, student_skills, internship_skills):
    """
    Calculate each internship's skill-match percentage.

    Match percentage =
        matched required skills / total required skills * 100
    """

    student_skill_ids = set()

    if student_skills is not None and not student_skills.empty:
        student_skill_ids = {
            int(skill_id)
            for skill_id in student_skills["skill_id"]
            if not is_missing(skill_id)
        }

    # Group required skills by internship ID.
    required_skills_by_internship = {}

    if internship_skills is not None and not internship_skills.empty:
        for _, skill in internship_skills.iterrows():
            internship_id = int(skill["internship_id"])

            required_skills_by_internship.setdefault(
                internship_id, []
            ).append(
                {
                    "skill_id": int(skill["skill_id"]),
                    "skill_name": str(skill["skill_name"]),
                }
            )

    # Calculate the match for each internship.
    results = []

    for _, internship in internships.iterrows():
        internship_data = internship.to_dict()

        internship_id = int(internship["internship_id"])

        required_skills = required_skills_by_internship.get(
            internship_id, []
        )

        required_skill_ids = {
            skill["skill_id"] for skill in required_skills
        }

        matched_skill_ids = (
            student_skill_ids & required_skill_ids
        )

        matched_skills = [
            skill["skill_name"]
            for skill in required_skills
            if skill["skill_id"] in matched_skill_ids
        ]

        missing_skills = [
            skill["skill_name"]
            for skill in required_skills
            if skill["skill_id"] not in matched_skill_ids
        ]

        if required_skill_ids:
            match_percentage = round(
                len(matched_skill_ids)
                / len(required_skill_ids)
                * 100
            )
        else:
            match_percentage = None

        internship_data["required_skills"] = [
            skill["skill_name"] for skill in required_skills
        ]

        internship_data["matched_skills"] = matched_skills
        internship_data["missing_skills"] = missing_skills
        internship_data["skill_match_percentage"] = match_percentage

        results.append(internship_data)

    # Sort internships by match percentage, highest first.
    # Internships without specified skills appear last.
    results.sort(
        key=lambda internship: (
            internship["skill_match_percentage"] is not None,
            internship["skill_match_percentage"]
            if internship["skill_match_percentage"] is not None
            else -1,
        ),
        reverse=True,
    )

    return results


def render():
    # Only logged-in students can browse internships.
    user = require_role("student")
    student_id = user["user_id"]

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

    # Remember the search filters after submission.
    if "internship_filters" not in st.session_state:
        st.session_state["internship_filters"] = {
            "title": "",
            "location": "",
            "work_mode": "All",
            "min_stipend": 0,
        }

    if search_clicked:
        st.session_state["internship_filters"] = {
            "title": title,
            "location": location,
            "work_mode": work_mode,
            "min_stipend": min_stipend,
        }

    filters = st.session_state["internship_filters"]

    # Retrieve internships and skill data.
    try:
        if any(
            [
                filters["title"].strip(),
                filters["location"].strip(),
                filters["min_stipend"] > 0,
                filters["work_mode"] != "All",
            ]
        ):
            internships = search_internships(
                title=filters["title"],
                location=filters["location"],
                min_stipend=(
                    filters["min_stipend"]
                    if filters["min_stipend"] > 0
                    else None
                ),
                work_mode=(
                    filters["work_mode"].lower()
                    if filters["work_mode"] != "All"
                    else ""
                ),
            )
        else:
            internships = get_all_internships()

        student_skills = get_student_skills(student_id)
        internship_skills = get_internship_skills()

    except Exception as e:
        st.error("Unable to load internships or skill information.")
        st.exception(e)
        return

    if internships is None or internships.empty:
        st.info(
            "No internships match your search. "
            "Try changing your filters."
        )

        if st.button("Clear Search"):
            st.session_state["internship_filters"] = {
                "title": "",
                "location": "",
                "work_mode": "All",
                "min_stipend": 0,
            }
            st.rerun()

        return

    # Calculate skill matches and sort the results.
    ranked_internships = calculate_skill_matches(
        internships,
        student_skills,
        internship_skills,
    )

    # Results summary.
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Available Opportunities")

    with col2:
        st.metric(
            "Internships Found",
            len(ranked_internships),
        )

    st.caption(
        "Internships are ranked by how closely their required skills "
        "match your profile."
    )

    if student_skills is None or student_skills.empty:
        st.info(
            "You haven't added any skills to your profile yet. "
            "Add your skills to get personalized internship matches."
        )

    # Display internship cards.
    for internship in ranked_internships:
        internship_id = int(internship["internship_id"])

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {internship['title']}")

                st.markdown(
                    f"**🏢 {internship['company_name']}**"
                )

                description = internship.get("description")

                if not is_missing(description):
                    description = str(description).strip()

                    if description:
                        if len(description) > 300:
                            description = (
                                description[:300].rstrip() + "..."
                            )

                        st.write(description)

            with col2:
                st.markdown(
                    f"### {format_stipend(internship.get('stipend_monthly'))}"
                )

                match_percentage = internship[
                    "skill_match_percentage"
                ]

                if match_percentage is None:
                    st.info("🎯 Skills not specified")
                else:
                    st.metric(
                        "🎯 Skill Match",
                        f"{match_percentage}%",
                    )

                location_value = internship.get("location")

                if is_missing(location_value) or not str(
                    location_value
                ).strip():
                    location_value = "Not specified"

                st.caption(f"📍 {location_value}")

                mode = internship.get("work_mode")

                if not is_missing(mode):
                    st.caption(
                        f"🏠 {str(mode).replace('_', ' ').title()}"
                    )

            st.markdown("---")

            col1, col2, col3 = st.columns(3)

            with col1:
                duration = internship.get("duration_months")

                if is_missing(duration):
                    st.caption("⏳ Duration: Not specified")
                else:
                    st.caption(f"⏳ Duration: {duration} months")

            with col2:
                openings = internship.get("openings")

                if is_missing(openings):
                    st.caption("👥 Openings: Not specified")
                else:
                    st.caption(f"👥 Openings: {openings}")

            with col3:
                st.caption(
                    f"📅 Deadline: "
                    f"{format_deadline(internship.get('deadline'))}"
                )

            # Internship details.
            with st.expander("🔍 View Details"):
                st.markdown("#### Internship Description")

                full_description = internship.get("description")

                if is_missing(full_description) or not str(
                    full_description
                ).strip():
                    st.write("No description provided.")
                else:
                    st.write(full_description)

                st.markdown("#### Required Skills")

                required_skills = internship["required_skills"]
                matched_skills = internship["matched_skills"]
                missing_skills = internship["missing_skills"]

                if not required_skills:
                    st.info(
                        "The recruiter hasn't specified required skills "
                        "for this internship."
                    )
                else:
                    st.write(", ".join(required_skills))

                    st.markdown("#### ✅ Skills You Have")

                    if matched_skills:
                        st.success(", ".join(matched_skills))
                    else:
                        st.write(
                            "None of the required skills match "
                            "your current profile."
                        )

                    st.markdown("#### 📚 Skills You Could Learn")

                    if missing_skills:
                        st.write(", ".join(missing_skills))
                    else:
                        st.success(
                            "You have all the skills listed "
                            "for this internship!"
                        )

                st.markdown("#### Additional Information")

                st.write(
                    f"**Monthly Stipend:** "
                    f"{format_stipend(internship.get('stipend_monthly'))}"
                )

                st.write(
                    f"**Duration:** "
                    f"{internship.get('duration_months') or 'Not specified'}"
                    f" months"
                )

                st.write(
                    f"**Location:** "
                    f"{internship.get('location') or 'Not specified'}"
                )

                st.write(
                    f"**Work Mode:** "
                    f"{internship.get('work_mode') or 'Not specified'}"
                )

                st.write(
                    f"**Application Deadline:** "
                    f"{format_deadline(internship.get('deadline'))}"
                )

            # Application form.
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