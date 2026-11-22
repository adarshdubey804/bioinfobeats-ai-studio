from alembic import op
import sqlalchemy as sa

revision = "0012_job_heartbeats"
down_revision = "0011_job_cancellation"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("job_runs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column("job_runs", "heartbeat_at")
