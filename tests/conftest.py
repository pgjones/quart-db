import os
from typing import AsyncGenerator

import pytest

from quart import Quart
from quart_db import Connection, QuartDB


@pytest.fixture(name="connection")
async def _connection() -> AsyncGenerator[Connection, None]:
    db = QuartDB(Quart(__name__), url=os.environ["DATABASE_URL"])
    await db.before_serving()
    async with db.connection() as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
    await db.after_serving()


@pytest.fixture(autouse=True)
async def _setup_db(connection: Connection) -> None:
    await connection.execute("CREATE TABLE tbl (id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY)")
