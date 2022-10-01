Database backends
=================

To connect to a postgresql database the asyncpg backend is used. It is
installed via the ``postgresql`` extra. It will be used if
``QUART_DB_DATABASE_URL`` has ``postgresql`` as the scheme.

To connect to a sqlite database the aiosqlite backend is used. It is
installed via the ``sqlite`` extra.  It will be used if
``QUART_DB_DATABASE_URL`` has ``sqlite`` as the scheme.
