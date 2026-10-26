import streamlit as st

from services.auth_service import authenticate, login_user


def render():
    st.title("Internship Finder 🎓")
    st.subheader("Log in")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        user = authenticate(email, password)
        if user is None:
            st.error("Invalid email or password.")
        else:
            login_user(user)
            st.rerun()

    st.divider()
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write("Don't have an account yet?")
    with col2:
        reg_page = st.session_state.get("_nav_register_page")
        if reg_page:
            st.page_link(reg_page, label="Create an account ✨", icon="📝")