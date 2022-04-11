Why a connection per request?
=============================

Quart-DB automatically provides a connection per request from the pool
even if the connection is never used. This means that the request
request could potentially block until a connection in the pool is
available and hence limits the concurrency to the pool size.

This decision is made on basis that most uses of QuartDB will gain
from the conveniance of using ``g.connection`` as the usage is for a
single database with most/all routes using a connection.

This can be disabled as desired by setting the
``auto_request_connection`` constructor argument to False or setting
the ``QUART_DB_AUTO_REQUEST_CONNECTION`` configuration value to False.
