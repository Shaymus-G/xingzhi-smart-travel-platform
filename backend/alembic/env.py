import sys
import os
from logging.config import fileConfig
from urllib.parse import quote_plus

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 将 backend 根目录加入 sys.path，确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入所有 Model，确保 Alembic 能扫描到
from app.core.database import Base  # noqa: E402
from app.models import *  # noqa: E402, F403

# target_metadata 指向 Base.metadata
target_metadata = Base.metadata

# 从应用配置读取数据库 URL，覆盖 alembic.ini 中的占位符
from app.core.config import settings  # noqa: E402


def get_database_url() -> str:
    return (
        f"mysql+pymysql://"
        f"{quote_plus(settings.MYSQL_USER)}:"
        f"{quote_plus(settings.MYSQL_PASSWORD)}@"
        f"{settings.MYSQL_HOST}:"
        f"{settings.MYSQL_PORT}/"
        f"{settings.MYSQL_DATABASE}"
        "?charset=utf8mb4"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
