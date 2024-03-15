Database backends
=================

Quart-DB supports 3 backends, PostgreSQL+asyncpg, PostgreSQL+psycopg,
and SQLite+aiosqlite. The backend used will be chosen based on the
scheme provided in the ``QUART_DB_DATABASE_URL``. To choose
PostgreSQL+asyncpg

================== ========== =========
Scheme             Database   Engine
------------------ ---------- ---------
postgresql+asyncpg PostgreSQL asyncpg
postgresql+psycopg PostgreSQL psycopg
sqlite             SQLite     aiosqlite
================== ========== =========

Note that ``postgresql`` as the scheme will default to
PostgreSQL+asyncpg.
