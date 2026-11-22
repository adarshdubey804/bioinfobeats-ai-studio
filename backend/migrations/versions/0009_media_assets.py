from alembic import op
import sqlalchemy as sa

revision = "0009_media_assets"
down_revision = "0008_script_revisions"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_name", sa.String(100), nullable=False, unique=True),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_media_assets_user_id", "media_assets", ["user_id"])
    op.create_index("ix_media_assets_media_type", "media_assets", ["media_type"])

def downgrade():
    op.drop_index("ix_media_assets_media_type", table_name="media_assets")
    op.drop_index("ix_media_assets_user_id", table_name="media_assets")
    op.drop_table("media_assets")
