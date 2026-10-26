"""Shared authentication helpers (student and recruiter).
The login and registration forms live in app_pages/common/login.py and app_pages/common/register.py."""
import hashlib
import hmac
import re
import secrets
from typing import Optional

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.connection import get_connection, run_query

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthError(Exception):
    """User-correctable authentication and registration exception."""
    pass


def hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 600_000) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 matching verify_password."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest}"


def get_all_companies():
    """Retrieve list of existing companies ordered by name."""
    return run_query(
        """
        SELECT company_id, name, industry, city
        FROM companies
        ORDER BY name ASC
        """
    )


def register_user(
    *,
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    role: str,
    # Student profile fields (optional)
    university: Optional[str] = None,
    degree: Optional[str] = None,
    graduation_year: Optional[int] = None,
    cgpa: Optional[float] = None,
    city: Optional[str] = None,
    phone: Optional[str] = None,
    # Recruiter profile fields (optional)
    job_title: Optional[str] = None,
    company_id: Optional[int] = None,
    new_company_name: Optional[str] = None,
    new_company_industry: Optional[str] = None,
    new_company_city: Optional[str] = None,
    new_company_website: Optional[str] = None,
) -> dict:
    """Register a new user (student or recruiter) and create their initial profile in a single transaction."""
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()

    # Core validation
    if not full_name:
        raise AuthError("Full name is required.")
    if len(full_name) > 120:
        raise AuthError("Full name must be 120 characters or fewer.")

    if not email:
        raise AuthError("Email address is required.")
    if len(email) > 254:
        raise AuthError("Email address must be 254 characters or fewer.")
    if not EMAIL_REGEX.match(email):
        raise AuthError("Please enter a valid email address (e.g. name@example.com).")

    if not password or len(password) < 6:
        raise AuthError("Password must be at least 6 characters long.")
    if password != confirm_password:
        raise AuthError("Passwords do not match.")

    if role not in ("student", "recruiter"):
        raise AuthError("Invalid role. Must be 'student' or 'recruiter'.")

    # Check for existing email
    existing = run_query(
        "SELECT user_id FROM users WHERE LOWER(email) = LOWER(:email)",
        {"email": email},
    )
    if not existing.empty:
        raise AuthError(f"An account with email '{email}' already exists. Please log in.")

    # Student validations
    grad_yr_val = None
    cgpa_val = None
    uni_val = None
    degree_val = None
    city_val = None
    phone_val = None

    if role == "student":
        if graduation_year is not None and str(graduation_year).strip() != "":
            try:
                grad_yr_val = int(graduation_year)
                if not (2000 <= grad_yr_val <= 2100):
                    raise AuthError("Graduation year must be between 2000 and 2100.")
            except ValueError:
                raise AuthError("Graduation year must be a valid 4-digit number.")

        if cgpa is not None and str(cgpa).strip() != "":
            try:
                cgpa_val = float(cgpa)
                if not (0.0 <= cgpa_val <= 10.0):
                    raise AuthError("CGPA must be between 0.0 and 10.0.")
            except ValueError:
                raise AuthError("CGPA must be a valid number between 0 and 10.")

        uni_val = (university or "").strip() or None
        if uni_val and len(uni_val) > 180:
            raise AuthError("University name must be 180 characters or fewer.")

        degree_val = (degree or "").strip() or None
        if degree_val and len(degree_val) > 120:
            raise AuthError("Degree name must be 120 characters or fewer.")

        city_val = (city or "").strip() or None
        if city_val and len(city_val) > 100:
            raise AuthError("City must be 100 characters or fewer.")

        phone_val = (phone or "").strip() or None
        if phone_val and len(phone_val) > 30:
            raise AuthError("Phone number must be 30 characters or fewer.")

    # Recruiter validations
    title_val = None
    target_company_id = company_id
    new_comp = (new_company_name or "").strip()

    if role == "recruiter":
        title_val = (job_title or "").strip() or None
        if title_val and len(title_val) > 120:
            raise AuthError("Job title must be 120 characters or fewer.")

        if new_comp and len(new_comp) > 160:
            raise AuthError("Company name must be 160 characters or fewer.")

    # Transaction: Create user and profile
    conn = get_connection()
    with conn.session as session:
        try:
            # Handle new company insertion if requested
            if role == "recruiter" and new_comp:
                c_row = session.execute(
                    text("SELECT company_id FROM companies WHERE LOWER(name) = LOWER(:name)"),
                    {"name": new_comp},
                ).first()
                if c_row:
                    target_company_id = c_row[0]
                else:
                    c_res = session.execute(
                        text("""
                            INSERT INTO companies (name, industry, city, website)
                            VALUES (:name, :industry, :city, :website)
                            RETURNING company_id
                        """),
                        {
                            "name": new_comp,
                            "industry": (new_company_industry or "").strip() or None,
                            "city": (new_company_city or "").strip() or None,
                            "website": (new_company_website or "").strip() or None,
                        },
                    )
                    target_company_id = c_res.scalar_one()

            # Insert users table entry
            pw_hash = hash_password(password)
            u_res = session.execute(
                text("""
                    INSERT INTO users (full_name, email, password_hash, role, is_active)
                    VALUES (:full_name, :email, :password_hash, :role, TRUE)
                    RETURNING user_id
                """),
                {
                    "full_name": full_name,
                    "email": email,
                    "password_hash": pw_hash,
                    "role": role,
                },
            )
            user_id = int(u_res.scalar_one())

            # Insert associated profile
            if role == "student":
                session.execute(
                    text("""
                        INSERT INTO student_profiles (
                            student_id, university, degree, graduation_year, cgpa, city, phone
                        )
                        VALUES (
                            :student_id, :university, :degree, :graduation_year, :cgpa, :city, :phone
                        )
                    """),
                    {
                        "student_id": user_id,
                        "university": uni_val,
                        "degree": degree_val,
                        "graduation_year": grad_yr_val,
                        "cgpa": cgpa_val,
                        "city": city_val,
                        "phone": phone_val,
                    },
                )
            elif role == "recruiter":
                session.execute(
                    text("""
                        INSERT INTO recruiter_profiles (
                            recruiter_id, company_id, job_title
                        )
                        VALUES (
                            :recruiter_id, :company_id, :job_title
                        )
                    """),
                    {
                        "recruiter_id": user_id,
                        "company_id": int(target_company_id) if target_company_id else None,
                        "job_title": title_val,
                    },
                )

            session.commit()
            return {
                "user_id": user_id,
                "full_name": full_name,
                "email": email,
                "role": role,
            }
        except IntegrityError as e:
            session.rollback()
            err_msg = str(e.orig).lower()
            if "users_email_lower_uq" in err_msg or "unique" in err_msg:
                raise AuthError("This email address is already registered.")
            raise AuthError(f"Database constraint error: {e.orig}")
        except Exception:
            session.rollback()
            raise


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