from alembic import op
import sqlalchemy as sa

revision = "0013_user_media_quota"
down_revision = "0012_job_heartbeats"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("media_bytes_used", sa.BigInteger(), nullable=False, server_default="0"))

def downgrade():
    op.drop_column("users", "media_bytes_used")
