from datetime import date
import pytest
from app.analytics.youtube import owner_channel_report, AnalyticsConfigurationError
from app.core.config import settings

def test_owner_report_requires_oauth_token(monkeypatch):
    monkeypatch.setattr(settings, "youtube_oauth_access_token", "")
    with pytest.raises(AnalyticsConfigurationError):
        owner_channel_report(date(2026, 1, 1), date(2026, 1, 2))

def test_owner_report_rejects_reversed_dates(monkeypatch):
    monkeypatch.setattr(settings, "youtube_oauth_access_token", "test-token")
    with pytest.raises(ValueError):
        owner_channel_report(date(2026, 1, 3), date(2026, 1, 2))
