from alembic import op
import sqlalchemy as sa
revision='0001_initial';down_revision=None;branch_labels=None;depends_on=None
def upgrade():
 op.create_table('workflows',sa.Column('id',sa.String(36),primary_key=True),sa.Column('topic',sa.String(500),nullable=False),sa.Column('status',sa.String(32),nullable=False,server_default='draft'),sa.Column('config',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
 op.create_index('ix_workflows_status','workflows',['status'])
def downgrade():
 op.drop_index('ix_workflows_status',table_name='workflows');op.drop_table('workflows')
