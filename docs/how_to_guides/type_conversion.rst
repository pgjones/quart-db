Convert between Python and Postgres types
=========================================

By default Quart-DB uses asyncpg's `built in type conversion
<https://magicstack.github.io/asyncpg/current/usage.html#type-conversion>`_
for simple types and converts the ``json`` and ``jsonb`` postgres
types to Python types using ``json.dumps`` and ``json.loads``. This
should be sufficient in most cases, however where it is not custom
type converters (also called codecs) can be specified. For example the
``json`` converter can be set via,

.. code-block:: python

    db = QuartDB(...)

    db.set_converter("json", json.dumps, json.loads)


Another common example is to convert between Python and Postgres enums
which can be done via the following,

.. code-block:: python

    from enum import Enum

    class Options(Enum):
        A = "A"
        B = "B"

    db.set_converter("options_t", lambda type_: type_.value, Options)
