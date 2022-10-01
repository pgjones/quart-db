Convert between Python and Postgres types
=========================================

By default Quart-DB uses the default converters whilst ensuring that
JSON is converted, using the stdlib ``json.loads`` and ``json.dumps``
functions if required. Custom type converters are supported, but
depend on the DB backend used.

Postgres - asyncpg
------------------

To define a custom type converter (also called codecs) can be
specified the ``set_converter`` method can be used. For example for
enums:

.. code-block:: python

    from enum import Enum

    class Options(Enum):
        A = "A"
        B = "B"

    db.set_converter("options_t", lambda type_: type_.value, Options)

The keyword argument ``schema`` can be used to specify the schema to
which the typename belongs.

SQLite - aiosqlite
------------------

To define a custom type converter (also called codecs) can be
specified the ``set_converter`` method can be used. For example for
enums:

.. code-block:: python

    from enum import Enum

    class Options(Enum):
        A = "A"
        B = "B"

    db.set_converter(
        "options_t", lambda type_: type_.value, Options, pytype=Options
    )

Note the ``pytype`` argument is required and the keyword argument
``schema`` has no affect.
