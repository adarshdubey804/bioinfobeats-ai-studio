from alembic import op
import sqlalchemy as sa

revision = "0005_analytics_snapshots"
down_revision = "0004_google_oauth"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.String(length=10), nullable=False),
        sa.Column("period_end", sa.String(length=10), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analytics_snapshots_user_id", "analytics_snapshots", ["user_id"])
    op.create_index("ix_analytics_snapshots_user_created", "analytics_snapshots", ["user_id", "created_at"])

def downgrade():
    op.drop_index("ix_analytics_snapshots_user_created", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_user_id", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
