import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from database.seed import seed_database

st.title("Seed Database")
st.warning(
    "This inserts fictional demo records into your Neon database. "
    "Existing records are not intentionally deleted."
)

if st.button("Insert Seed Data", type="primary"):
    try:
        with st.spinner("Inserting sample records..."):
            seed_database()

        st.success("Seed data inserted successfully!")
        st.info("You can now test your internship queries.")

    except Exception as e:
        st.error("Seeding failed. The transaction was rolled back.")
        st.exception(e)
