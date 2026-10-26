# 🎓 Internship Finder

A full-stack DBMS platform built with **Streamlit** and **PostgreSQL (Neon)** connecting students seeking internships with recruiters hiring top talent.

---

## 🚀 Features

### 👤 Role-Based Authentication
- **Secure Registration & Login**: Supports both **Students** and **Recruiters** with PBKDF2-HMAC-SHA256 password hashing.
- **Dynamic Role-Based Navigation**: Streamlit navigation dynamically renders personalized portals based on the authenticated session.

### 🎓 Student Portal
- **Dashboard**: Track overall application statuses, saved internships, and quick action items.
- **Browse & Search Internships**: Filter by keywords, work mode (Remote, On-site, Hybrid), stipend, and required skills.
- **One-Click Application**: Apply with custom cover notes and check live deadlines.
- **Profile & Portfolio**:
  - Academic background (University, Degree, CGPA, Graduation Year).
  - Skill inventory with proficiency ratings (Beginner, Intermediate, Advanced).
  - Project portfolio with descriptions and repository links.
- **Application History**: Track application lifecycle stages (Pending ➔ Reviewing ➔ Shortlisted ➔ Accepted / Rejected).

### 💼 Recruiter Portal
- **Recruiter Dashboard**: High-level metrics on total internships, active listings, total applications, and candidates awaiting review.
- **Internship Management**:
  - Create, publish, or save listings as drafts.
  - Set openings, stipend, duration, deadlines, and required skills.
  - Manage internship lifecycle (Draft ➔ Open ➔ Closed / Filled / Cancelled).
- **Candidate Tracking**:
  - Review candidate applications, academic profiles, skills, and projects.
  - Update candidate statuses with automated trigger audit history.

---

## 🛠️ Tech Stack & Architecture

- **Frontend / Framework**: [Streamlit](https://streamlit.io/)
- **Database**: PostgreSQL (Hosted on [Neon](https://neon.tech))
- **ORM / Query Engine**: SQLAlchemy + raw SQL queries with parameterized inputs to prevent SQL injection
- **Authentication**: PBKDF2 password hashing (`hashlib`) with cryptographically secure random salt

---

## 📁 Project Structure

```text
internship-finder/
├── app.py                         # Application entrypoint & navigation router
├── app_pages/
│   ├── common/                    # Public pages
│   │   ├── login.py               # User login form
│   │   └── register.py            # Student & Recruiter registration
│   ├── student/                   # Student portal
│   │   ├── dashboard.py           # Student overview & metrics
│   │   ├── browse_internships.py  # Search and apply for internships
│   │   ├── my_applications.py     # Application tracking
│   │   ├── profile.py             # Academic & personal profile
│   │   ├── my_skills.py           # Skill management
│   │   └── my_projects.py         # Project showcase
│   └── recruiter/                 # Recruiter portal
│       ├── dashboard.py           # Recruiter metrics & stats
│       ├── manage_internships.py  # Create and update internship postings
│       └── applications.py        # Applicant review & status updates
├── database/
│   ├── connection.py              # Neon database connection pool
│   ├── schema.sql                 # DDL definitions, tables & constraints
│   ├── seed.py                    # Initial seed data generator
│   ├── queries.py                 # Student-side SQL operations
│   └── recruiter_queries.py       # Recruiter-side SQL operations
├── services/
│   ├── auth_service.py            # Authentication, registration & session logic
│   └── recruiter_service.py       # Recruiter business rules & validations
└── requirements.txt               # Dependencies
```

---

## ⚡ Getting Started

### 1. Prerequisites
- Python 3.10+
- Neon PostgreSQL Database

### 2. Configure Database Secrets
Ensure `.streamlit/secrets.toml` exists with your database connection strings:

```toml
[connections.neon]
url = "postgresql://<user>:<password>@<neon-host>/<database>?sslmode=require"

[connections.neon_test]
url = "postgresql://<user>:<password>@<neon-host>/<test-database>?sslmode=require"
```

### 3. Initialize & Seed Database (Optional)
Run the seed script to create initial sample companies, students, recruiters, and internships:

```powershell
# Using the local virtual environment:
.\.venv\Scripts\python.exe database/seed.py
```

### 4. Run the Application

```powershell
# Option A: Run directly using the virtual environment executable
.\.venv\Scripts\streamlit.exe run .\app.py

# Option B: Activate the virtual environment in PowerShell first
.\.venv\Scripts\Activate.ps1
streamlit run .\app.py
```

The application will open in your browser at `http://localhost:8501`.

---

## 🔐 Default Demo Accounts

If you seeded the database with `seed.py`, you can test with:
- **Default Password**: `DemoPass123!`
- Check `users` table for seeded emails, or simply create a new student or recruiter account via the **Register** page!
