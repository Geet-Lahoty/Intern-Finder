"""Recruiter-side tests: ownership, constraints, transitions, trigger history.
Run from the project root:  python -m pytest tests/test_recruiter.py -v"""
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import recruiter_queries as rq
from database.seed import hash_password
from services import recruiter_service as svc
from services.auth_service import verify_password


# ---------- helpers ----------

def valid_data(**overrides):
    data = {
        "title": "Pytest Intern",
        "description": "Created by an automated test.",
        "location": "Remote",
        "work_mode": "remote",
        "stipend_monthly": 1000.0,
        "duration_months": 3,
        "openings": 1,
        "deadline": date.today() + timedelta(days=30),
    }
    data.update(overrides)
    return data


def make_internship(recruiter_id, publish=True, **overrides):
    return svc.create_internship(recruiter_id, valid_data(**overrides), [], publish)


def make_application(engine, world, internship_id):
    """Inserts a pending application the way the student side does:
    status_changed_by = the student."""
    with engine.begin() as c:
        return c.execute(
            text("""
                INSERT INTO applications
                    (internship_id, student_id, status, status_changed_by)
                VALUES (:i, :s, 'pending', :s)
                RETURNING application_id
            """),
            {"i": internship_id, "s": world["student"]},
        ).scalar_one()


def scalar(engine, sql, **params):
    with engine.connect() as c:
        return c.execute(text(sql), params).scalar()


def history_rows(engine, application_id):
    with engine.connect() as c:
        return c.execute(
            text("""
                SELECT old_status, new_status, changed_by
                FROM application_status_history
                WHERE application_id = :a
                ORDER BY history_id
            """),
            {"a": application_id},
        ).all()


# ---------- password verification (no database needed) ----------

def test_verify_password_accepts_correct_and_rejects_wrong():
    stored = hash_password("DemoPass123!")
    assert verify_password("DemoPass123!", stored) is True
    assert verify_password("wrong", stored) is False


def test_verify_password_rejects_malformed_hash():
    assert verify_password("anything", "not-a-valid-hash") is False


# ---------- creating internships ----------

def test_create_published_internship_is_owned_and_open(engine, world):
    iid = make_internship(world["a"], publish=True)
    assert scalar(engine, "SELECT posted_by FROM internships WHERE internship_id=:i", i=iid) == world["a"]
    assert scalar(engine, "SELECT status FROM internships WHERE internship_id=:i", i=iid) == "open"
    assert scalar(engine, "SELECT company_id FROM internships WHERE internship_id=:i", i=iid) == world["company"]


def test_create_unpublished_internship_is_draft(engine, world):
    iid = make_internship(world["a"], publish=False)
    assert scalar(engine, "SELECT status FROM internships WHERE internship_id=:i", i=iid) == "draft"


def test_create_rejects_zero_openings(world):
    with pytest.raises(svc.ServiceError):
        make_internship(world["a"], openings=0)


def test_create_rejects_past_deadline(world):
    with pytest.raises(svc.ServiceError):
        make_internship(world["a"], deadline=date.today() - timedelta(days=1))


def test_create_rejects_blank_title(world):
    with pytest.raises(svc.ServiceError):
        make_internship(world["a"], title="   ")


def test_database_check_constraint_is_the_last_line_of_defence(engine, world):
    """Bypass the service entirely: the schema itself must reject bad data."""
    with pytest.raises(IntegrityError, match="internships_openings_positive"):
        with engine.begin() as c:
            c.execute(
                text("""
                    INSERT INTO internships
                        (company_id, posted_by, title, description, work_mode,
                         duration_months, openings)
                    VALUES (:c, :p, 't', 'd', 'remote', 3, 0)
                """),
                {"c": world["company"], "p": world["a"]},
            )


# ---------- ownership of internships ----------

def test_other_recruiter_cannot_edit_internship(engine, world):
    iid = make_internship(world["a"], title="Original title")
    with pytest.raises(svc.ServiceError):
        svc.update_internship(world["b"], iid, valid_data(title="Hacked"), [])
    assert scalar(engine, "SELECT title FROM internships WHERE internship_id=:i", i=iid) == "Original title"


def test_other_recruiter_cannot_change_internship_status(engine, world):
    iid = make_internship(world["a"])
    with pytest.raises(svc.ServiceError):
        svc.change_internship_status(world["b"], iid, "closed")
    assert scalar(engine, "SELECT status FROM internships WHERE internship_id=:i", i=iid) == "open"


def test_owner_can_edit_internship(engine, world):
    iid = make_internship(world["a"])
    svc.update_internship(world["a"], iid, valid_data(title="New title"), [])
    assert scalar(engine, "SELECT title FROM internships WHERE internship_id=:i", i=iid) == "New title"


def test_recruiter_lists_only_own_internships(world):
    iid_a = make_internship(world["a"])
    make_internship(world["b"])
    listed = rq.get_recruiter_internships(world["a"])
    assert listed["internship_id"].tolist() == [iid_a]
    assert rq.get_owned_internship(iid_a, world["b"]).empty


