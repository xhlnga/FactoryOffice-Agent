from logging.config import fileConfig

from alembic import context
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.models.document_chunk import Vector
import app.models  # noqa: F401  # 导入全部模型，保证 Alembic 能发现表结构。


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# pgvector 是 PostgreSQL 扩展类型。这里注册给 SQLAlchemy 反射层，
# 避免 Alembic 检查迁移漂移时把 vector 字段识别成未知类型。
ischema_names["vector"] = Vector


def get_database_url() -> str:
    """从项目配置读取数据库地址，保证迁移和应用使用同一套配置。"""
    return settings.database_url


def run_migrations_offline() -> None:
    """离线生成 SQL，用于审查迁移脚本。"""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线执行迁移。"""
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
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
