import importlib.util
from pathlib import Path
from typing import Optional

from .interfaces import ConnectionABC


class MigrationFailedError(Exception):
    pass


async def setup_schema(
    connection: ConnectionABC,
    migrations_path: Optional[Path],
    data_file: Optional[Path],
    state_table_name: str,
) -> None:
    await _create_migration_table(connection, state_table_name)

    for_update = "FOR UPDATE" if connection.supports_for_update else ""

    while migrations_path is not None:
        async with connection.transaction():
            migration = await connection.fetch_val(
                f"SELECT version FROM {state_table_name} {for_update}"
            )
            migration += 1
            try:
                await _run_migration(connection, migration, migrations_path)
            except FileNotFoundError:
                if migration > 0 and not (migrations_path / f"{migration - 1}.py").exists():
                    raise MigrationFailedError("Database is ahead of local migrations") from None
                else:
                    break
            else:
                await connection.execute(
                    f"UPDATE {state_table_name} SET version = :version",
                    values={"version": migration},
                )

    async with connection.transaction():
        data_loaded = await connection.fetch_val(
            f"SELECT data_loaded FROM {state_table_name} {for_update}"
        )
        if not data_loaded and data_file is not None:
            try:
                await _run_data(connection, data_file)
            except Exception:
                raise MigrationFailedError("Error loading data")
            else:
                await connection.execute(f"UPDATE {state_table_name} SET data_loaded = TRUE")


async def _create_migration_table(connection: ConnectionABC, state_table_name: str) -> None:
    await connection.execute(
        f"""CREATE TABLE IF NOT EXISTS {state_table_name} (
               onerow_id BOOL PRIMARY KEY DEFAULT TRUE,
               data_loaded BOOL NOT NULL,
               version INTEGER NOT NULL,

               CONSTRAINT onerow_uni CHECK (onerow_id)
           )""",
    )
    await connection.execute(
        f"""INSERT INTO {state_table_name} (data_loaded, version)
                 VALUES (FALSE, -1)
            ON CONFLICT DO NOTHING"""
    )


async def _run_migration(connection: ConnectionABC, migration: int, migrations_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        f"quart_db_{migration}", migrations_path / f"{migration}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.migrate(connection)
    valid = await module.valid_migration(connection)
    if not valid:
        raise MigrationFailedError(f"Migration {migration} is not valid")


async def _run_data(connection: ConnectionABC, path: Path) -> None:
    spec = importlib.util.spec_from_file_location("quart_db_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.execute(connection)
