from alembic import op
import sqlalchemy as sa
revision = "0010_job_runs"
down_revision = "0009_media_assets"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("job_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(36), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("celery_task_id", sa.String(100), nullable=True, unique=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_job_runs_workflow_id", "job_runs", ["workflow_id"])
    op.create_index("ix_job_runs_task_type", "job_runs", ["task_type"])
    op.create_index("ix_job_runs_celery_task_id", "job_runs", ["celery_task_id"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])

def downgrade():
    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_job_runs_celery_task_id", table_name="job_runs")
    op.drop_index("ix_job_runs_task_type", table_name="job_runs")
    op.drop_index("ix_job_runs_workflow_id", table_name="job_runs")
    op.drop_table("job_runs")
