from logging.config import fileConfig

from alembic import context

from app.db import crear_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online() -> None:
    engine = crear_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Las migraciones de EvalAI se ejecutan conectadas a la base (sin --sql).")
run_migrations_online()
