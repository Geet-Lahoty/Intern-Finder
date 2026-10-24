import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from database.queries import get_all_internships

st.title("Testing Query Functions")

if st.button("Run get_all_internships"):
    try:
        intenships = get_all_internships()

        st.success("Fetched")

        if intenships.empty:
            st.info("The query works but the intenship table is empty")
        else:
            st.subheader("Query result")
            st.dataframe(
                intenships,
                width="stretch",
                hide_index=True,
            )

            st.subheader("Column info")
            st.write(list(intenships.columns))

    except Exception as error:
        st.error("Query failed")
        st.exception(error)