"""Shared authentication helpers (student and recruiter).
The login FORM lives in app_pages/common/login.py."""
import hashlib
import hmac

import streamlit as st

from database.connection import run_query


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against 'pbkdf2_sha256$iters$salt$digest' (see database/seed.py)."""
    try:
        scheme, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, AttributeError):
        return False


def authenticate(email: str, password: str):
    """Return a user dict if credentials are valid and the account is active, else None."""
    if not email.strip() or not password:
        return None

    df = run_query(
        """
        SELECT user_id, full_name, email, password_hash, role, is_active
        FROM users
        WHERE LOWER(email) = LOWER(:email)
        """,
        {"email": email.strip()},
    )
    if df.empty:
        return None

    row = df.iloc[0]
    if not bool(row["is_active"]):
        return None
    if not verify_password(password, row["password_hash"]):
        return None

    return {
        "user_id": int(row["user_id"]),
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
    }


# Session helpers (the shared contract: st.session_state["user"])

def get_current_user():
    return st.session_state.get("user")


def login_user(user: dict) -> None:
    st.session_state["user"] = user


def logout_user() -> None:
    st.session_state.pop("user", None)


def require_role(role: str) -> dict:
    """Guard for every page: stops the page unless the logged-in user has `role`.
    Returns {user_id, full_name, email, role}."""
    user = get_current_user()
    if user is None:
        st.warning("Please log in first.")
        st.stop()
    if user["role"] != role:
        st.error(f"This page is only available to {role} accounts.")
        st.stop()
    return user