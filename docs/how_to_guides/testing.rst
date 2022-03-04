Testing
=======

Quart-DB uses the Quart startup functionality to connect to the
database and create the connection pool. Therefore the test_app will
need to be used to ensure that the connection is setup for testing as
well, see `the docs
<https://pgjones.gitlab.io/quart/how_to_guides/startup_shutdown.html#testing>`_. To
do so I recommend the following fixture be used with pytest,

.. code-block:: python

    @pytest.fixture(name="app", scope="function")
    async def _app():
        app = create_app()  # Initialize app
        async with app.test_app() as test_app:
            yield test_app

If you would like only a connection for usage in tests I recommend the
following fixture note the ``DATABASE_URL`` is being supplied as a
environment variable,

.. code-block:: python

    @pytest.fixture(name="connection")
    async def _connection():
        asyncpg_connection = await asyncpg.connect(os.environ["DATABASE_URL"])
        connection = Connection(asyncpg_connection)
        async with connection.transaction(force_rollback=True):
            yield connection
        await asyncpg_connection.close()
