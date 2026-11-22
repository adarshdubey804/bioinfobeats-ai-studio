from alembic import op
import sqlalchemy as sa

revision = "0003_workflow_owners"
down_revision = "0002_users"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("workflows", sa.Column("owner_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_workflows_owner_id_users", "workflows", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_workflows_owner_id", "workflows", ["owner_id"], unique=False)

def downgrade():
    op.drop_index("ix_workflows_owner_id", table_name="workflows")
    op.drop_constraint("fk_workflows_owner_id_users", "workflows", type_="foreignkey")
    op.drop_column("workflows", "owner_id")
