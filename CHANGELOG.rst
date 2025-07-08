0.10.0 2025-07-08
-----------------

* Replace fetch_one with fetch_first and fetch_sole

0.9.0 2024-12-15
----------------

* Add support for a psycopg backend.
* Separate the backend and test connection options.
* Support Python 3.13, drop Python 3.8.

0.8.3 2024-08-29
----------------

* Bugfix correctly support list values (not named).

0.8.2 2024-03-06
----------------

* Bugfix ensure the value of data_loaded is kept.

0.8.1 2024-02-26
----------------

* Bugfix naming typo.
* Bugfix background migrations should not run in a transaction.

0.8.0 2024-02-25
----------------

* Make the valid_migration function optional, if not present the
  migration is assumed to be valid.
* Support background migrations. Note the first deployment should be
  monitored as this requires a change to Quart-DB's state table.
* Bugfix ensure None is returned if there is no result for
  ``fetch_val`` and ``fetch_one``.

0.7.1 2023-10-30
----------------

* Ensure auto request connectons are released.

0.7.0 2023-10-07
----------------

* Add a migrations timeout defaulting to 60s.
* Support Quart 0.19 onwards.
* Support 3.12 drop 3.7.

0.6.2 2023-09-01
----------------

* Bugfix ensure connections are released.

0.6.1 2023-08-23
----------------

* Bugfix add missing f-string designator.

0.6.0 2023-08-10
----------------

* Bugfix ensure aiosqlite works, and specifically type conversion for
  JSON.
* Improve the typing utilising LiteralStrings.
* Allow the state table name to be configured.

0.5.0 2023-05-07
----------------

* Allow postgres as a valid URL scheme alongside postgresql.
* Allow additional options to be passed to the backend db driver.
* Add a db-migrate cli command.
* Bugfix protocol typing for iterate method.
* Bugfix avoid double-close if the pool has already been disconnected.

0.4.1 2022-10-09
----------------

* Bugfix add missing aiosqlite dependency

0.4.0 2022-10-08
----------------

* Support SQLite databases.
* Bugfix ensure that exceptions are not propagated, unless
  specifically set. This prevents connection exhaustion on errors.

0.3.0 2022-08-23
----------------

* Require the connection lock earlier in iterate.
* Acquire the connection lock on Transaction.
* Add a db-schema command to output the entity relation diagram.

0.2.0 2022-04-12
----------------

* Add a lock on connection operations to ensure only one concurrent
  operation per connection (use multiple connections).
* Add a default per request connection on g, so that g.connection can
  be used in request contexts.
* Switch to github rather than gitlab.

0.1.0 2022-03-07
----------------

* Basic initial release.
