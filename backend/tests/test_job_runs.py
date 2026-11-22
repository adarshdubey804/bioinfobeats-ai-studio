from app.models.job_run import JobRun


def test_job_run_stores_durable_execution_state():
    run = JobRun(workflow_id="workflow-1", task_type="agent_pipeline", status="queued", progress={"stage": "queued", "percent": 0})
    assert run.workflow_id == "workflow-1"
    assert run.status == "queued"
    assert run.progress["percent"] == 0
    assert run.attempts in (None, 0)
