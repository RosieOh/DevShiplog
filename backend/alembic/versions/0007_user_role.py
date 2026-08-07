"""사용자 역할

신고는 쌓이는데 처리할 사람이 없으면 신고 기능은 장식이다.
공개 서비스로 열기 전에 운영자를 구분할 수 있어야 한다.

Revision ID: 0007_user_role
Revises: 0006_product_events
"""
from alembic import op
import sqlalchemy as sa

revision = '0007_user_role'
down_revision = '0006_product_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 기존 사용자는 전부 일반 사용자다. 운영자는 스크립트로 명시적으로 올린다 —
    # 마이그레이션이 조용히 누군가를 운영자로 만들면 안 된다.
    op.add_column(
        'users',
        sa.Column(
            'role',
            sa.Enum('USER', 'ADMIN', name='userrole'),
            nullable=False,
            server_default='USER',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'role')
