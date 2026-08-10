"""서버 오류 기록

메모리에만 두었더니 재시작하면 사라지고, 워커가 여럿이면 일부만 보였다.
"어제 밤에 뭐가 터졌지" 를 물을 수 없는 기록은 기록이 아니다.

Revision ID: 0008_error_groups
Revises: 0007_user_role
"""
from alembic import op
import sqlalchemy as sa

revision = '0008_error_groups'
down_revision = '0007_user_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'error_groups',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('fingerprint', sa.String(length=32), nullable=False),
        sa.Column('type', sa.String(length=120), nullable=False),
        sa.Column('message', sa.String(length=300), nullable=True),
        sa.Column('origin', sa.String(length=500), nullable=True),
        sa.Column('path', sa.String(length=500), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('first_seen', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_seen', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_request_id', sa.String(length=64), nullable=True),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        # 지문당 한 행. 워커가 여럿이면 같은 지문을 동시에 만들려 하는데,
        # 이 제약이 없으면 같은 오류가 여러 행으로 갈라져 "몇 번" 을 셀 수 없다.
        sa.UniqueConstraint('fingerprint', name='uq_error_groups_fingerprint'),
    )
    op.create_index('ix_error_groups_last_seen', 'error_groups', ['last_seen'])
    op.create_index('ix_error_groups_resolved_seen', 'error_groups', ['resolved_at', 'last_seen'])


def downgrade() -> None:
    op.drop_table('error_groups')
