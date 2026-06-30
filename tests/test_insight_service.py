from backend.services.insight_service import InsightService


def test_extract_skill_counts_finds_known_keywords():
    service = InsightService()
    counts = service._extract_skill_counts(
        "Python, FastAPI, and Docker are important for modern backend development."
    )

    assert counts["python"] == 1
    assert counts["fastapi"] == 1
    assert counts["docker"] == 1
    assert counts["backend"] == 1


def test_extract_skill_counts_is_case_insensitive():
    service = InsightService()
    counts = service._extract_skill_counts("PYTHON and pYtHoN")

    assert counts["python"] == 2
