import pytest

from quart_db import Connection, MultipleRowsError, UndefinedParameterError
from quart_db.backends.asyncpg import Connection as AsyncpgConnection
from quart_db.backends.psycopg import Connection as PsycopgConnection


async def test_execute(connection: Connection) -> None:
    await connection.execute("SELECT 1")


async def test_execute_many(connection: Connection) -> None:
    await connection.execute_many(
        "INSERT INTO tbl (value) VALUES (:value)",
        [{"value": 2}, {"value": 3}],
    )
    results = await connection.fetch_all("SELECT value FROM tbl")
    assert [2, 3] == [result["value"] for result in results]


async def test_fetch_first(connection: Connection) -> None:
    await connection.execute(
        "INSERT INTO tbl (value) VALUES (:value)",
        {"value": 2},
    )
    result = await connection.fetch_first("SELECT * FROM tbl")
    assert result["value"] == 2


async def test_fetch_first_list_params(connection: Connection) -> None:
    if isinstance(connection, (AsyncpgConnection, PsycopgConnection)):
        param = "$1"
    else:
        param = "?"
    await connection.execute(f"INSERT INTO tbl (data) VALUES ({param})", [{"A": 2}])
    result = await connection.fetch_first("SELECT * FROM tbl")
    assert result["data"] == {"A": 2}


async def test_fetch_first_no_result(connection: Connection) -> None:
    result = await connection.fetch_first("SELECT * FROM tbl WHERE id = -1")
    assert result is None


async def test_fetch_sole(connection: Connection) -> None:
    await connection.execute(
        "INSERT INTO tbl (value) VALUES (:value)",
        {"value": 3},
    )
    result = await connection.fetch_sole("SELECT * FROM tbl WHERE value = 3")
    assert result["value"] == 3


async def test_fetch_sole_raises(connection: Connection) -> None:
    for _ in range(2):
        await connection.execute(
            "INSERT INTO tbl (value) VALUES (:value)",
            {"value": 3},
        )
    with pytest.raises(MultipleRowsError):
        await connection.fetch_sole("SELECT * FROM tbl WHERE value = 3")


async def test_fetch_sole_no_result(connection: Connection) -> None:
    await connection.execute(
        "INSERT INTO tbl (value) VALUES (:value)",
        {"value": 3},
    )
    result = await connection.fetch_sole("SELECT * FROM tbl WHERE value = 2")
    assert result is None


async def test_fetch_val(connection: Connection) -> None:
    value = await connection.fetch_val("SELECT 2")
    assert value == 2


async def test_fetch_val_no_result(connection: Connection) -> None:
    value = await connection.fetch_val("SELECT id FROM tbl WHERE id = -1")
    assert value is None


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
