How to execute queries
======================

To execute a single query use ``connection.execute(query, values)`` and
to execute the same query with multiple values use
``connection.execute_many(query, many_values)``. Neither of these
connection-methods return anything.

To execute a query and retreive the result the various ``fetch_`` prefixed
connection-methods can be used. Firstly ``fetch_all(query, values)`` to
retreive all the rows returned by the query. ``fetch_first(query, values)``
to retreive only the first row. ``fetch_sole(query, values)`` to retreive
the only returned row (or raise ``MultipleRowsError`` if there are more
rows). Finally ``fetch_val(query, values)`` to retreive the first row
as a singular value.

If you want to retreive all the rows whilst limiting memory usage,
``iterate(query, values)`` can be used to iterate over the returned
rows. Please note that ``iterate`` takes a lock and hence no other
queries can be used inside the iteration.œ
