import streamlit as st

st.title("Internship Finder 🎓")
st.write("Find internships and kick-start your career.")
name = st.text_input("Enter Your Name", placeholder="Your name...")

if st.button("Create Profile!"):
    if not name:
        st.error("Write Valid Name")
    else:
        st.success("Profile created")    
        st.write("You are Mr./Mrs ", name)
