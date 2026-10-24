from database.connection import (run_query, get_connection)
from sqlalchemy import text


# internship queries
def get_all_internships():
    return run_query(
        """
        SELECT
            i.internship_id,
            i.title,
            c.name AS company_name,
            i.description,
            i.location,
            i.work_mode,
            i.stipend_monthly,
            i.duration_months,
            i.openings,
            i.deadline,
            i.status,
            i.posted_at
        FROM internships AS i
        JOIN companies AS c
            ON i.company_id = c.company_id
        WHERE i.status = 'open'
        ORDER BY i.posted_at DESC
        """
    )


def search_internships(
    title="",
    location="",
    min_stipend=None,
    work_mode="",
):
    query = """
        SELECT
            i.internship_id,
            i.title,
            c.name AS company_name,
            i.description,
            i.location,
            i.work_mode,
            i.stipend_monthly,
            i.duration_months,
            i.openings,
            i.deadline,
            i.status
        FROM internships AS i
        JOIN companies AS c
            ON i.company_id = c.company_id
        WHERE i.status = 'open'
    """

    params = {}

    if title.strip():
        query += " AND i.title ILIKE :title"
        params["title"] = f"%{title.strip()}%"

    if location.strip():
        query += " AND i.location ILIKE :location"
        params["location"] = f"%{location.strip()}%"

    if min_stipend is not None:
        query += " AND i.stipend_monthly >= :min_stipend"
        params["min_stipend"] = min_stipend

    if work_mode.strip():
        query += " AND i.work_mode = :work_mode"
        params["work_mode"] = work_mode.strip().lower()

    query += " ORDER BY i.posted_at DESC"

    return run_query(query, params=params)


# application queries
def get_student_applications(student_id):
    return run_query(
        """
        SELECT
            a.application_id,
            i.title AS internship_title,
            c.name AS company_name,
            a.status,
            a.applied_at,
            a.cover_note
        FROM applications AS a
        JOIN internships AS i
            ON a.internship_id = i.internship_id
        JOIN companies AS c
            ON i.company_id = c.company_id
        WHERE a.student_id = :student_id
        ORDER BY a.applied_at DESC
        """,
        params={"student_id": student_id},
    )


def apply_for_internship(student_id, internship_id, cover_note=""):
    conn = get_connection()

    with conn.session as session:
        try:
            result = session.execute(
                text("""
                    INSERT INTO applications (
                        student_id,
                        internship_id,
                        status,
                        status_changed_by,
                        cover_note
                    )
                    SELECT
                        :student_id,
                        i.internship_id,
                        'pending',
                        :student_id,
                        :cover_note
                    FROM internships AS i
                    WHERE i.internship_id = :internship_id
                      AND i.status = 'open'
                      AND (
                          i.deadline IS NULL
                          OR i.deadline >= CURRENT_DATE
                      )
                    ON CONFLICT (student_id, internship_id)
                    DO NOTHING
                    RETURNING application_id
                """),
                {
                    "student_id": student_id,
                    "internship_id": internship_id,
                    "cover_note": cover_note.strip() or None,
                },
            )

            application_id = result.scalar_one_or_none()
            session.commit()

            return application_id

        except Exception:
            session.rollback()
            raise


def get_application_history(application_id):
    return run_query(
        """
        SELECT
            h.history_id,
            h.old_status,
            h.new_status,
            h.changed_by,
            h.changed_at
        FROM application_status_history AS h
        WHERE h.application_id = :application_id
        ORDER BY h.changed_at DESC
        """,
        params={"application_id": application_id},
    )


# recruiter queries
def get_recruiter_internships(recruiter_id):
    return run_query(
        """
        SELECT
            i.internship_id,
            i.title,
            i.status AS internship_status,
            i.location,
            i.work_mode,
            i.stipend_monthly,
            i.deadline,
            COUNT(a.application_id) AS total_applications,
            COUNT(a.application_id)
                FILTER (WHERE a.status = 'pending') AS pending_count,
            COUNT(a.application_id)
                FILTER (WHERE a.status = 'shortlisted') AS shortlisted_count,
            COUNT(a.application_id)
                FILTER (WHERE a.status = 'accepted') AS accepted_count,
            COUNT(a.application_id)
                FILTER (WHERE a.status = 'rejected') AS rejected_count
        FROM internships AS i
        LEFT JOIN applications AS a
            ON i.internship_id = a.internship_id
        WHERE i.posted_by = :recruiter_id
        GROUP BY i.internship_id
        ORDER BY i.posted_at DESC
        """,
        params={"recruiter_id": recruiter_id},
    )


