.. _quickstart:

Quickstart
==========

A simple CRUD API can be written as given below, noting that the
database url should be customised to match your setup (the given URL
creates an in memory sqlite database).

.. code-block:: python
    :caption: schema.py

    from quart import g, Quart, request
    from quart_db import QuartDB

    app = Quart(__name__)
    db = QuartDB(app, url="sqlite:memory:")

    @app.get("/")
    async def get_all():
        results = await g.connection.fetch_all("SELECT col1, col2 FROM tbl")
        return [{"a": row["col1"], "b": row["col2"]} for row in results]

    @app.post("/")
    async def create():
        data = await request.get_json()
        await g.connection.execute(
            "INSERT INTO tbl (col1, col2) VALUES (:col1, :col2)",
            {"col1": data["a"], "col2": data["b"]},
        )
        return {}

    @app.get("/<int:id>")
    async def get(id):
        result = await g.connection.fetch_first(
            "SELECT col1, col2 FROM tbl WHERE id = :id",
            {"id": id},
        )
        return {"a": result["col1"], "b": result["col2"]}

    @app.delete("/<int:id>")
    async def delete(id):
        await g.connection.execute("DELETE FROM tbl WHERE id = :id", {"id": id})
        return {}

    @app.put("/<int:id>")
    async def update(id):
        data = await request.get_json()
        await g.connection.execute(
            "UPDATE tbl SET col1 = :col1, col2 = :col2 WHERE id = :id",
            {"id": id, "col1": data["a"], "col2": data["b"]},
        )
        return {}

Initial migrations
------------------

In the above example it is assumed there is a table named ``tbl`` with
columns ``id``, ``col1`` and ``col2``. If the database does not have a
structure (schema) or you wish to change it, a migration can be
used.

Quart-DB looks for migrations in a ``migrations`` folder that should
be placed alongside the application (as with ``templates``). A example
would be placing the following in ``migrations/0.py``

.. code-block:: python
    :caption: migrations/0.py

    async def migrate(connection):
        await connection.execute(
            "CREATE TABLE tbl (id INT NOT NULL PRIMARY KEY, col1 TEXT, col2 TEXT)"
        )

    async def valid_migration(connection):
        return True

This migration will run once when the application starts. See
:ref:`migrations` for more.
