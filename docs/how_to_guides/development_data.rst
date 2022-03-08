Development & testing data
==========================

It is often desired to load an initial set of data into the database
often for developing against or testing against. You can do this by
specifying the ``data_path`` either by the constructor argument or via
the ``QUART_DB_DATA_PATH`` configuration variable. The path should be
relative to the app's root and contain a function with the following
signature,

.. code-block:: python

    async def execute(connection: quart_db.Connection) -> None:
        ...

The data will only be into the database loaded once, after any
migrations have completed.
