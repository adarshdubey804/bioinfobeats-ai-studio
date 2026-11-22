from datetime import datetime, timezone

ACTIVE_JOB_STATUSES = {"queued", "running", "retrying", "cancelling"}


def job_health(run, now=None):
    """Return stale-job diagnostics without mutating or replaying work."""
    now = now or datetime.now(timezone.utc)
    anchor = getattr(run, 'heartbeat_at', None) or run.started_at or run.created_at
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    age_seconds = max(0, int((now - anchor).total_seconds()))
    threshold = 30 * 60 if run.status == "queued" else 45 * 60
    stale = run.status in ACTIVE_JOB_STATUSES and age_seconds >= threshold
    return {
        "is_stale": stale,
        "age_seconds": age_seconds,
        "stale_after_seconds": threshold if run.status in ACTIVE_JOB_STATUSES else None,
        "health": "stale" if stale else ("active" if run.status in ACTIVE_JOB_STATUSES else "finished"),
    }
