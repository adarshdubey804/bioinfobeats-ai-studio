from datetime import datetime
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.api.routes.publishing import approve_and_schedule, PublishApproval


class FakeDB:
    def __init__(self, item):
        self.item = item

    def get(self, model, key):
        return self.item

    def commit(self):
        pass


class FakeWorkflow:
    id = "wf-123"
    owner_id = "user-1"
    config = {}


USER = SimpleNamespace(id="user-1")


def test_publish_requires_explicit_approval():
    with pytest.raises(HTTPException) as exc:
        approve_and_schedule("wf-123", PublishApproval(channel_id="channel-1", text="A post", approved=False, publish_now=True), FakeDB(FakeWorkflow()), USER)
    assert exc.value.status_code == 400


def test_schedule_requires_timezone():
    with pytest.raises(HTTPException) as exc:
        approve_and_schedule("wf-123", PublishApproval(channel_id="channel-1", text="A post", approved=True, scheduled_at=datetime.now()), FakeDB(FakeWorkflow()), USER)
    assert exc.value.status_code == 400


def test_publish_now_requires_explicit_approval_and_calls_buffer(monkeypatch):
    item = FakeWorkflow()
    monkeypatch.setattr("app.api.routes.publishing.create_post", lambda *args: {"id": "post-1", "status": "sent", "externalLink": "https://example.com"})
    result = approve_and_schedule("wf-123", PublishApproval(channel_id="channel-1", text="Approved copy", approved=True, publish_now=True), FakeDB(item), USER)
    assert result["publishing"]["post_id"] == "post-1"
    assert item.config["publishing"]["status"] == "sent"
