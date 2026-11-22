from datetime import date
from types import SimpleNamespace
from app.analytics.collection import collect_connection_snapshot

class FakeQuery:
    def __init__(self, model): self.model = model

def test_collection_creates_seven_day_snapshot(monkeypatch):
    import app.analytics.collection as module
    captured = {}
    monkeypatch.setattr(module, "owner_channel_report", lambda start, end, connection: {"rows": [[7, 2]]})
    class FakeDB:
        def add(self, item): captured["item"] = item
        def commit(self): pass
        def refresh(self, item): item.id = "snapshot-1"
    connection = SimpleNamespace(user_id="user-1")
    result = collect_connection_snapshot(FakeDB(), connection, date(2026, 11, 22))
    assert result.period_start == "2026-11-16"
    assert result.period_end == "2026-11-22"
    assert result.report == {"rows": [[7, 2]]}
