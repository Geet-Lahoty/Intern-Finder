import streamlit as st

from app_pages.common import login, register
from app_pages.student import (dashboard as student_dashboard, profile as student_profile, 
                               browse_internships, my_applications, my_skills, my_projects)
from app_pages.recruiter import dashboard, manage_internships, applications
from services.auth_service import get_current_user, logout_user

st.set_page_config(page_title="Internship Finder", page_icon="🎓", layout="wide")


def student_placeholder():
    # TEAMMATE: replace with st.Page(...) entries pointing at app_pages/student/*.py
    st.title("Student area")
    st.info("Student pages are being built.")
    


user = get_current_user()

if user is None:
    login_page = st.Page(login.render, title="Log in", icon="🔐", url_path="login", default=True)
    register_page = st.Page(register.render, title="Register", icon="✨", url_path="register")
    st.session_state["_nav_login_page"] = login_page
    st.session_state["_nav_register_page"] = register_page
    pages = [login_page, register_page]

elif user["role"] == "recruiter":
    pages = {
        "Recruiter": [
            st.Page(dashboard.render, title="Dashboard",
                    url_path="recruiter-dashboard", default=True),
            st.Page(manage_internships.render, title="Manage Internships",
                    url_path="recruiter-internships"),
            st.Page(applications.render, title="Applications",
                    url_path="recruiter-applications"),
        ]
    }

else:  # student
    pages = {
        "Student": [
            st.Page(
                student_dashboard.render,
                title="Dashboard",
                url_path="student-dashboard",
                default=True,
            ),
            st.Page(
                student_profile.render,
                title="My Profile",
                url_path="student-profile",
            ),
            st.Page(
                browse_internships.render,
                title="Browse Internships",
                url_path="browse-internships",
            ),
            st.Page(
                my_applications.render,
                title="My Applications",
                url_path="my-applications",
            ),
            st.Page(
                my_skills.render,
                title="My skills",
                url_path="my-skills"
            ),
            st.Page(
                my_projects.render,
                title="My Projects",
                url_path="my-projects",
            ),
        ]
    }

if user is not None:
    st.sidebar.write(f"Signed in as **{user['full_name']}** ({user['role']})")
    if st.sidebar.button("Log out"):
        logout_user()
        st.rerun()

st.navigation(pages).run()