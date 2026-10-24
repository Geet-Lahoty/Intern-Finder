from database.connection import run_query


def get_all_internships():
    return run_query(
        """
        SELECT *
        FROM internships
        ORDER BY internship_id DESC
        """
    )
