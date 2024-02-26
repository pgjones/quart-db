import importlib.util
from pathlib import Path
from types import ModuleType
from typing import AsyncGenerator, Literal

from .interfaces import BackendABC, ConnectionABC


class MigrationFailedError(Exception):
    pass


async def execute_foreground_migrations(
    backend: BackendABC,
    migrations_path: Path,
    state_table_name: str,
) -> None:
    connection = await backend._acquire_migration_connection()
    try:
        async for module in _migration_generator(
            connection, "foreground", migrations_path, state_table_name
        ):
            await module.migrate(connection)
            valid = not hasattr(module, "valid_migration") or await module.valid_migration(
                connection
            )
            if not valid:
                raise MigrationFailedError(f"Migration {module.__name__} is not valid")
    finally:
        await backend._release_migration_connection(connection)


async def execute_background_migrations(
    backend: BackendABC,
    migrations_path: Path,
    state_table_name: str,
) -> None:
    connection = await backend._acquire_migration_connection()
    try:
        async for module in _migration_generator(
            connection, "background", migrations_path, state_table_name
        ):
            migrate = getattr(module, "background_migrate", None)
            if migrate is not None:
                await migrate(connection)
    finally:
        await backend._release_migration_connection(connection)


async def execute_data_loader(
    backend: BackendABC,
    data_path: Path,
    state_table_name: str,
) -> None:
    connection = await backend._acquire_migration_connection()
    try:
        for_update = "FOR UPDATE" if connection.supports_for_update else ""

        async with connection.transaction():
            data_loaded = await connection.fetch_val(
                f"SELECT data_loaded FROM {state_table_name} {for_update}"
            )
            if not data_loaded:
                module = _load_module("quart_db_data", data_path)
                try:
                    await module.execute(connection)
                except Exception:
                    raise MigrationFailedError("Error loading data")
                else:
                    await connection.execute(f"UPDATE {state_table_name} SET data_loaded = TRUE")
    finally:
        await backend._release_migration_connection(connection)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _migration_generator(
    connection: ConnectionABC,
    type_name: Literal["foreground", "background"],
    migrations_path: Path,
    state_table_name: str,
) -> AsyncGenerator[ModuleType, None]:
    for_update = "FOR UPDATE" if connection.supports_for_update else ""

    while True:
        async with connection.transaction():
            migration = await connection.fetch_val(
                f"SELECT {type_name} FROM {state_table_name} {for_update}"
            )
            migration += 1
            migration_path = migrations_path / f"{migration}.py"
            try:
                module = _load_module(f"quart_db_{migration}", migration_path)
            except FileNotFoundError:
                if migration > 0 and not (migrations_path / f"{migration - 1}.py").exists():
                    raise MigrationFailedError("Database is ahead of local migrations") from None
                else:
                    return

            yield module

            await connection.execute(
                f"UPDATE {state_table_name} SET {type_name} = :migration",
                values={"migration": migration},
            )


async def ensure_state_table(backend: BackendABC, state_table_name: str) -> None:
    connection = await backend._acquire_migration_connection()

    # This is required to migrate previous state version tables
    try:
        version = await connection.fetch_val(f"SELECT version FROM {state_table_name}")
    except Exception:  # Either table or column "version" does not exist
        version = -1
    else:  # "version" does exist => old table structure
        await connection.execute(f"DROP TABLE {state_table_name}")

    try:
        await connection.execute(
            f"""CREATE TABLE IF NOT EXISTS {state_table_name} (
                   onerow_id BOOL PRIMARY KEY DEFAULT TRUE,
                   background INTEGER NOT NULL,
                   data_loaded BOOL NOT NULL,
                   foreground INTEGER NOT NULL,

                   CONSTRAINT onerow_uni CHECK (onerow_id)
               )""",
        )
        await connection.execute(
            f"""INSERT INTO {state_table_name} (background, data_loaded, foreground)
                     VALUES (:version, FALSE, :version)
                ON CONFLICT DO NOTHING""",
            {"version": version},
        )
    finally:
        await backend._release_migration_connection(connection)
