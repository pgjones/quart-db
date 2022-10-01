import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
from quart import Quart

from quart_db import Connection, QuartDB
from .utils import Options


@pytest.fixture(name="url", params=["aiosqlite", "asyncpg"])
def _url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    if request.param == "asyncpg":
        return os.environ["DATABASE_URL"]
    else:
        db_path = tmp_path / "temp.sql"
        return f"sqlite:////{db_path}"


@pytest.fixture(name="connection")
async def _connection(url: str) -> AsyncGenerator[Connection, None]:
    db = QuartDB(Quart(__name__), url=url)

    db.set_converter("options_t", lambda type_: type_.value, Options, pytype=Options)
    await db.before_serving()
    async with db.connection() as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
    await db.after_serving()
