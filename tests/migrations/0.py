from quart_db import Connection
from quart_db.backends.asyncpg import Connection as AsyncPGConnection


async def migrate(connection: Connection) -> None:
    await connection.execute("DROP TABLE IF EXISTS tbl")
    if not isinstance(connection, AsyncPGConnection):
        await connection.execute(
            """CREATE TABLE tbl (
                   id INTEGER PRIMARY KEY,
                   data JSON,
                   value INTEGER
            )"""
        )
    else:
        await connection.execute("DROP TYPE IF EXISTS options_t")
        await connection.execute("CREATE TYPE options_t AS ENUM ('A', 'B')")
        await connection.execute(
            """CREATE TABLE tbl (
                   id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                   data JSON,
                   value INT,
                   options OPTIONS_T
            )"""
        )


async def valid_migration(connection: Connection) -> bool:
    return True
