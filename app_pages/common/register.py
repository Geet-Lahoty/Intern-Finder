import streamlit as st

from services.auth_service import (
    AuthError,
    get_all_companies,
    login_user,
    register_user,
)


def render():
    st.title("Join Internship Finder 🎓")
    st.markdown(
        "Create an account to start applying for curated internships "
        "or post openings to discover talented candidates."
    )

    role_choice = st.radio(
        "I want to register as:",
        options=["🎓 Student", "💼 Recruiter"],
        index=0,
        horizontal=True,
    )
    is_student = "Student" in role_choice
    selected_role = "student" if is_student else "recruiter"

    st.divider()

    with st.form("register_form", clear_on_submit=False):
        st.subheader("1. Account Credentials")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *", placeholder="e.g. Jane Doe")
            password = st.text_input(
                "Password * (min. 6 characters)",
                type="password",
                placeholder="Choose a strong password",
            )

        with col2:
            email = st.text_input("Email Address *", placeholder="e.g. jane@example.com")
            confirm_password = st.text_input(
                "Confirm Password *",
                type="password",
                placeholder="Re-enter your password",
            )

        # Role-specific fields
        if is_student:
            st.subheader("2. Academic & Contact Details (Optional)")
            st.caption("You can fill these now or update them anytime from your Profile page.")

            sc1, sc2 = st.columns(2)
            with sc1:
                university = st.text_input("University / College", placeholder="e.g. Stanford University")
                degree = st.text_input("Degree / Major", placeholder="e.g. B.S. Computer Science")
                city = st.text_input("City", placeholder="e.g. San Francisco")

            with sc2:
                grad_year = st.number_input(
                    "Expected Graduation Year",
                    min_value=2000,
                    max_value=2100,
                    value=2026,
                    step=1,
                )
                cgpa = st.number_input(
                    "CGPA (out of 10.0)",
                    min_value=0.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.1,
                    format="%.2f",
                )
                phone = st.text_input("Phone Number", placeholder="e.g. +1 555-0199")

            # Reset recruiter specific variables
            job_title = None
            company_id = None
            new_company_name = None
            new_company_industry = None
            new_company_city = None
            new_company_website = None

        else:  # Recruiter
            st.subheader("2. Recruiter & Company Details")
            job_title = st.text_input("Your Job Title", placeholder="e.g. Talent Acquisition Lead / HR")

            # Fetch existing companies
            companies_df = get_all_companies()
            company_options = {}
            if not companies_df.empty:
                for _, row in companies_df.iterrows():
                    company_options[int(row["company_id"])] = (
                        f"{row['name']} ({row['industry'] or 'Company'})"
                    )

            company_options_list = ["➕ Add a new company..."] + [
                f"{cid}: {cname}" for cid, cname in company_options.items()
            ]

            selected_company_option = st.selectbox(
                "Associated Company",
                options=company_options_list,
                index=0,
                help="Select your company or add a new one to immediately post internships.",
            )

            if selected_company_option == "➕ Add a new company...":
                st.markdown("**New Company Information**")
                nc1, nc2 = st.columns(2)
                with nc1:
                    new_company_name = st.text_input("Company Name *", placeholder="e.g. Acme Technologies")
                    new_company_industry = st.text_input("Industry", placeholder="e.g. Software, Fintech")
                with nc2:
                    new_company_city = st.text_input("Headquarters City", placeholder="e.g. New York")
                    new_company_website = st.text_input("Website URL", placeholder="e.g. https://acme.com")
                company_id = None
            else:
                company_id = int(selected_company_option.split(":")[0])
                new_company_name = None
                new_company_industry = None
                new_company_city = None
                new_company_website = None

            # Reset student specific variables
            university = None
            degree = None
            grad_year = None
            cgpa = None
            city = None
            phone = None

        st.markdown("<br>", unsafe_allow_html=True)
        btn_label = "Create Student Account 🚀" if is_student else "Create Recruiter Account 🚀"
        submitted = st.form_submit_button(btn_label, use_container_width=True)

    if submitted:
        try:
            user = register_user(
                full_name=full_name,
                email=email,
                password=password,
                confirm_password=confirm_password,
                role=selected_role,
                university=university if is_student else None,
                degree=degree if is_student else None,
                graduation_year=int(grad_year) if (is_student and grad_year) else None,
                cgpa=float(cgpa) if (is_student and cgpa and cgpa > 0) else None,
                city=city if is_student else None,
                phone=phone if is_student else None,
                job_title=job_title if not is_student else None,
                company_id=company_id if not is_student else None,
                new_company_name=new_company_name if not is_student else None,
                new_company_industry=new_company_industry if not is_student else None,
                new_company_city=new_company_city if not is_student else None,
                new_company_website=new_company_website if not is_student else None,
            )

            st.success(f"🎉 Welcome aboard, {user['full_name']}! Your account has been created.")
            login_user(user)
            st.rerun()

        except AuthError as e:
            st.error(f"⚠️ {str(e)}")
        except Exception as e:
            st.error("An unexpected error occurred while creating your account. Please try again.")
            st.exception(e)

    st.divider()
    login_col1, login_col2 = st.columns([3, 2])
    with login_col1:
        st.write("Already have an account?")
    with login_col2:
        login_page = st.session_state.get("_nav_login_page")
        if login_page:
            st.page_link(login_page, label="Log in to your account", icon="🔐")
