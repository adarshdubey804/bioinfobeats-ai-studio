from alembic import op
import sqlalchemy as sa

revision = '0011_job_cancellation'
down_revision = '0010_job_runs'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('job_runs', sa.Column('cancel_requested', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('job_runs', 'cancel_requested')
