"""템플릿, 발행 예약, 작업 단계별 진행률

develop 브랜치의 기능을 main 의 마이그레이션 계보 위에 올린다.
develop 에는 별개의 초기 마이그레이션 계보가 있었지만, 그대로 가져오면
0001 이 만든 테이블을 다시 만들려 하므로 새 테이블만 여기에 다시 썼다.

Revision ID: 0004_templates_schedules
Revises: 0003_views_search_reset
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_templates_schedules'
down_revision = '0003_views_search_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('audience', sa.String(length=50), nullable=True),
        sa.Column('length_preset', sa.String(length=50), nullable=True),
        sa.Column('style_profile_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        # 문체를 지워도 템플릿은 남는다. 문체 없이도 쓸 수 있다.
        sa.ForeignKeyConstraint(['style_profile_id'], ['style_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_templates_user_id'), 'templates', ['user_id'])

    op.create_table(
        'schedules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('draft_id', sa.String(length=36), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED', name='schedulestatus'),
            nullable=True,
        ),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_schedules_user_id'), 'schedules', ['user_id'])
    op.create_index(op.f('ix_schedules_draft_id'), 'schedules', ['draft_id'])
    # 예약 실행 워커가 "지금 보내야 할 것" 을 뽑는 경로.
    op.create_index('ix_schedules_status_time', 'schedules', ['status', 'scheduled_at'])

    # 긴 생성 작업에서 "지금 어디쯤인지" 를 보여주기 위한 값.
    op.add_column('jobs', sa.Column('current_step', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('steps', sa.JSON(), nullable=True))

    # 작성 보조용 메모. 발행물(Post)에는 넘어가지 않는다.
    op.add_column('drafts', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('drafts', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('drafts', sa.Column('checklist', sa.JSON(), nullable=True))
    op.add_column('drafts', sa.Column('generation_log', sa.JSON(), nullable=True))
    op.add_column('drafts', sa.Column('outline', sa.JSON(), nullable=True))


def downgrade() -> None:
    for column in ('outline', 'generation_log', 'checklist', 'notes', 'tags'):
        op.drop_column('drafts', column)
    op.drop_column('jobs', 'steps')
    op.drop_column('jobs', 'current_step')
    # 인덱스는 따로 지우지 않는다 — drop_table 이 같이 지우고,
    # 외래키가 쓰는 인덱스를 먼저 지우려 하면 MariaDB 가 거절한다 (1553).
    op.drop_table('schedules')
    op.drop_table('templates')
