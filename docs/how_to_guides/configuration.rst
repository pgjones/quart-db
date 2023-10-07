Configuring Quart-DB
====================

The following configuration options are used by Quart-DB. They should
be set as part of the standard `Quart configuration
<https://pgjones.gitlab.io/quart/how_to_guides/configuration.html>`_.

================================ ============ ================
Configuration key                type         default
-------------------------------- ------------ ----------------
QUART_DB_DATABASE_URL            str
QUART_DB_MIGRATIONS_FOLDER       str          migrations
QUART_DB_DATA_PATH               str
QUART_DB_AUTO_REQUEST_CONNECTION bool
QUART_DB_MIGRATION_TIMEOUT       float | None 60
QUART_DB_STATE_TABLE_NAME        str          schema_migration
================================ ============ ================

``QUART_DB_DATABASE_URL`` allows this database url to be specified and
is ``None`` by default (set via constructor argument).

``QUART_DB_MIGRATIONS_FOLDER`` refers to the location of the
migrations folder relative to the app's root path. You can set
this to `None` in order to disable the migrations system.

``QUART_DB_DATA_PATH`` refers to the location of the data module
relative to the app's root path.

``QUART_DB_AUTO_REQUEST_CONNECTION`` can be used to disable (when
False) the automatic ``g.connection`` connection per request.

``QUART_DB_STATE_TABLE_NAME`` can be used to change the table Quart-DB
uses to store the database migration state.

``QUART_DB_MIGRATION_TIMEOUT`` sets the maximum time the migrations
may take. Note that most ASGI servers will also timeout the startup
phase as well. This can be disabled by setting the value to ``None``.


SQLite configuration
--------------------

To use a relative path ``QUART_DB_DATABASE_URL`` should start with
``sqlite:///``, whereas for an absolute path it should start with
``sqlite:////``. In memory usage should be avoided as changes will not
be persisted.
