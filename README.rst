Quart-DB
========

|Build Status| |docs| |pypi| |python| |license|

Quart-DB is a Quart extension that provides managed connection(s) to
postgresql database(s).

Quickstart
----------

Quart-DB is used by associating it with an app and a DB (via a URL),

.. code-block:: python

    from quart import Quart, websocket
    from quart_db import QuartDB

    app = Quart(__name__)
    db = QuartDB(app, url="postgresql://user:pass@localhost:5432/db_name"))

    @app.get("/<int:id>")
    async def get_count(id: int):
        async with db.connection() as connection:
            result = await connection.fetch_val(
                "SELECT COUNT(*) FROM tbl WHERE id = :id",
                {"id": id},
            )
        return {"count": result}

    @app.post("/")
    async def set_with_transaction():
        async with db.connection() as connection:
            async with connection.transaction():
                await db.execute("UPDATE tbl SET done = $1", [True])
                ...
        return {}

Parameters can be defined via positional ``$1`` or keyword ``:id``
binds.

Contributing
------------

Quart-DB is developed on `GitHub
<https://github.com/pgjones/quart-db>`_. If you come across an issue,
or have a feature request please open an `issue
<https://github.com/pgjones/quart-db/issues>`_. If you want to
contribute a fix or the feature-implementation please do (typo fixes
welcome), by proposing a `merge request
<https://github.com/pgjones/quart-db/merge_requests>`_.

Testing
~~~~~~~

The best way to test Quart-DB is with `Tox
<https://tox.readthedocs.io>`_,

.. code-block:: console

    $ pip install tox
    $ tox

this will check the code style and run the tests.

Help
----

The Quart-DB `documentation
<https://quart-db.readthedocs.io/en/latest/>`_ is the best places to
start, after that try searching `stack overflow
<https://stackoverflow.com/questions/tagged/quart>`_ or ask for help
`on gitter <https://gitter.im/python-quart/lobby>`_. If you still
can't find an answer please `open an issue
<https://github.com/pgjones/quart-db/issues>`_.


.. |Build Status| image:: https://github.com/pgjones/quart-db/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/pgjones/quart-db/commits/main

.. |docs| image:: https://readthedocs.org/projects/quart-db/badge/?version=latest&style=flat
   :target: https://quart-db.readthedocs.io/en/latest/

.. |pypi| image:: https://img.shields.io/pypi/v/quart-db.svg
   :target: https://pypi.python.org/pypi/Quart-DB/

.. |python| image:: https://img.shields.io/pypi/pyversions/quart-db.svg
   :target: https://pypi.python.org/pypi/Quart-DB/

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/pgjones/quart-db/blob/main/LICENSE
