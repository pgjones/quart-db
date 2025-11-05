import os
from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from quart import Quart

from quart_db import Connection, QuartDB
from .utils import Options


@pytest.fixture(name="url", params=["aiosqlite", "asyncpg", "psycopg"])
def _url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    if request.param in ("asyncpg", "psycopg"):
        scheme, *parts = urlsplit(os.environ["DATABASE_URL"])
        scheme = f"postgresql+{request.param}"
        return urlunsplit((scheme, *parts))
    else:
        db_path = tmp_path / "temp.sql"
        return f"sqlite:////{db_path}"


@pytest.fixture(name="connection")
async def _connection(url: str) -> AsyncGenerator[Connection, None]:
    app = Quart(__name__)
    db = QuartDB(app, url=url)

    db.set_converter("options_t", lambda type_: type_.value, Options, pytype=Options)
    await app.startup()
    async with db.connection() as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
    await app.shutdown()
