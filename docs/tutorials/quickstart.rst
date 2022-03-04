.. _quickstart:

Quickstart
==========

A simple CRUD API can be written as given below, noting that the
database url should be customised to match your setup.

.. code-block:: python
    :caption: schema.py

    from quart import Quart, request
    from quart_db import QuartDB

    app = Quart(__name__)
    db = QuartDB(app, url="postgresql://username:password@0.0.0.0:5432/db_name")

    @app.get("/")
    async def get_all():
        async with db.connection() as connection:
            results = await connection.fetch_all("SELECT col1, col2 FROM tbl")

        return [{"a": row["col1"], "b": row["col2"]} for row in results]

    @app.post("/")
    async def create():
        data = await request.get_json()
        async with db.connection() as connection:
            await db.execute(
                "INSERT INTO tbl (col1, col2) VALUES (:col1, :col2)",
                {"col1": data["a"], "col2": data["b"]},
            )

        return {}

    @app.get("/<int:id>")
    async def get(id):
        async with db.connection() as connection:
            result = await connection.fetch_one(
                "SELECT col1, col2 FROM tbl WHERE id = :id",
                {"id": id},
            )

        return {"a": result["col1"], "b": result["col2"]}

    @app.delete("/<int:id>")
    async def delete(id):
        async with db.connection() as connection:
            await db.execute("DELETE FROM tbl WHERE id = :id", {"id": id})

        return {}

    @app.put("/<int:id>")
    async def update(id):
        data = await request.get_json()
        async with db.connection() as connection:
            await db.execute(
                "UPDATE tbl SET col1 = :col1, col2 = :col2 WHERE id = :id",
                {"id": id, "col1": data["a"], "col2": data["b"]},
            )

        return {}
