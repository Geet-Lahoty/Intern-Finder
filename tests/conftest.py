"""Pytest setup: points the recruiter code at the Neon TEST BRANCH, never at main.

The app code uses st.connection(...). Here we replace it with a plain SQLAlchemy
engine built from [connections.neon_test] in .streamlit/secrets.toml
(or the TEST_DATABASE_URL environment variable)."""
import os
import tomllib
import uuid
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent


def _read_secrets() -> dict:
    path = ROOT / ".streamlit" / "secrets.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _strip(url):
    return url.split("?")[0] if url else url


@pytest.fixture(scope="session")
def engine():
    secrets = _read_secrets().get("connections", {})
    test_url = os.environ.get("TEST_DATABASE_URL") or secrets.get("neon_test", {}).get("url")
    main_url = secrets.get("neon", {}).get("url")

    if not test_url:
        pytest.exit(
            "No test database configured. Add [connections.neon_test] to "
            ".streamlit/secrets.toml (a Neon BRANCH) or set TEST_DATABASE_URL.",
            returncode=2,
        )
    if main_url and _strip(test_url) == _strip(main_url):
        pytest.exit("neon_test points at the SAME database as neon. Use a separate branch.",
                    returncode=2)

    eng = create_engine(test_url, pool_pre_ping=True)
    yield eng
    eng.dispose()


class _FakeConnection:
    """Mimics the two things the app uses from st.connection: .session and .query."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def session(self):
        return Session(self.engine)

    def query(self, sql, params=None, ttl=None):
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})


@pytest.fixture(autouse=True)
def use_test_database(engine, monkeypatch):
    """Redirect every database call in the recruiter code to the test branch."""
    fake = _FakeConnection(engine)

    def fake_run_query(query, params=None):
        return fake.query(query, params)

    # These modules did `from database.connection import run_query / get_connection`,
    # so each module's own name must be patched.
    monkeypatch.setattr("database.recruiter_queries.run_query", fake_run_query)
    monkeypatch.setattr("services.auth_service.run_query", fake_run_query)
    monkeypatch.setattr("services.recruiter_service.get_connection", lambda: fake)


@pytest.fixture
def world(engine):
    """Creates an isolated company, recruiters A and B, and one student.
    Everything is deleted again after the test."""
    tag = uuid.uuid4().hex[:8]
    ids = {}

    with engine.begin() as c:
        ids["company"] = c.execute(
            text("INSERT INTO companies (name) VALUES (:n) RETURNING company_id"),
            {"n": f"PytestCo {tag}"},
        ).scalar_one()

        for key, role in (("a", "recruiter"), ("b", "recruiter"), ("student", "student")):
            ids[key] = c.execute(
                text("""
                    INSERT INTO users (full_name, email, password_hash, role)
                    VALUES (:name, :email, 'x', :role)
                    RETURNING user_id
                """),
                {"name": f"Pytest {key} {tag}",
                 "email": f"pytest_{key}_{tag}@test.local", "role": role},
            ).scalar_one()

        for key in ("a", "b"):
            c.execute(
                text("""
                    INSERT INTO recruiter_profiles (recruiter_id, company_id, job_title)
                    VALUES (:r, :c, 'Tester')
                """),
                {"r": ids[key], "c": ids["company"]},
            )
        c.execute(text("INSERT INTO student_profiles (student_id) VALUES (:s)"),
                  {"s": ids["student"]})

    yield ids

    # Teardown order matters because of ON DELETE RESTRICT:
    # applications (history cascades) -> internships -> users -> company.
    with engine.begin() as c:
        c.execute(text("DELETE FROM applications WHERE student_id = :s"), {"s": ids["student"]})
        c.execute(text("DELETE FROM internships WHERE company_id = :c"), {"c": ids["company"]})
        c.execute(text("DELETE FROM users WHERE user_id IN (:a, :b, :s)"),
                  {"a": ids["a"], "b": ids["b"], "s": ids["student"]})
        c.execute(text("DELETE FROM companies WHERE company_id = :c"), {"c": ids["company"]})