
import hashlib
import hmac

from sqlalchemy import text
from database.connection import get_connection


# Helpers

def hash_password(password: str) -> str:
    """Hash demo passwords using Python's built-in PBKDF2."""
    salt = b"internship-finder-demo"
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600_000,
    ).hex()
    return f"pbkdf2_sha256$600000${salt.hex()}${digest}"


def get_or_create_user(session, name, email, role):
    row = session.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE LOWER(email) = LOWER(:email)
        """),
        {"email": email},
    ).first()

    if row:
        return row[0]

    result = session.execute(
        text("""
            INSERT INTO users
                (full_name, email, password_hash, role)
            VALUES
                (:name, :email, :password_hash, :role)
            RETURNING user_id
        """),
        {
            "name": name,
            "email": email,
            "password_hash": hash_password("DemoPass123!"),
            "role": role,
        },
    )
    return result.scalar_one()


def get_or_create_company(session, name, industry, city, website, description):
    row = session.execute(
        text("SELECT company_id FROM companies WHERE name = :name"),
        {"name": name},
    ).first()

    if row:
        return row[0]

    result = session.execute(
        text("""
            INSERT INTO companies
                (name, industry, city, website, description)
            VALUES
                (:name, :industry, :city, :website, :description)
            RETURNING company_id
        """),
        {
            "name": name,
            "industry": industry,
            "city": city,
            "website": website,
            "description": description,
        },
    )
    return result.scalar_one()


def get_or_create_skill(session, name, category):
    row = session.execute(
        text("SELECT skill_id FROM skills WHERE skill_name = :name"),
        {"name": name},
    ).first()

    if row:
        return row[0]

    result = session.execute(
        text("""
            INSERT INTO skills (skill_name, category)
            VALUES (:name, :category)
            RETURNING skill_id
        """),
        {"name": name, "category": category},
    )
    return result.scalar_one()


def get_or_create_internship(
    session,
    company_id,
    recruiter_id,
    title,
    description,
    location,
    work_mode,
    stipend,
    duration,
    openings,
    deadline,
):
    row = session.execute(
        text("""
            SELECT internship_id
            FROM internships
            WHERE company_id = :company_id
              AND title = :title
        """),
        {"company_id": company_id, "title": title},
    ).first()

    if row:
        return row[0]

    result = session.execute(
        text("""
            INSERT INTO internships (
                company_id, posted_by, title, description,
                location, work_mode, stipend_monthly,
                duration_months, openings, deadline, status
            )
            VALUES (
                :company_id, :recruiter_id, :title, :description,
                :location, :work_mode, :stipend,
                :duration, :openings, :deadline, 'open'
            )
            RETURNING internship_id
        """),
        {
            "company_id": company_id,
            "recruiter_id": recruiter_id,
            "title": title,
            "description": description,
            "location": location,
            "work_mode": work_mode,
            "stipend": stipend,
            "duration": duration,
            "openings": openings,
            "deadline": deadline,
        },
    )
    return result.scalar_one()


# Seed database

def seed_database():
    conn = get_connection()

    with conn.session as session:
        try:
            # 1. Companies
            companies_data = [
                (
                    "PixelForge Labs", "Software", "Bengaluru",
                    "https://example.com/pixelforge",
                    "A fictional software product company.",
                ),
                (
                    "DataNest Analytics", "Data Analytics", "Pune",
                    "https://example.com/datanest",
                    "A fictional data analytics company.",
                ),
                (
                    "NeuralSpring AI", "Artificial Intelligence", "Remote",
                    "https://example.com/neuralspring",
                    "A fictional AI research startup.",
                ),
                (
                    "CloudBridge Systems", "Cloud Computing", "Hyderabad",
                    "https://example.com/cloudbridge",
                    "A fictional cloud technology company.",
                ),
            ]

            company_ids = {}
            for item in companies_data:
                company_ids[item[0]] = get_or_create_company(
                    session, *item
                )

            # 2. Recruiters
            recruiters_data = [
                ("Aarav Mehta", "aarav.recruiter@example.com",
                 "PixelForge Labs", "Technical Recruiter"),
                ("Diya Shah", "diya.recruiter@example.com",
                 "DataNest Analytics", "Hiring Manager"),
                ("Kabir Rao", "kabir.recruiter@example.com",
                 "NeuralSpring AI", "AI Research Recruiter"),
                ("Anaya Iyer", "anaya.recruiter@example.com",
                 "CloudBridge Systems", "Talent Partner"),
            ]

            recruiter_ids = {}
            for name, email, company_name, job_title in recruiters_data:
                user_id = get_or_create_user(
                    session, name, email, "recruiter"
                )
                recruiter_ids[company_name] = user_id

                session.execute(
                    text("""
                        INSERT INTO recruiter_profiles
                            (recruiter_id, company_id, job_title)
                        VALUES (:user_id, :company_id, :job_title)
                        ON CONFLICT (recruiter_id) DO NOTHING
                    """),
                    {
                        "user_id": user_id,
                        "company_id": company_ids[company_name],
                        "job_title": job_title,
                    },
                )

            # 3. Students
            students_data = [
                ("Riya Sharma", "riya.student@example.com",
                 "ABC Institute of Technology", "B.Tech AI", 2028, 8.4,
                 "Ahmedabad"),
                ("Arjun Patel", "arjun.student@example.com",
                 "Western Engineering College", "B.Tech CSE", 2027, 8.1,
                 "Surat"),
                ("Meera Nair", "meera.student@example.com",
                 "National Institute of Technology", "B.Tech IT", 2028, 9.0,
                 "Pune"),
            ]

            student_ids = {}
            for name, email, university, degree, grad_year, cgpa, city in students_data:
                user_id = get_or_create_user(
                    session, name, email, "student"
                )
                student_ids[email] = user_id

                session.execute(
                    text("""
                        INSERT INTO student_profiles (
                            student_id, university, degree,
                            graduation_year, cgpa, city, bio
                        )
                        VALUES (
                            :student_id, :university, :degree,
                            :grad_year, :cgpa, :city, :bio
                        )
                        ON CONFLICT (student_id) DO NOTHING
                    """),
                    {
                        "student_id": user_id,
                        "university": university,
                        "degree": degree,
                        "grad_year": grad_year,
                        "cgpa": cgpa,
                        "city": city,
                        "bio": f"Demo student interested in technology and internships.",
                    },
                )

            # 4. Skills
            skill_data = [
                ("Python", "Programming"),
                ("SQL", "Database"),
                ("C++", "Programming"),
                ("Machine Learning", "AI/ML"),
                ("Data Analysis", "Analytics"),
                ("React", "Web Development"),
                ("Git", "Tools"),
                ("PostgreSQL", "Database"),
            ]

            skill_ids = {
                name: get_or_create_skill(session, name, category)
                for name, category in skill_data
            }

            # 5. Internships
            internships_data = [
                ("PixelForge Labs", "Python Developer Intern",
                 "Build Python utilities and backend features.",
                 "Bengaluru", "hybrid", 18000, 3, 2,
                 ["Python", "SQL", "Git"]),
                ("PixelForge Labs", "Frontend Developer Intern",
                 "Help develop responsive web interfaces.",
                 "Remote", "remote", 15000, 3, 2,
                 ["React", "Git"]),
                ("PixelForge Labs", "C++ Software Intern",
                 "Work on application modules and algorithms.",
                 "Bengaluru", "on_site", 12000, 2, 1,
                 ["C++", "Git"]),
                ("DataNest Analytics", "Data Analyst Intern",
                 "Clean datasets and create analytical reports.",
                 "Pune", "hybrid", 16000, 3, 2,
                 ["Python", "SQL", "Data Analysis"]),
                ("DataNest Analytics", "SQL Intern",
                 "Write queries and assist with database reporting.",
                 "Remote", "remote", 10000, 2, 1,
                 ["SQL", "PostgreSQL"]),
                ("NeuralSpring AI", "Machine Learning Intern",
                 "Prototype and evaluate machine learning models.",
                 "Remote", "remote", 22000, 4, 2,
                 ["Python", "Machine Learning"]),
                ("NeuralSpring AI", "AI Research Intern",
                 "Support experiments and research prototypes.",
                 "Ahmedabad", "hybrid", 20000, 4, 1,
                 ["Python", "Machine Learning", "SQL"]),
                ("CloudBridge Systems", "Database Intern",
                 "Assist with PostgreSQL queries and database design.",
                 "Hyderabad", "on_site", 14000, 3, 2,
                 ["SQL", "PostgreSQL"]),
                ("CloudBridge Systems", "Python Automation Intern",
                 "Automate repetitive workflows using Python.",
                 "Remote", "remote", 12500, 3, 1,
                 ["Python", "Git"]),
                ("DataNest Analytics", "Business Data Intern",
                 "Explore business data and prepare visual reports.",
                 "Pune", "on_site", 0, 2, 1,
                 ["SQL", "Data Analysis"]),
            ]

            internship_ids = {}

            for (
                company_name, title, description, location, work_mode,
                stipend, duration, openings, required_skills
            ) in internships_data:
                internship_id = get_or_create_internship(
                    session,
                    company_ids[company_name],
                    recruiter_ids[company_name],
                    title,
                    description,
                    location,
                    work_mode,
                    stipend,
                    duration,
                    openings,
                    "2027-12-31",
                )
                internship_ids[title] = internship_id

                for skill in required_skills:
                    session.execute(
                        text("""
                            INSERT INTO internship_skills
                                (internship_id, skill_id)
                            VALUES (:internship_id, :skill_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "internship_id": internship_id,
                            "skill_id": skill_ids[skill],
                        },
                    )

            # 6. Student skills
            student_skill_data = [
                ("riya.student@example.com",
                 ["Python", "SQL", "Machine Learning"]),
                ("arjun.student@example.com",
                 ["C++", "Git", "SQL"]),
                ("meera.student@example.com",
                 ["Python", "Data Analysis", "PostgreSQL"]),
            ]

            for email, skills in student_skill_data:
                for skill in skills:
                    session.execute(
                        text("""
                            INSERT INTO student_skills
                                (student_id, skill_id, proficiency)
                            VALUES (:student_id, :skill_id, 'intermediate')
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "student_id": student_ids[email],
                            "skill_id": skill_ids[skill],
                        },
                    )

            # 7. Saved internships
            saved_data = [
                ("riya.student@example.com", "Machine Learning Intern"),
                ("riya.student@example.com", "Python Developer Intern"),
                ("arjun.student@example.com", "C++ Software Intern"),
                ("meera.student@example.com", "Data Analyst Intern"),
            ]

            for email, title in saved_data:
                session.execute(
                    text("""
                        INSERT INTO saved_internships
                            (student_id, internship_id)
                        VALUES (:student_id, :internship_id)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "student_id": student_ids[email],
                        "internship_id": internship_ids[title],
                    },
                )

            # 8. Applications
            application_data = [
                ("riya.student@example.com", "Python Developer Intern",
                 "I enjoy building Python projects.", "pending"),
                ("riya.student@example.com", "Machine Learning Intern",
                 "I am interested in applied ML.", "shortlisted"),
                ("arjun.student@example.com", "C++ Software Intern",
                 "I have experience with C++ and algorithms.", "rejected"),
                ("meera.student@example.com", "Data Analyst Intern",
                 "I enjoy working with data and SQL.", "accepted"),
                ("meera.student@example.com", "Database Intern",
                 "I want to deepen my database skills.", "pending"),
            ]

            for email, title, cover_note, desired_status in application_data:
                student_id = student_ids[email]
                internship_id = internship_ids[title]

                row = session.execute(
                    text("""
                        SELECT application_id
                        FROM applications
                        WHERE student_id = :student_id
                          AND internship_id = :internship_id
                    """),
                    {
                        "student_id": student_id,
                        "internship_id": internship_id,
                    },
                ).first()

                if row:
                    application_id = row[0]
                else:
                    result = session.execute(
                        text("""
                            INSERT INTO applications (
                                internship_id, student_id, status,
                                status_changed_by, cover_note
                            )
                            VALUES (
                                :internship_id, :student_id, 'pending',
                                :changed_by, :cover_note
                            )
                            RETURNING application_id
                        """),
                        {
                            "internship_id": internship_id,
                            "student_id": student_id,
                            "changed_by": student_id,
                            "cover_note": cover_note,
                        },
                    )
                    application_id = result.scalar_one()

                # Only change status on first seed; repeated runs leave
                # existing applications untouched.
                if not row and desired_status != "pending":
                    recruiter_id = session.execute(
                        text("""
                            SELECT posted_by
                            FROM internships
                            WHERE internship_id = :internship_id
                        """),
                        {"internship_id": internship_id},
                    ).scalar_one()

                    session.execute(
                        text("""
                            UPDATE applications
                            SET status = :status,
                                status_changed_by = :recruiter_id
                            WHERE application_id = :application_id
                        """),
                        {
                            "status": desired_status,
                            "recruiter_id": recruiter_id,
                            "application_id": application_id,
                        },
                    )

            
            # 9. Projects
            projects_data = [
                (
                    "riya.student@example.com",
                    "Internship Tracker",
                    "A small project to organize internship applications.",
                ),
                (
                    "arjun.student@example.com",
                    "Algorithm Visualizer",
                    "A demo project for exploring common algorithms.",
                ),
                (
                    "meera.student@example.com",
                    "Sales Data Analysis",
                    "A sample project analyzing sales data with Python.",
                ),
            ]

            for email, title, description in projects_data:
                student_id = student_ids[email]

                existing_project = session.execute(
                    text("""
                        SELECT project_id
                        FROM projects
                        WHERE student_id = :student_id
                          AND title = :title
                    """),
                    {
                        "student_id": student_id,
                        "title": title,
                    },
                ).first()

                if existing_project is None:
                    session.execute(
                        text("""
                            INSERT INTO projects (
                                student_id,
                                title,
                                description
                            )
                            VALUES (
                                :student_id,
                                :title,
                                :description
                            )
                        """),
                        {
                            "student_id": student_id,
                            "title": title,
                            "description": description,
                        },
                    )


            session.commit()

        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    seed_database()
    print("Seed data inserted successfully!")
