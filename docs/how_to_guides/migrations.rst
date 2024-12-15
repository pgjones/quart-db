.. _migrations:

Migrations
==========

A migration is a change to the database schema (structure) or
data. Migrations are either run before the app starts serving
(foreground) or whilst the app is serving (background). Typically
schema changes are done in foreground and data background migrations,
but this need not be the case.

Quart-DB considers migrations to be linear and forward only, as
such migrations are numbered from 0, to 1, onwards. Each migration is
a python file containing a ``migrate`` function with the following
signature,

.. code-block:: python

    async def migrate(connection: quart_db.Connection) -> None:
        ...

``migrate`` will run before the app starts serving (in the foreground)
and should run whatever queries are required for the migration.

.. warning::

    If you are using postgres Quart-DB will ensure only a single
    invocation of ``migrate`` will occur regardless of the number of
    app instances. This is not possible though with SQLite.

A migration may also include a ``background_migrate`` function for a
migration that runs whilst the app is serving (in the background) with
the following signature,

.. code-block:: python

    async def background_migrate(connection: quart_db.Connection) -> None:
        ...

``background_migrate`` will run whilst the app is serving. Note all
the foreground migrations will complete before the background
migrations start.

.. warning::

    If you are running multiple instances of your app there will be
    multiple instances of ``background_migrate`` running concurrently.

The file can also contain an optional ``valid_migration`` function
with the following signature,

.. code-block:: python

    async def valid_migration(connection: quart_db.Connection) -> bool:
        ...

``valid_migration`` should check that the migration was successful and
the data in the database is as expected. It can be omitted if this is
something you'd prefer to skip.

Transactions
------------

Foreground migrations run in a transaction and hence the migration
code must execute without error and the ``valid_migration`` function
(if present) return True, otherwise the transaction is rolled back.

Background migrations do not run in a transaction, but should be
idempotent to allow Quart-DB to retry if the migration if it is
cancelled by the app shutdown.

Type conversion
---------------

Custom type conversion is not possible in the migration scripts as the
conversion code must be registered before the corresponding type is
created in the migtration.

Invocation
----------

The migrations are automatically invoked during the app
startup. Alternatively it can be invoked via this command::

  quart db-migrate

Note that background migrations are forced to run in the foreground
thereby blocking this command until they finish.
