"""Recruiter business rules and transaction boundaries."""
from datetime import date

from sqlalchemy.exc import IntegrityError

from database import recruiter_queries as rq
from database.connection import get_connection

WORK_MODES = ("remote", "on_site", "hybrid")
EDITABLE_STATUSES = ("draft", "open", "closed")

# Allowed internship status transitions for the recruiter who owns it.
INTERNSHIP_TRANSITIONS = {
    "draft": {"open", "cancelled"},
    "open": {"closed", "filled", "cancelled"},
    "closed": {"open", "cancelled"},
    "filled": set(),
    "cancelled": set(),
}

# Maps database constraint names to messages a user can understand.
_CONSTRAINT_MESSAGES = {
    "internships_deadline_valid": "The deadline cannot be earlier than the posting date.",
    "internships_stipend_nonnegative": "The stipend cannot be negative.",
    "internships_duration_positive": "Duration must be at least 1 month.",
    "internships_openings_positive": "Openings must be at least 1.",
    "internships_title_not_blank": "Title cannot be blank.",
    "internships_description_not_blank": "Description cannot be blank.",
    "internships_work_mode_valid": "Invalid work mode.",
    "internships_status_valid": "Invalid status.",
}


class ServiceError(Exception):
    """A problem the user can fix; the message is safe to show on the page."""


def _translate_integrity_error(error: IntegrityError) -> ServiceError:
    text_ = str(error.orig)
    for name, message in _CONSTRAINT_MESSAGES.items():
        if name in text_:
            return ServiceError(message)
    return ServiceError("The database rejected this change (constraint violation).")


def _clean_and_validate(data: dict, *, is_create: bool) -> dict:
    """First line of defence. The CHECK constraints in schema.sql are the second."""
    errors = []

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    location = (data.get("location") or "").strip() or None
    work_mode = data.get("work_mode")
    deadline = data.get("deadline")

    if not title:
        errors.append("Title is required.")
    elif len(title) > 180:
        errors.append("Title must be 180 characters or fewer.")
    if not description:
        errors.append("Description is required.")
    if location and len(location) > 180:
        errors.append("Location must be 180 characters or fewer.")
    if work_mode not in WORK_MODES:
        errors.append("Choose a valid work mode.")

    stipend = data.get("stipend_monthly")
    if stipend is not None and stipend < 0:
        errors.append("Stipend cannot be negative.")

    duration = data.get("duration_months")
    if duration is None or int(duration) < 1:
        errors.append("Duration must be at least 1 month.")

    openings = data.get("openings")
    if openings is None or int(openings) < 1:
        errors.append("Openings must be at least 1.")

    if is_create and deadline is not None and deadline < date.today():
        errors.append("Deadline cannot be in the past.")

    if errors:
        raise ServiceError(" ".join(errors))

    return {
        "title": title,
        "description": description,
        "location": location,
        "work_mode": work_mode,
        "stipend_monthly": stipend,
        "duration_months": int(duration),
        "openings": int(openings),
        "deadline": deadline,
    }


def create_internship(recruiter_id: int, data: dict, skill_ids: list, publish: bool) -> int:
    """Creates the internship and its required skills in ONE transaction."""
    profile = rq.get_recruiter_profile(recruiter_id)
    if profile.empty or profile.iloc[0]["company_id"] is None \
            or str(profile.iloc[0]["company_id"]) in ("nan", "None", "<NA>"):
        raise ServiceError("Your account is not linked to a company, so you cannot post internships.")
    company_id = int(profile.iloc[0]["company_id"])

    clean = _clean_and_validate(data, is_create=True)
    clean["status"] = "open" if publish else "draft"

    with get_connection().session as session:
        try:
            internship_id = rq.insert_internship(session, company_id, recruiter_id, clean)
            rq.replace_internship_skills(session, internship_id, skill_ids)
            session.commit()
            return internship_id
        except IntegrityError as error:
            session.rollback()
            raise _translate_integrity_error(error)
        except Exception:
            session.rollback()
            raise


def update_internship(recruiter_id: int, internship_id: int, data: dict, skill_ids: list) -> None:
    """Edits fields and skills in ONE transaction, only if the recruiter owns the row."""
    clean = _clean_and_validate(data, is_create=False)

    with get_connection().session as session:
        try:
            current_status = rq.lock_owned_internship_status(session, internship_id, recruiter_id)
            if current_status is None:
                raise ServiceError("Internship not found.")
            if current_status not in EDITABLE_STATUSES:
                raise ServiceError(f"A {current_status} internship can no longer be edited.")

            if rq.update_internship_fields(session, internship_id, recruiter_id, clean) != 1:
                raise ServiceError("Internship not found.")
            rq.replace_internship_skills(session, internship_id, skill_ids)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise _translate_integrity_error(error)
        except Exception:
            session.rollback()
            raise


def change_internship_status(recruiter_id: int, internship_id: int, new_status: str) -> None:
    """Lock the row, validate the transition, then update. Two clicks at once
    cannot both succeed, because the second one waits for the lock and then
    sees the new status."""
    with get_connection().session as session:
        try:
            current = rq.lock_owned_internship_status(session, internship_id, recruiter_id)
            if current is None:
                raise ServiceError("Internship not found.")
            if new_status not in INTERNSHIP_TRANSITIONS.get(current, set()):
                raise ServiceError(f"Cannot change an internship from '{current}' to '{new_status}'.")

            if rq.update_internship_status(session, internship_id, recruiter_id, new_status) != 1:
                raise ServiceError("Internship not found.")
            session.commit()
        except Exception:
            session.rollback()
            raise