# ---------- internship status transitions ----------

def test_internship_valid_transition(engine, world):
    iid = make_internship(world["a"])
    svc.change_internship_status(world["a"], iid, "closed")
    assert scalar(engine, "SELECT status FROM internships WHERE internship_id=:i", i=iid) == "closed"


def test_internship_invalid_transition_is_rejected(world):
    iid = make_internship(world["a"])
    svc.change_internship_status(world["a"], iid, "cancelled")
    with pytest.raises(svc.ServiceError):          # cancelled is final
        svc.change_internship_status(world["a"], iid, "open")


def test_cancelled_internship_cannot_be_edited(world):
    iid = make_internship(world["a"])
    svc.change_internship_status(world["a"], iid, "cancelled")
    with pytest.raises(svc.ServiceError):
        svc.update_internship(world["a"], iid, valid_data(title="Late edit"), [])


# ---------- dashboard aggregates ----------

def test_dashboard_stats_match_data(engine, world):
    open_id = make_internship(world["a"], publish=True)
    make_internship(world["a"], publish=False)       # draft
    make_application(engine, world, open_id)         # pending

    s = rq.get_dashboard_stats(world["a"]).iloc[0]
    assert int(s["total_internships"]) == 2
    assert int(s["open_internships"]) == 1
    assert int(s["total_applications"]) == 1
    assert int(s["awaiting_review"]) == 1

    empty = rq.get_dashboard_stats(world["b"]).iloc[0]
    assert int(empty["total_internships"]) == 0
    assert int(empty["total_applications"]) == 0


# ---------- applications: visibility ----------

def test_applications_visible_only_to_owner(engine, world):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)

    assert rq.get_recruiter_applications(world["a"])["application_id"].tolist() == [app_id]
    assert rq.get_recruiter_applications(world["b"]).empty
    assert not rq.get_application_detail(app_id, world["a"]).empty
    assert rq.get_application_detail(app_id, world["b"]).empty
    assert rq.get_application_history(app_id, world["b"]).empty


def test_application_filters(engine, world):
    iid = make_internship(world["a"])
    make_application(engine, world, iid)

    assert len(rq.get_recruiter_applications(world["a"], internship_id=iid, status="pending")) == 1
    assert rq.get_recruiter_applications(world["a"], status="accepted").empty
    with pytest.raises(ValueError):
        rq.get_recruiter_applications(world["a"], status="not-a-status")


def test_duplicate_application_is_rejected_by_unique_constraint(engine, world):
    iid = make_internship(world["a"])
    make_application(engine, world, iid)
    with pytest.raises(IntegrityError, match="applications_student_internship_uq"):
        make_application(engine, world, iid)


# ---------- reviewing applications: ownership, transitions, trigger ----------

def test_trigger_logs_application_insert(engine, world):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)
    assert history_rows(engine, app_id) == [(None, "pending", world["student"])]


def test_recruiter_status_change_is_logged_with_recruiter_as_actor(engine, world):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)

    svc.change_application_status(world["a"], app_id, "shortlisted")

    assert scalar(engine, "SELECT status FROM applications WHERE application_id=:a", a=app_id) == "shortlisted"
    assert history_rows(engine, app_id) == [
        (None, "pending", world["student"]),
        ("pending", "shortlisted", world["a"]),
    ]


def test_other_recruiter_cannot_review_application(engine, world):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)

    with pytest.raises(svc.ServiceError):
        svc.change_application_status(world["b"], app_id, "accepted")

    assert scalar(engine, "SELECT status FROM applications WHERE application_id=:a", a=app_id) == "pending"
    assert len(history_rows(engine, app_id)) == 1    # nothing new logged


@pytest.mark.parametrize("bad_target", ["pending", "withdrawn", "banana"])
def test_recruiter_cannot_set_disallowed_status(engine, world, bad_target):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)
    with pytest.raises(svc.ServiceError):
        svc.change_application_status(world["a"], app_id, bad_target)


def test_final_status_cannot_be_changed_again(engine, world):
    """Simulates the stale-page case: a second decision after the first one."""
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)

    svc.change_application_status(world["a"], app_id, "accepted")
    with pytest.raises(svc.ServiceError):
        svc.change_application_status(world["a"], app_id, "rejected")

    assert scalar(engine, "SELECT status FROM applications WHERE application_id=:a", a=app_id) == "accepted"
    assert len(history_rows(engine, app_id)) == 2    # insert + one change only


def test_shortlisted_can_then_be_accepted(engine, world):
    iid = make_internship(world["a"])
    app_id = make_application(engine, world, iid)
    svc.change_application_status(world["a"], app_id, "shortlisted")
    svc.change_application_status(world["a"], app_id, "accepted")
    assert [r[1] for r in history_rows(engine, app_id)] == ["pending", "shortlisted", "accepted"]
