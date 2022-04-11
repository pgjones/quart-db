Multiple databases
==================

Multiple QuartDB instances can be used to connect to multiple
databases, with an instance per database. Connections should then be
managed explicitly with the ``auto_request_connection`` disabled, as
so,

.. code-block:: python

    read_db = QuartDB(app, url=READ_DB_URL, auto_request_connection=False)
    write_db = QuartDB(app, url=WRITE_DB_URL, auto_request_connection=False)

    @app.get("/")
    async def read():
        async with read_db.connection() as connection:
            await connection.execute("SELECT ...")

    @app.post("/")
    async def write():
        async with write_db.connection() as connection:
            await connection.execute("INSERT INTO ...")
