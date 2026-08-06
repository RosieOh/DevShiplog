"""기술 스택 메타데이터와 신선도

글을 "어떤 스택의 어떤 버전에서, 언제 확인된 절차" 로 다루기 위한 스키마.
자세한 배경은 docs/PRODUCT_STRATEGY.md 참고.

Revision ID: 0005_tech_stack_freshness
Revises: 0004_templates_schedules
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_tech_stack_freshness'
down_revision = '0004_templates_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'post_stacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('post_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.String(length=10), nullable=False, server_default='high'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'name', name='unique_post_stack'),
    )
    # 스택 탐색 페이지(/stacks/react)의 주 경로.
    op.create_index('ix_post_stacks_name_version', 'post_stacks', ['name', 'version'])

    op.create_table(
        'post_signals',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('post_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('kind', sa.Enum('WORKS', 'BROKEN', name='signalkind'), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # 한 사람이 한 글에 하나. 여러 번 눌러 신호를 부풀리지 못하게.
        sa.UniqueConstraint('post_id', 'user_id', name='unique_post_signal_per_user'),
    )
    op.create_index('ix_post_signals_post_resolved', 'post_signals', ['post_id', 'resolved_at'])

    # 마지막으로 "지금도 동작한다" 고 확인한 시각. published_at 과 다른 개념이다.
    op.add_column('posts', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_posts_verified_at'), 'posts', ['verified_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_posts_verified_at'), table_name='posts')
    op.drop_column('posts', 'verified_at')
    # 인덱스는 따로 지우지 않는다 — drop_table 이 같이 지우고,
    # 외래키가 쓰는 인덱스를 먼저 지우려 하면 MariaDB 가 거절한다 (1553).
    op.drop_table('post_signals')
    op.drop_table('post_stacks')
