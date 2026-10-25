"""All recruiter-side SQL. Every query is scoped by the recruiter's ID,
which must come from the authenticated session, never from a form field."""
from sqlalchemy import text

from database.connection import run_query


# ---------- READ (Step 1) ----------

def get_recruiter_profile(recruiter_id: int):
    return run_query(
        """
        SELECT u.user_id, u.full_name, rp.job_title,
               c.company_id, c.name AS company_name
        FROM users u
        JOIN recruiter_profiles rp ON rp.recruiter_id = u.user_id
        LEFT JOIN companies c ON c.company_id = rp.company_id
        WHERE u.user_id = :recruiter_id
          AND u.role = 'recruiter'
          AND u.is_active
        """,
        {"recruiter_id": recruiter_id},
    )


def get_dashboard_stats(recruiter_id: int):
    """One row of aggregates over this recruiter's internships and applications."""
    return run_query(
        """
        SELECT
            COUNT(DISTINCT i.internship_id) AS total_internships,
            COUNT(DISTINCT i.internship_id)
                FILTER (WHERE i.status = 'open') AS open_internships,
            COUNT(a.application_id) AS total_applications,
            COUNT(a.application_id)
                FILTER (WHERE a.status = 'pending') AS awaiting_review
        FROM internships i
        LEFT JOIN applications a ON a.internship_id = i.internship_id
        WHERE i.posted_by = :recruiter_id
        """,
        {"recruiter_id": recruiter_id},
    )


def get_recruiter_internships(recruiter_id: int):
    """This recruiter's internships with application counts."""
    return run_query(
        """
        SELECT i.internship_id,
               i.title,
               i.status,
               i.work_mode,
               i.location,
               i.openings,
               i.deadline,
               i.posted_at,
               COUNT(a.application_id) AS applications,
               COUNT(a.application_id)
                   FILTER (WHERE a.status = 'pending') AS pending
        FROM internships i
        LEFT JOIN applications a ON a.internship_id = i.internship_id
        WHERE i.posted_by = :recruiter_id
        GROUP BY i.internship_id
        ORDER BY i.posted_at DESC
        """,
        {"recruiter_id": recruiter_id},
    )


# ---------- READ (Step 2) ----------

def get_all_skills():
    return run_query(
        "SELECT skill_id, skill_name FROM skills ORDER BY skill_name"
    )


def get_owned_internship(internship_id: int, recruiter_id: int):
    """Returns the internship ONLY if it belongs to this recruiter (empty otherwise)."""
    return run_query(
        """
        SELECT internship_id, title, description, location, work_mode,
               stipend_monthly, duration_months, openings, deadline,
               status, posted_at
        FROM internships
        WHERE internship_id = :internship_id
          AND posted_by = :recruiter_id
        """,
        {"internship_id": internship_id, "recruiter_id": recruiter_id},
    )


def get_internship_skill_ids(internship_id: int):
    """Call only after ownership has been verified."""
    df = run_query(
        "SELECT skill_id FROM internship_skills WHERE internship_id = :internship_id",
        {"internship_id": internship_id},
    )
    return [int(x) for x in df["skill_id"].tolist()]


# ---------- WRITE (take a session; the service controls the transaction) ----------

def insert_internship(session, company_id: int, posted_by: int, d: dict) -> int:
    return session.execute(
        text("""
            INSERT INTO internships (
                company_id, posted_by, title, description, location,
                work_mode, stipend_monthly, duration_months, openings,
                deadline, status
            )
            VALUES (
                :company_id, :posted_by, :title, :description, :location,
                :work_mode, :stipend_monthly, :duration_months, :openings,
                :deadline, :status
            )
            RETURNING internship_id
        """),
        {"company_id": company_id, "posted_by": posted_by, **d},
    ).scalar_one()


def lock_owned_internship_status(session, internship_id: int, recruiter_id: int):
    """Locks the row (FOR UPDATE) and returns its status, or None if the
    internship does not exist or belongs to someone else."""
    return session.execute(
        text("""
            SELECT status
            FROM internships
            WHERE internship_id = :internship_id
              AND posted_by = :recruiter_id
            FOR UPDATE
        """),
        {"internship_id": internship_id, "recruiter_id": recruiter_id},
    ).scalar()


def update_internship_fields(session, internship_id: int, recruiter_id: int, d: dict) -> int:
    result = session.execute(
        text("""
            UPDATE internships
            SET title = :title,
                description = :description,
                location = :location,
                work_mode = :work_mode,
                stipend_monthly = :stipend_monthly,
                duration_months = :duration_months,
                openings = :openings,
                deadline = :deadline
            WHERE internship_id = :internship_id
              AND posted_by = :recruiter_id
        """),
        {"internship_id": internship_id, "recruiter_id": recruiter_id, **d},
    )
    return result.rowcount


def update_internship_status(session, internship_id: int, recruiter_id: int, new_status: str) -> int:
    result = session.execute(
        text("""
            UPDATE internships
            SET status = :new_status
            WHERE internship_id = :internship_id
              AND posted_by = :recruiter_id
        """),
        {"internship_id": internship_id, "recruiter_id": recruiter_id,
         "new_status": new_status},
    )
    return result.rowcount


def replace_internship_skills(session, internship_id: int, skill_ids: list) -> None:
    session.execute(
        text("DELETE FROM internship_skills WHERE internship_id = :internship_id"),
        {"internship_id": internship_id},
    )
    for skill_id in skill_ids:
        session.execute(
            text("""
                INSERT INTO internship_skills (internship_id, skill_id)
                VALUES (:internship_id, :skill_id)
            """),
            {"internship_id": internship_id, "skill_id": skill_id},
        )