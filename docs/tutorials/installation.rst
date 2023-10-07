.. _installation:

Installation
============

Quart-DB is only compatible with Python 3.8 or higher and can be
installed using pip or your favorite python package manager. You will
need to decide which database you wish to connect to as you install,
for example for postgresql:

.. code-block:: sh

    pip install quart-db[postgresql]

Whereas for sqlite:

.. code-block:: sh

    pip install quart-db[sqlite]

Installing quart-db will install Quart if it is not present in your
environment.
