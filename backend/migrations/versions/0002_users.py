from alembic import op
import sqlalchemy as sa
revision='0002_users';down_revision='0001_initial';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('users',sa.Column('id',sa.String(36),primary_key=True),sa.Column('email',sa.String(320),nullable=False),sa.Column('password_hash',sa.String(255),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
 op.create_index('ix_users_email','users',['email'],unique=True)
def downgrade():
 op.drop_index('ix_users_email',table_name='users');op.drop_table('users')
