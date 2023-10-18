from asyncio import CancelledError
from typing import NoReturn, Type

import pytest
from quart import g, Quart, ResponseReturnValue

from quart_db import QuartDB


async def test_extension(url: str) -> None:
    app = Quart(__name__)
    QuartDB(app, auto_request_connection=True, url=url)

    @app.get("/")
    async def index() -> ResponseReturnValue:
        return await g.connection.fetch_val("SELECT 'test'")

    async with app.test_app():
        test_client = app.test_client()
        response = await test_client.get("/")
        data = await response.get_data(as_text=True)
    assert data == "test"


@pytest.mark.parametrize(
    "exception",
    [CancelledError, ValueError],
)
async def test_g_connection_release(url: str, exception: Type[Exception]) -> None:
    if not url.startswith("sqlite"):
        pytest.skip("aiosqlite - simpler backend to test")

    app = Quart(__name__)
    db = QuartDB(app, auto_request_connection=True, url=url)

    @app.get("/")
    async def index() -> NoReturn:
        raise exception()

    async with app.test_app():
        test_client = app.test_client()
        await test_client.get("/")
    assert db._backend._connections == set()  # type: ignore
