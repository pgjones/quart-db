import sqlite3

import pytest

from quart_db import Connection
from quart_db.backends.asyncpg import Connection as AsyncPGConnection
from .utils import Options


@pytest.mark.skipif(sqlite3.sqlite_version < "3.35.0", reason="Requires SQLite 3.35 for RETURNING")
async def test_json_conversion(connection: Connection) -> None:
    id_ = await connection.fetch_val(
        "INSERT INTO tbl (data) VALUES (:data) RETURNING id",
        {"data": {"a": 1}},
    )
    data = await connection.fetch_val("SELECT data FROM tbl WHERE id = :id", {"id": id_})
    assert data == {"a": 1}


async def test_enum_conversion(connection: Connection) -> None:
    if not isinstance(connection, AsyncPGConnection):
        pytest.skip()

    id_ = await connection.fetch_val(
        "INSERT INTO tbl (options) VALUES (:options) RETURNING id",
        {"options": Options.B},
    )
    options = await connection.fetch_val("SELECT options FROM tbl WHERE id = :id", {"id": id_})
    assert options == options.B
