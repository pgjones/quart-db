from quart_db import Connection
from .utils import Options


async def test_json_conversion(connection: Connection) -> None:
    id_ = await connection.fetch_val(
        "INSERT INTO tbl (data) VALUES (:data) RETURNING id",
        {"data": {"a": 1}},
    )
    data = await connection.fetch_val("SELECT data FROM tbl WHERE id = :id", {"id": id_})
    assert data == {"a": 1}


async def test_enum_conversion(connection: Connection) -> None:
    id_ = await connection.fetch_val(
        "INSERT INTO tbl (options) VALUES (:options) RETURNING id",
        {"options": Options.B},
    )
    options = await connection.fetch_val("SELECT options FROM tbl WHERE id = :id", {"id": id_})
    assert options == options.B
