Why not a connection per request?
=================================

Quart-DB does not automatically provide a connection per request as
each connection is taken from a pool and hence the request could
potentially block until a connection in the pool is available. This
would limit the concurrency to the pool size.

In general Quart-DB attempts to be explicit about connection usage as
this should make the code easier to reason about and less likely to
introduce side affects.

Snippet for adding a connection to g
------------------------------------

The following can be used to provide a per request connection on
``g``,

.. code-block:: python

    from quart import g

    @app.before_request
    @app.before_websocket
    async def acquire_connection():
        g.connection = await db.acquire()

    @app.after_request
    @app.after_websocket
    async def release_connection(response):
        if getattr(g, "connection", None) is not None:
            await db.release(g.connection)
        g.connection = None
        return response
