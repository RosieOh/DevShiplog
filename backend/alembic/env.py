from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from src.infrastructure.database.session import Base
from src.infrastructure.config.settings import settings

# autogenerate 가 테이블을 인식하려면 모든 모델이 import 되어 있어야 한다.
import src.infrastructure.database.models  # noqa: F401  (side-effect import)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from settings.
# ConfigParser 는 % 를 보간 문자로 해석하므로 이스케이프한다 (비밀번호에 % 가 있을 수 있다).
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# add your model's MetaData object here
target_metadata = Base.metadata


# 손으로 관리하는 인덱스. autogenerate 비교에서 제외한다.
#
# MySQL 전용 FULLTEXT 인덱스라 모델에 선언할 수 없다(SQLite 테스트에서 깨진다).
# 마이그레이션에서 raw SQL 로 만들기 때문에, 빼두지 않으면 autogenerate 가
# 매번 "없어졌다" 며 지웠다 만드는 마이그레이션을 만들어 낸다.
HAND_MANAGED_INDEXES = {"ft_posts_title_body"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "index" and name in HAND_MANAGED_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

