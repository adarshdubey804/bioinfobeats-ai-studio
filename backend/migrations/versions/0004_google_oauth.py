from alembic import op
import sqlalchemy as sa

revision = "0004_google_oauth"
down_revision = "0003_workflow_owners"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "google_oauth_connections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(length=2000), nullable=False),
        sa.Column("scopes", sa.String(length=1000), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_google_oauth_user"),
    )
    op.create_index("ix_google_oauth_connections_user_id", "google_oauth_connections", ["user_id"])

def downgrade():
    op.drop_index("ix_google_oauth_connections_user_id", table_name="google_oauth_connections")
    op.drop_table("google_oauth_connections")
