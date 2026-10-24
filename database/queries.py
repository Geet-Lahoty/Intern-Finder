from database.connection import run_query


def get_all_internships():
    return run_query(
        """
        SELECT *
        FROM internships
        ORDER BY internship_id DESC
        """
    )


def search_internships(
        title="",
        location="",
        min_stipend=None,
):
    query = """
        SELECT * FROM internships
        WHERE 1 = 1
    """

    params = {}

    if title.strip():
        query += " AND title ILIKE :title"
        params["title"] = f"%{title.strip()}%"

    if location.strip():
        query += " AND location ILIKE :location"
        params["location"] = f"%{location.strip()}%"

    if min_stipend is not None:
        query += " AND stipend >= :min_stipend"
        params["min_stipend"] = min_stipend

    query += " ORDER BY internship_id DESC"

    return run_query(query, params=params)