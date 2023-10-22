import pytest

from quart_db import Connection, UndefinedParameterError


async def test_execute(connection: Connection) -> None:
    await connection.execute("SELECT 1")


async def test_execute_many(connection: Connection) -> None:
    await connection.execute_many(
        "INSERT INTO tbl (value) VALUES (:value)",
        [{"value": 2}, {"value": 3}],
    )
    results = await connection.fetch_all("SELECT value FROM tbl")
    assert [2, 3] == [result["value"] for result in results]


async def test_fetch_one(connection: Connection) -> None:
    await connection.execute(
        "INSERT INTO tbl (value) VALUES (:value)",
        {"value": 2},
    )
    result = await connection.fetch_one("SELECT * FROM tbl")
    assert result["value"] == 2


async def test_fetch_val(connection: Connection) -> None:
    value = await connection.fetch_val("SELECT 2")
    assert value == 2


async def test_iterate(connection: Connection) -> None:
    await connection.execute_many(
        "INSERT INTO tbl (value) VALUES (:value)",
        [{"value": 2}, {"value": 3}],
    )
    assert [2, 3] == [
        result["value"] async for result in connection.iterate("SELECT value FROM tbl")
    ]


async def test_transaction(connection: Connection) -> None:
    async with connection.transaction():
        await connection.execute("SELECT 1")


async def test_transaction_rollback(connection: Connection) -> None:
    try:
        async with connection.transaction():
            await connection.execute("INSERT INTO tbl (value) VALUES (:value)", {"value": 2})
            raise Exception()
    except Exception:
        pass
    rows = await connection.fetch_val("SELECT COUNT(*) FROM tbl")
    assert rows == 0


async def test_missing_bind(connection: Connection) -> None:
    with pytest.raises(UndefinedParameterError) as exc:
        await connection.execute("SELECT * FROM tbl WHERE id = :id", {"a": 2})
    assert "id" in str(exc.value)
