Testserver
----------

For first tests you can use the simple testserver that is provided with
the *pyads* package. To start it up simply run the following command
from a separate console window.

.. code:: bash

   $ python -m pyads.testserver

This will create a new device on 127.0.0.1 port 48898. In the next step
the route to the testserver needs to be added from another python
console.

.. code:: python

   >>> import pyads
   >>> pyads.add_route("127.0.0.1.1.1", '127.0.0.1')
