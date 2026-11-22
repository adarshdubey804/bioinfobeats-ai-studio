from alembic import op
import sqlalchemy as sa

revision = "0008_script_revisions"
down_revision = "0007_research_scripts"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "script_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("script_id", sa.String(36), sa.ForeignKey("research_scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("change_note", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_script_revisions_script_id", "script_revisions", ["script_id"])
    op.create_index("ix_script_revisions_user_id", "script_revisions", ["user_id"])

def downgrade():
    op.drop_index("ix_script_revisions_user_id", table_name="script_revisions")
    op.drop_index("ix_script_revisions_script_id", table_name="script_revisions")
    op.drop_table("script_revisions")
