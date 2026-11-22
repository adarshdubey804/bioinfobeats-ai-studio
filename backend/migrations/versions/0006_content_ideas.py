from alembic import op
import sqlalchemy as sa

revision = "0006_content_ideas"
down_revision = "0005_analytics_snapshots"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "content_ideas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(300), nullable=False),
        sa.Column("format", sa.String(80), nullable=False),
        sa.Column("target_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("scheduled_date", sa.String(10), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_ideas_user_id", "content_ideas", ["user_id"])
    op.create_index("ix_content_ideas_status", "content_ideas", ["status"])

def downgrade():
    op.drop_index("ix_content_ideas_status", table_name="content_ideas")
    op.drop_index("ix_content_ideas_user_id", table_name="content_ideas")
    op.drop_table("content_ideas")
