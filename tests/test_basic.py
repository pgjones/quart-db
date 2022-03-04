import pytest

from quart_db import Connection, UndefinedParameterError


async def test_execute(connection: Connection) -> None:
    await connection.execute("SELECT 1")


async def test_fetch_val(connection: Connection) -> None:
    value = await connection.fetch_val("SELECT 2")
    assert value == 2


async def test_transaction(connection: Connection) -> None:
    async with connection.transaction():
        await connection.execute("SELECT 1")


async def test_missing_bind(connection: Connection) -> None:
    with pytest.raises(UndefinedParameterError) as exc:
        await connection.execute("SELECT * FROM tbl WHERE id = :id")
    assert "id" in str(exc.value)

    with pytest.raises(UndefinedParameterError) as exc:
        await connection.execute("SELECT * FROM tbl WHERE id = $1")
    assert "$1" in str(exc.value)
