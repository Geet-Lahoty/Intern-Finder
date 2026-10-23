import streamlit as st
from database.connection import get_connection

st.title("Database Test")

try:
    conn = get_connection()

    result = conn.query(
        "SELECT current_database() AS database_name, "
        "current_user AS connected_user",
        ttl=0
    )

    st.success("Connected to database")
    st.dataframe(result, width="stretch")

    tables = conn.query(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        ttl=0,
    )

    st.subheader("Tables found")
    st.dataframe(tables, width="stretch")

except Exception as error:
    st.error("Failed to connect")
    st.exception(error)