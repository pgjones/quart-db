Configuring Quart-DB
====================

The following configuration options are used by Quart-DB. They should
be set as part of the standard `Quart configuration
<https://pgjones.gitlab.io/quart/how_to_guides/configuration.html>`_.

========================== ==== ==========
Configuration key          type default
-------------------------- ---- ----------
QUART_DB_DATABASE_URL      str
QUART_DB_MIGRATIONS_FOLDER str  migrations
QUART_DB_DATA_PATH         str
========================== ==== ==========

``QUART_DB_DATABASE_URL`` allows this database url to be specified and
is ``None`` by default (set via constructor argument).

``QUART_DB_MIGRATIONS_FOLDER`` refers to the location of the
migrations folder relative to the app's root path.

``QUART_DB_DATA_PATH`` refers to the location of the data module
relative to the app's root path.
