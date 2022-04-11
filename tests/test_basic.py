import os

from quart import g, Quart, ResponseReturnValue

from quart_db import QuartDB


async def test_extension() -> None:
    app = Quart(__name__)
    QuartDB(app, auto_request_connection=True, url=os.environ["DATABASE_URL"])

    @app.get("/")
    async def index() -> ResponseReturnValue:
        return await g.connection.fetch_val("SELECT 'test'")

    async with app.test_app():
        test_client = app.test_client()
        response = await test_client.get("/")
        data = await response.get_data(as_text=True)
    assert data == "test"
