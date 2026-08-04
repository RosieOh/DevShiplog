"""조회 기록, 전문검색 인덱스, 비밀번호 재설정, 초안 낙관적 잠금

Revision ID: 0003_views_search_reset
Revises: 0002_blog_platform
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_views_search_reset'
down_revision = '0002_blog_platform'
branch_labels = None
depends_on = None


def _is_mysql() -> bool:
    return op.get_bind().dialect.name in ("mysql", "mariadb")


def upgrade() -> None:
    op.create_table(
        'post_views',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('post_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('viewer_key', sa.String(length=64), nullable=False),
        sa.Column('viewed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'viewer_key', name='unique_post_viewer'),
    )
    op.create_index('ix_post_views_user_time', 'post_views', ['user_id', 'viewed_at'])

    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_password_reset_user', 'password_reset_tokens', ['user_id', 'created_at'])

    op.add_column(
        'draft_versions',
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
    )

    if not _is_mysql():
        return

    """
    전문검색 인덱스.

    LIKE '%키워드%' 는 앞에 와일드카드가 있어 인덱스를 못 탄다. 글이 만 건만 넘어도
    매 검색이 풀스캔이다.

    MySQL 이면 ngram 파서를 쓴다. 기본 파서는 공백으로 단어를 나누는데, 한국어는
    '리액트를' 처럼 조사가 붙어 다녀서 '리액트' 로 검색해도 안 걸린다. ngram 은
    2글자 단위로 쪼개 색인하므로 이 문제를 피한다.

    MariaDB 에는 ngram 파서가 없다(mroonga 같은 플러그인이 필요하다). 대신 기본
    파서로 인덱스를 만들고, 검색할 때 접두 와일드카드('리액트*')로 조사를 흡수한다.
    """
    try:
        op.execute(
            "ALTER TABLE posts ADD FULLTEXT INDEX ft_posts_title_body "
            "(title, summary, content_md) WITH PARSER ngram"
        )
    except Exception:
        op.execute(
            "ALTER TABLE posts ADD FULLTEXT INDEX ft_posts_title_body "
            "(title, summary, content_md)"
        )


def downgrade() -> None:
    if _is_mysql():
        op.execute("ALTER TABLE posts DROP INDEX ft_posts_title_body")
    op.drop_column('draft_versions', 'revision')
    op.drop_index('ix_password_reset_user', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_index('ix_post_views_user_time', table_name='post_views')
    op.drop_table('post_views')
