Symbols
~~~~~~~

Symbol creation
^^^^^^^^^^^^^^^

Reading from or writing to an ADS variable (= an ADS symbol) can be done even more pythonic
through an :py:class:`.AdsSymbol` instance:

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> plc.open()
   >>> symbol = plc.get_symbol('global.bool_value')

The address and type of the symbol will be automatically determined
using a READ_WRITE request to the ADS server, based on the variable
name. This lookup is skipped when all the information has already been
provided:

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> plc.open()
   # Remaining info will be looked up:
   >>> symbol = plc.get_symbol('global.bool_value')
   # Alternatively, specify all information and no lookup will be done:
   >>> symbol = plc.get_symbol('global.bool_value', index_group=123,
                               index_offset=12345, symbol_type='BOOL')

Here the indices are same as used in :py:meth:`.Connection.read` and :py:meth:`.Connection.write`.
The symbol type is a string of the variable type in PLC-style, e.g. ‘LREAL’, ‘INT’, ‘UDINT’, etc.

.. warning::

  Symbols don't work with structs or lists of structs. But you can use them to address specific
  members of a struct, e.g. `plc.get_symbol("GVL.mydata.ival")`.

Read and write operations
^^^^^^^^^^^^^^^^^^^^^^^^^

Reading from and writing to symbols is straightforward:

.. code:: python

   >>> symbol.read()
   True
   >>> symbol.write(False)
   >>> symbol.read()
   False
   >>> plc.close()

The symbol objects have the ``value`` property, which is the buffered
symbol value:

.. code:: python

   >>> if symbol.read() > 0.5:
   >>>     print(symbol.value)

The example above will perform a single READ request. ``value`` is
updated on every read and write of the symbol. If ``None`` is passed to
:py:meth:`.AdsSymbol.write()` (the default parameter), the buffer will be
written to the target:

.. code:: python

   >>> symbol.write(3.14)

   >>> # Is identical to:
   >>> symbol.value = 3.14
   >>> symbol.write()

The symbol can be set to auto-update the :py:attr:`.AdsSymbol.value` property
through a device notification. See the subsection below.

Device notifications
^^^^^^^^^^^^^^^^^^^^

Notifications (function callbacks) can be attached directly to a symbol:

.. code:: python

   >>> symbol.add_device_notification(my_func)

The symbol will track the handles of the notifications attached to it
and free them up when the object runs out of scope.

You can delete specific notifications or clear all of them:

.. code:: python

   >>> handles = symbol.add_device_notification(my_func)
   >>> symbol.del_device_notification(handles)

   >>> # Or clear all:
   >>> symbol.clear_device_notifications()

:py:meth:`.AdsSymbol.add_device_notification` will automatically create a
notification attribute object with the right variable length. You can also
specify an optional notification attribute and/or user handle:

.. code:: python

   >>> attr = NotificationAttrib(length=sizeof(pyads.PLCTYPE_BOOL), max_delay=1.0, cycle_time=1.0)
   >>> user_handle = 123
   >>> symbol.add_device_notification(my_func, attr=attr, user_handle=user_handle)

Auto-update
^^^^^^^^^^^

A built-in notification is available to automatically update the symbol
buffer based on the remote value. This is disabled by default, enable it
with:

.. code:: python

   >>> symbol.auto_update = True

This will create a new notification callback to update :py:attr:`.AdsSymbol.value`.
This can be efficient if the remote variable changes less frequently
then your code runs. The number of notification callbacks will then be
less than what the number of read operations would have been.

It can be disabled again with:

.. code:: python

   >>> symbol.auto_update = False

Using auto_update will also write the value immediately to the plc when
:py:attr:`.AdsSymbol.value`` is changed.

.. warning::
    Take care that :py:meth:`.AdsSymbol.clear_device_notifications` will *also* remove the
    auto-update notification. Like all symbol notifications, the auto-update
    will be cleared automatically in the object destructor.

