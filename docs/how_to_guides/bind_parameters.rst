Bind parameters
===============

In order to paramterise a query you should use binding parameters and
avoid string formatting. This is particularly important with user
input as string formatting may leave you vulnerable to SQL injection
attacks.

Quart-DB only supports keyword bind parameters with the latter
utilising `buildpg <https://github.com/samuelcolvin/buildpg>`_ for
postgresql databases. The Quart-DB connection instance methods accept
a query (str) and a collection of values as arguments.

A ``UndefinedParameterError`` will be raised if a parameter is
specified in the query without a parameter being provided.

Keyword binds
-------------

Keyword binds are so called as the values are taken by key-name, and
hence should be supplied via a dictionary.

.. code-block:: python

     await connection.execute(
         "SELECT * FROM tbl WHERE a = :a AND b = :b",
         {"a": 1, "b": 2},
     )
