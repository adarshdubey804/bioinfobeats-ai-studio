from alembic import op
import sqlalchemy as sa

revision = "0007_research_scripts"
down_revision = "0006_content_ideas"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "research_scripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("audience", sa.String(300), nullable=False),
        sa.Column("target_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("claims", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("fact_check", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_scripts_user_id", "research_scripts", ["user_id"])

def downgrade():
    op.drop_index("ix_research_scripts_user_id", table_name="research_scripts")
    op.drop_table("research_scripts")
