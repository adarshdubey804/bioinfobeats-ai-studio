from app.api.routes.ideas import IdeaRequest, IdeaStatusRequest

def test_idea_request_limits():
    payload = IdeaRequest(niche="Bioinformatics", audience="Graduate learners", count=8, duration_minutes=5)
    assert payload.count == 8
    assert payload.duration_minutes == 5

def test_status_rejects_unknown_values():
    import pytest
    with pytest.raises(Exception):
        IdeaStatusRequest(status="published-now")
