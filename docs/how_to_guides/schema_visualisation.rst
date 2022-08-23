Schema visualisation
====================

The database schema, or entity relations, can be visualised if
Quart-DB is installed with the ``erdiagram`` extra. When installed the
command::

  quart db-schema

can be used to output the schema to ``quart_db_schema.png`` or a
custom file via::

  quart db-schema outputfile.ext

This command uses `eralchemy2
<https://github.com/maurerle/eralchemy2/>`_ to draw the diagrams and
the various formats supported by it are supported. The following
output file extensions are supported,

- '.er': writes to a file the markup to generate an ER style diagram.
- '.dot': returns the graph in the dot syntax.
- '.md': writes to a file the markup to generate an Mermaid-JS style diagram

[This detail is from the eralchemy2 code].
