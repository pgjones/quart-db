Why not use databases?
======================

Quart-DB has a similar design to `Encode's databases
<https://www.encode.io/databases/>`_ which is a fantastic
library. However, it doesn't support migrations and prefers a singular
implicit connection. This latter design decision causes major issues
in practice (in my view/experience) as seen in this `issue
<https://github.com/encode/databases/issues/456>`_, hence why Quart-DB
exists.
