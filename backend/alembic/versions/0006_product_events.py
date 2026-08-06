"""제품 지표용 이벤트

신선도 기능이 값어치가 있는지 판단할 근거를 남긴다.
"쓸 만해 보인다" 는 판단 근거가 아니다 — 접을지 말지를 정하려면 수가 있어야 한다.

Revision ID: 0006_product_events
Revises: 0005_tech_stack_freshness
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_product_events'
down_revision = '0005_tech_stack_freshness'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'product_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('post_id', sa.String(length=36), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_product_events_name_time', 'product_events', ['name', 'created_at'])
    op.create_index('ix_product_events_post', 'product_events', ['post_id', 'name'])

    # 새 알림 종류. MySQL 의 ENUM 은 값을 늘리려면 컬럼을 다시 정의해야 한다.
    op.execute(
        "ALTER TABLE notifications MODIFY COLUMN type "
        "ENUM('COMMENT','REPLY','LIKE','FOLLOW','SIGNAL_BROKEN') NOT NULL"
    ) if op.get_bind().dialect.name in ("mysql", "mariadb") else None


def downgrade() -> None:
    if op.get_bind().dialect.name in ("mysql", "mariadb"):
        op.execute(
            "ALTER TABLE notifications MODIFY COLUMN type "
            "ENUM('COMMENT','REPLY','LIKE','FOLLOW') NOT NULL"
        )
    op.drop_table('product_events')
