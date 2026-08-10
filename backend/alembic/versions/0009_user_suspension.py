"""사용자 정지

신고 처리로 글을 내리는 것까지만 할 수 있었다.
같은 사람이 반복하면 글을 하나씩 내리는 것으로는 멈추지 않는다.

기한제만 둔다. 영구 정지는 오판했을 때 고칠 방법이 없고, 오판은 한다.

Revision ID: 0009_user_suspension
Revises: 0008_error_groups
"""
from alembic import op
import sqlalchemy as sa

revision = '0009_user_suspension'
down_revision = '0008_error_groups'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('suspended_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('suspend_reason', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'suspend_reason')
    op.drop_column('users', 'suspended_until')
