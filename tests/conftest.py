import os
from typing import AsyncGenerator

import asyncpg
import pytest
from quart import Quart

from quart_db import Connection, QuartDB
from .utils import Options


@pytest.fixture(autouse=True)
async def _setup_db() -> AsyncGenerator[None, None]:
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    await connection.execute("DROP TABLE IF EXISTS tbl")
    await connection.execute("DROP TYPE IF EXISTS options_t")
    await connection.execute("CREATE TYPE options_t AS ENUM ('A', 'B')")
    await connection.execute(
        """CREATE TABLE tbl (
               id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
               data JSON,
               options OPTIONS_T
        )"""
    )
    yield
    await connection.execute("DROP TABLE IF EXISTS tbl")
    await connection.execute("DROP TYPE IF EXISTS options_t")


@pytest.fixture(name="connection")
async def _connection(_setup_db: None) -> AsyncGenerator[Connection, None]:
    db = QuartDB(Quart(__name__), url=os.environ["DATABASE_URL"])
    db.set_converter("options_t", lambda type_: type_.value, Options)
    await db.before_serving()
    async with db.connection() as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
    await db.after_serving()
