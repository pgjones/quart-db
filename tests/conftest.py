import os
from typing import AsyncGenerator

import pytest
from quart import Quart

from quart_db import Connection, QuartDB
from .utils import Options


@pytest.fixture(name="connection")
async def _connection() -> AsyncGenerator[Connection, None]:
    db = QuartDB(Quart(__name__), url=os.environ["DATABASE_URL"])
    await db.migrate()

    db.set_converter("options_t", lambda type_: type_.value, Options)
    await db.before_serving()
    async with db.connection() as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
    await db.after_serving()
