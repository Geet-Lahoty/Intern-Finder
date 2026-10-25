import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from database.queries import (get_all_internships, search_internships)

st.title("Testing Query Functions")

st.subheader("TEST 1: all internship")

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

st.divider()

st.subheader("Test 2: Search and Filter Internships")

with st.form("search_form"):
    title = st.text_input("Title contains", placeholder="Python")
    location = st.text_input("Location contains", placeholder="Pune")

    work_mode = st.selectbox(
        "Work mode",
        ["Any", "remote", "hybrid", "on_site"],
    )

    min_stipend = st.number_input(
        "Minimum monthly stipend (₹)",
        min_value=0,
        value=0,
        step=1000,
    )

    search_clicked = st.form_submit_button("Search")

if search_clicked:
    try:
        results = search_internships(
            title=title,
            location=location,
            min_stipend=min_stipend if min_stipend > 0 else None,
            work_mode="" if work_mode == "Any" else work_mode,
        )

        st.success(f"Found {len(results)} matching internships.")

        if results.empty:
            st.info("No matching internships found.")
        else:
            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    except Exception as e:
        st.error("Search failed.")
        st.exception(e)

