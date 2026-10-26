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
        # ---------- READ (Step 3: applications) ----------

APPLICATION_STATUSES = ("pending", "shortlisted", "rejected", "accepted", "withdrawn")


def get_recruiter_applications(recruiter_id: int, internship_id=None, status=None):
    """Applications to THIS recruiter's internships (4-table JOIN).
    Filters are optional. Only the SQL fragments are concatenated; every
    value is a bound parameter."""
    if status is not None and status not in APPLICATION_STATUSES:
        raise ValueError("Invalid status filter.")

    query = """
        SELECT a.application_id,
               i.internship_id,
               i.title            AS internship_title,
               u.full_name        AS student_name,
               u.email            AS student_email,
               sp.university,
               sp.degree,
               sp.cgpa,
               a.status,
               a.applied_at,
               (SELECT COUNT(*)
                  FROM internship_skills r
                  JOIN student_skills ss
                    ON ss.skill_id = r.skill_id
                   AND ss.student_id = a.student_id
                 WHERE r.internship_id = a.internship_id) AS matched_skills,
               (SELECT COUNT(*)
                  FROM internship_skills r2
                 WHERE r2.internship_id = a.internship_id) AS required_skills
        FROM applications a
        JOIN internships i       ON i.internship_id = a.internship_id
        JOIN student_profiles sp ON sp.student_id   = a.student_id
        JOIN users u             ON u.user_id       = sp.student_id
        WHERE i.posted_by = :recruiter_id
    """
    params = {"recruiter_id": recruiter_id}

    if internship_id is not None:
        query += " AND i.internship_id = :internship_id"
        params["internship_id"] = internship_id
    if status is not None:
        query += " AND a.status = :status"
        params["status"] = status

    query += " ORDER BY a.applied_at DESC"
    return run_query(query, params)


def get_application_status_counts(recruiter_id: int):
    """Applications per status for this recruiter (GROUP BY)."""
    return run_query(
        """
        SELECT a.status, COUNT(*) AS total
        FROM applications a
        JOIN internships i ON i.internship_id = a.internship_id
        WHERE i.posted_by = :recruiter_id
        GROUP BY a.status
        ORDER BY a.status
        """,
        {"recruiter_id": recruiter_id},
    )


def get_application_detail(application_id: int, recruiter_id: int):
    """One application, returned ONLY if the internship belongs to this recruiter."""
    return run_query(
        """
        SELECT a.application_id, a.status, a.cover_note, a.applied_at,
               i.internship_id, i.title AS internship_title,
               u.full_name AS student_name, u.email AS student_email,
               sp.university, sp.degree, sp.graduation_year, sp.cgpa, sp.city,
               sp.phone, sp.github_url, sp.linkedin_url, sp.portfolio_url,
               sp.resume_url, sp.bio,
               (SELECT STRING_AGG(sk.skill_name || ' (' || ss.proficiency || ')',
                                  ', ' ORDER BY sk.skill_name)
                  FROM student_skills ss
                  JOIN skills sk ON sk.skill_id = ss.skill_id
                 WHERE ss.student_id = a.student_id) AS student_skills
        FROM applications a
        JOIN internships i       ON i.internship_id = a.internship_id
        JOIN student_profiles sp ON sp.student_id   = a.student_id
        JOIN users u             ON u.user_id       = sp.student_id
        WHERE a.application_id = :application_id
          AND i.posted_by = :recruiter_id
        """,
        {"application_id": application_id, "recruiter_id": recruiter_id},
    )


def get_application_history(application_id: int, recruiter_id: int):
    """Status history for an application, only if the recruiter owns the internship."""
    return run_query(
        """
        SELECT h.changed_at, h.old_status, h.new_status,
               u.full_name AS changed_by_name, u.role AS changed_by_role
        FROM application_status_history h
        JOIN applications a ON a.application_id = h.application_id
        JOIN internships i  ON i.internship_id  = a.internship_id
        JOIN users u        ON u.user_id        = h.changed_by
        WHERE h.application_id = :application_id
          AND i.posted_by = :recruiter_id
        ORDER BY h.changed_at DESC, h.history_id DESC
        """,
        {"application_id": application_id, "recruiter_id": recruiter_id},
    )
# ---------- WRITE (Step 4: reviewing applications) ----------

def lock_owned_application_status(session, application_id: int, recruiter_id: int):
    """Locks the application row and returns its current status, or None if the
    application does not exist or its internship belongs to someone else."""
    return session.execute(
        text("""
            SELECT a.status
            FROM applications a
            JOIN internships i ON i.internship_id = a.internship_id
            WHERE a.application_id = :application_id
              AND i.posted_by = :recruiter_id
            FOR UPDATE OF a
        """),
        {"application_id": application_id, "recruiter_id": recruiter_id},
    ).scalar()


def update_application_status(session, application_id: int, recruiter_id: int,
                              new_status: str) -> int:
    """status_changed_by MUST be set in the same UPDATE: the history trigger
    reads it to fill application_status_history.changed_by."""
    result = session.execute(
        text("""
            UPDATE applications
            SET status = :new_status,
                status_changed_by = :recruiter_id
            WHERE application_id = :application_id
              AND internship_id IN (
                  SELECT internship_id
                  FROM internships
                  WHERE posted_by = :recruiter_id
              )
        """),
        {"application_id": application_id, "recruiter_id": recruiter_id,
         "new_status": new_status},
    )
    return result.rowcount