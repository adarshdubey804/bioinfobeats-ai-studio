from app.models.job_run import JobRun


def test_job_run_stores_durable_execution_state():
    run = JobRun(workflow_id="workflow-1", task_type="agent_pipeline", status="queued", progress={"stage": "queued", "percent": 0})
    assert run.workflow_id == "workflow-1"
    assert run.status == "queued"
    assert run.progress["percent"] == 0
    assert run.attempts in (None, 0)
    assert run.cancel_requested in (None, False)


from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.worker.job_health import job_health


def test_queued_job_becomes_stale_after_thirty_minutes():
    now = datetime.now(timezone.utc)
    run = SimpleNamespace(status="queued", started_at=None, created_at=now - timedelta(minutes=31))
    assert job_health(run, now)["is_stale"] is True


def test_recent_running_job_is_not_stale():
    now = datetime.now(timezone.utc)
    run = SimpleNamespace(status="running", started_at=now - timedelta(minutes=5), created_at=now - timedelta(minutes=6))
    assert job_health(run, now)["health"] == "active"


def test_completed_job_is_never_stale():
    now = datetime.now(timezone.utc)
    run = SimpleNamespace(status="succeeded", started_at=now - timedelta(days=2), created_at=now - timedelta(days=2))
    assert job_health(run, now)["health"] == "finished"
