Migrations
==========

Quart-DB considers migrations to be linear and forward only, as such
migrations are numbered from 0, to 1, onwards. Each migration is a
python file containing two functions, the first ``migrate`` has the
following signature,

.. code-block:: python

    async def migrate(connection: quart_db.Connection) -> None:
        ...

``migrate`` should run whatever queries are required for the
migration.

The second ``valid_migration`` has the following signature,

.. code-block:: python

    async def valid_migration(connection: quart_db.Connection) -> bool:
        ...

``valid_migration`` should check that the migration was successful and
the data in the database is as expected. It can just ``return True``
if this is something you'd prefer to skip.

Transactions
------------

Migrations run in a transaction and hence the migration code must
execute without error and the ``valid_migration`` function return True, otherwise
the transaction is rolled back.

Type conversion
---------------

Custom type conversion is not possible in the migration scripts as the
conversion code must be registered before the corresponding type is
created in the migtration.
