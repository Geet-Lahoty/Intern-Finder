import streamlit as st

@st.cache_resource
def get_connection():
    return st.connection("neon", type="sql")


def run_query(query, params=None):
    conn = get_connection()

    return conn.query(
        query,
        params=params or {},
        ttl=0
    )