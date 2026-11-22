from datetime import date
import pytest
from app.analytics.youtube import owner_channel_report


class FakeConnection:
    refresh_token_encrypted = "encrypted-refresh-token"


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"columnHeaders": [{"name": "views"}], "rows": [[42]]}


def test_owner_report_refreshes_encrypted_oauth_token(monkeypatch):
    monkeypatch.setattr("app.analytics.youtube.decrypt_refresh_token", lambda value: "refresh-token")
    monkeypatch.setattr("app.analytics.youtube.refresh_access_token", lambda value: {"access_token": "access-token"})
    monkeypatch.setattr("app.analytics.youtube.httpx.get", lambda *args, **kwargs: FakeResponse())
    result = owner_channel_report(date(2026, 1, 1), date(2026, 1, 2), FakeConnection())
    assert result["rows"] == [[42]]
    assert result["source"] == "youtube_analytics_api_owner_report"


def test_owner_report_rejects_reversed_dates():
    with pytest.raises(ValueError, match="on or after"):
        owner_channel_report(date(2026, 1, 3), date(2026, 1, 2), FakeConnection())
