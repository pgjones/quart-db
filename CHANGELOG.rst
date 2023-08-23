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