def get_internship_applicants(internship_id, recruiter_id):
    return run_query(
        """
        SELECT
            a.application_id,
            u.full_name,
            u.email,
            sp.university,
            sp.degree,
            sp.graduation_year,
            sp.cgpa,
            sp.city AS student_city,
            a.status AS application_status,
            a.applied_at,
            a.cover_note
        FROM applications AS a
        JOIN internships AS i
            ON a.internship_id = i.internship_id
        JOIN student_profiles AS sp
            ON a.student_id = sp.student_id
        JOIN users AS u
            ON sp.student_id = u.user_id
        WHERE a.internship_id = :internship_id
          AND i.posted_by = :recruiter_id
        ORDER BY a.applied_at DESC
        """,
        params={
            "internship_id": internship_id,
            "recruiter_id": recruiter_id,
        },
    )


def update_application_status(
    application_id,
    recruiter_id,
    new_status,
):
    allowed_statuses = {
        "pending",
        "shortlisted",
        "rejected",
        "accepted",
        "withdrawn",
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid application status.")

    conn = get_connection()

    with conn.session as session:
        try:
            result = session.execute(
                text("""
                    UPDATE applications AS a
                    SET status = :new_status,
                        status_changed_by = :recruiter_id
                    FROM internships AS i
                    WHERE a.application_id = :application_id
                      AND i.internship_id = a.internship_id
                      AND i.posted_by = :recruiter_id
                      AND a.status <> :new_status
                    RETURNING a.application_id
                """),
                {
                    "application_id": application_id,
                    "recruiter_id": recruiter_id,
                    "new_status": new_status,
                },
            )

            updated_id = result.scalar_one_or_none()
            session.commit()
            return updated_id

        except Exception:
            session.rollback()
            raise


# Students queries

# fetch student account details
def get_student_profile(student_id):
    return run_query(
        """
        SELECT
            u.user_id AS student_id,
            u.full_name,
            u.email,
            u.is_active,
            sp.university,
            sp.degree,
            sp.graduation_year,
            sp.cgpa,
            sp.city,
            sp.phone,
            sp.github_url,
            sp.linkedin_url,
            sp.portfolio_url,
            sp.resume_url,
            sp.bio
        FROM users AS u
        JOIN student_profiles AS sp
            ON sp.student_id = u.user_id
        WHERE u.user_id = :student_id
          AND u.role = 'student'
        """,
        params={"student_id": student_id},
    )

# Update a student's profile without changing account credentials
def update_student_profile(
    student_id,
    university,
    degree,
    graduation_year,
    cgpa,
    city,
    phone,
    github_url,
    linkedin_url,
    portfolio_url,
    resume_url,
    bio,
):

    conn = get_connection()

    with conn.session as session:
        try:
            result = session.execute(
                text("""
                    UPDATE student_profiles AS sp
                    SET university = :university,
                        degree = :degree,
                        graduation_year = :graduation_year,
                        cgpa = :cgpa,
                        city = :city,
                        phone = :phone,
                        github_url = :github_url,
                        linkedin_url = :linkedin_url,
                        portfolio_url = :portfolio_url,
                        resume_url = :resume_url,
                        bio = :bio
                    FROM users AS u
                    WHERE sp.student_id = :student_id
                      AND u.user_id = sp.student_id
                      AND u.role = 'student'
                    RETURNING sp.student_id
                """),
                {
                    "student_id": student_id,
                    "university": university.strip() or None,
                    "degree": degree.strip() or None,
                    "graduation_year": graduation_year,
                    "cgpa": cgpa,
                    "city": city.strip() or None,
                    "phone": phone.strip() or None,
                    "github_url": github_url.strip() or None,
                    "linkedin_url": linkedin_url.strip() or None,
                    "portfolio_url": portfolio_url.strip() or None,
                    "resume_url": resume_url.strip() or None,
                    "bio": bio.strip() or None,
                },
            )

            updated_student_id = result.scalar_one_or_none()
            session.commit()
            return updated_student_id

        except Exception:
            session.rollback()
            raise
