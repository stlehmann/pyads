Testserver
==========

The testserver was created initially for internal testing. However,
you can also use the testserver to test your application. Use it when no
real ADS server is available, for example during continuous integration or
when TwinCAT is not installed.

You can run a basic testserver with the command:

.. code:: bash

   $ python -m pyads.testserver --handler basic

The handler type defaults to 'advanced'.

This will create a new device on 127.0.0.1 port 48898. In the next step
the route to the testserver needs to be added from another python
console.

.. code:: python

   >>> import pyads
   >>> pyads.add_route("127.0.0.1.1.1", "127.0.0.1")

.. warning::

   The testserver functionality was originally intended only for internal
   testing. The documentation and any support are not guaranteed.

Handlers
--------

The server is a `socket.socket` listener, that listens to ADS-like connections and
sends responses to requests. :class:`~pyads.testserver.testserver.AdsTestServer`
itself does not manage the requests and responses. Those are managed by handler
classes. Currently there are two handlers available:

 * :class:`~pyads.testserver.basic_handler.BasicHandler` always returns the same static responses. No data can be saved, any returned values are always 0.
 * :class:`~pyads.testserver.advanced_handler.AdvancedHandler` keeps a list of variables and allows for reading/writing variables. Variables need to be created upfront via :meth:`~pyads.testserver.advanced_handler.AdvancedHandler.add_variable`.

Your requirements determine which handler is most suitable. You can also create your own handler by extending the
:class:`~pyads.testserver.handler.AbstractHandler` class. Typically, the basic handler will require the least amount
of work.

A complete overview of the capabilities of the handlers is below. If a feature is
mocked, it will do nothing but no error will be thrown when it is executed. If a
feature is not implemented, an error will be thrown when an attempt is made to use
the feature.

.. list-table:: Handler implementations
   :widths: 50 25 25
   :header-rows: 1

   * - | Feature
       | (Methods from :class:`~pyads.ads.Connection`)
     - :class:`~pyads.testserver.basic_handler.BasicHandler`
     - :class:`~pyads.testserver.advanced_handler.AdvancedHandler`
   * - `read_state`
     - Mocked
     - Mocked
   * - `write_control`
     - Mocked
     - Mocked
   * - `read_device_info`
     - Mocked
     - Mocked
   * - `read`
     - Mocked
     - Implemented
   * - `write`
     - Mocked
     - Implemented
   * - `read_by_name`
     - Mocked
     - Implemented
   * - | `read_by_name`
       | (with handle)
     - Mocked
     - Implemented
   * - `write_by_name`
     - Mocked
     - Implemented
   * - | `write_by_name`
       | (with handle)
     - Mocked
     - Implemented
   * - `get_symbol`
     - | Mocked (no info will
       | be found automatically)
     - Implemented
   * - `get_all_symbols`
     - | Mocked (list will
       | always be empty)
     - Implemented
   * - `get_handle`
     - Mocked
     - Implemented
   * - `release_handle`
     - Mocked
     - Mocked
   * - `read_list_by_name`
     - Mocked
     - Implemented
   * - `write_list_by_name`
     - Mocked
     - Implemented
   * - `read_structure_by_name`
     - Mocked
     - Not implemented
   * - `write_structure_by_name`
     - Mocked
     - Not implemented
   * - `add_device_notification`
     - Mocked
     - Implemented
   * - `del_device_notification`
     - Mocked
     - Implemented
   * - Device notifications
     - | Not implemented (callbacks
       | will never fire)
     - Implemented

Basic Handler
*************

The :class:`~pyads.testserver.basic_handler.BasicHandler` just responds with `0x00` wherever possible. Trying to
read any byte or integer will always always net 0. Trying to read an LREAL
for example will give 2.09e-308, as that is the interpretation of all bits
at 0.

Actions like writing to a variable or adding a notification will always be
successful, but they won't have any effect.

Advanced Handler
****************

The :class:`~pyads.testserver.advanced_handler.AdvancedHandler` keeps track of variables in an internal list. You can
read from and write to those variables like you would with a real server, using
either the indices, name or variable handle. Any notifications will be issued
as expected too. The handler keeps a list of variables with the type :class:`~pyads.testserver.advanced_handler.PLCVariable`.
In order to address a variable you need to explicitly create it first:

.. code:: python

   # Server code

   handler = AdvancedHandler()

   test_var = PLCVariable(
       "Main.my_var", bytes(8), ads_type=constants.ADST_REAL64, symbol_type="LREAL"
   )
   handler.add_variable(test_var)


.. code:: python

   # Client code

   with plc:
       sym = plc.get_symbol("Main.my_var")  # Already exists remotely
       print(sym)
       print(sym.read())
