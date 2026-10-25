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