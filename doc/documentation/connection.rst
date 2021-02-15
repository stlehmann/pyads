Connections
~~~~~~~~~~~

.. important::

    Before starting a connection to a target make sure you created proper routes on the
    client and the target like described in the :doc:`routing` chapter.

Connect to a remote device
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> plc.open()
   >>> plc.close()

The connection will be closed automatically if the object runs out of scope, making
:py:meth:`.Connection.close` optional.

A context notation (using ``with:``) can be used to open a connection:

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> with plc:
   >>>     # ...

The context manager will make sure the connection is closed, either when
the ``with`` clause runs out, or an uncaught error is thrown.

Read and write by name
^^^^^^^^^^^^^^^^^^^^^^^

Values
""""""

Reading and writing values from/to variables on the target can be done with :py:meth:`.Connection.read_by_name` and
:py:meth:`.Connection.write_by_name`. Passing the `plc_datatype` is optional for both methods. If `plc_datatype`
is `None` the datatype will be queried from the target on the first call and cached inside the :py:class:`.Connection`
object. You can disable symbol-caching by setting the parameter `cache_symbol_info` to `False`.

.. warning::
  Querying the datatype only works for basic datatypes.
  For structs, lists and lists of structs you need provide proper definitions of the datatype and use
  :py:meth:`.Connection.read_structure_by_name` or :py:meth:`.Connection.read_list_by_name`.

Examples:

.. code:: python

  >>> import pyads
  >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1):
  >>> plc.open()
  >>>
  >>> plc.read_by_name('GVL.bool_value')  # datatype will be queried and cached
  True
  >>> plc.read_by_name('GVL.bool_value')  # cached datatype will be used
  True
  >>> plc.read_by_name('GVL.bool_value', cache_symbol_info=False)  # datatype will not be cached and queried on each call
  True
  >>> plc.read_by_name('GVL.int_value', pyads.PLCTYPE_INT)  # datatype is provided and will not be queried
  0
  >>> plc.write_by_name('GVL.int_value', 10)  # write to target
  >>> plc.read_by_name('GVL.int_value')
  10

 >>> plc.close()

If the name could not be found an Exception containing the error message
and ADS Error number is raised.

.. code:: python

   >>> plc.read_by_name('GVL.wrong_name', pyads.PLCTYPE_BOOL)
   ADSError: ADSError: symbol not found (1808)

For reading strings the maximum buffer length is 1024.

.. code:: python

   >>> plc.read_by_name('GVL.sample_string', pyads.PLCTYPE_STRING)
   'Hello World'
   >>> plc.write_by_name('GVL.sample_string', 'abc', pyads.PLCTYPE_STRING)
   >>> plc.read_by_name(adr, 'GVL.sample_string', pyads.PLCTYPE_STRING)
   'abc'

Arrays
""""""

You can also read/write arrays. For this you simply need to multiply the
datatype by the number of elements in the array or structure you want to
read/write.

.. code:: python

   >>> plc.write_by_name('global.sample_array', [1, 2, 3], pyads.PLCTYPE_INT * 3)
   >>> plc.read_by_name('global.sample_array', pyads.PLCTYPE_INT * 3)
   [1, 2, 3]

.. code:: python

   >>> plc.write_by_name('global.sample_array[0]', 5, pyads.PLCTYPE_INT)
   >>> plc.read_by_name('global.sample_array[0]', pyads.PLCTYPE_INT)
   5


Structures of the same datatype
"""""""""""""""""""""""""""""""

TwinCAT declaration:

::

   TYPE sample_structure :
   STRUCT
       rVar : LREAL;
       rVar2 : LREAL;
       rVar3 : LREAL;
       rVar4 : ARRAY [1..3] OF LREAL;
   END_STRUCT
   END_TYPE

Python code:

.. code:: python

   >>> plc.write_by_name('global.sample_structure',
                         [11.1, 22.2, 33.3, 44.4, 55.5, 66.6],
                         pyads.PLCTYPE_LREAL * 6)
   >>> plc.read_by_name('global.sample_structure', pyads.PLCTYPE_LREAL * 6)
   [11.1, 22.2, 33.3, 44.4, 55.5, 66.6]

.. code:: python

   >>> plc.write_by_name('global.sample_structure.rVar2', 1234.5, pyads.PLCTYPE_LREAL)
   >>> plc.read_by_name('global.sample_structure.rVar2', pyads.PLCTYPE_LREAL)
   1234.5

Structures with multiple datatypes
""""""""""""""""""""""""""""""""""

**The structure in the PLC must be defined with \`{attribute ‘pack_mode’
:= ‘1’}.**

TwinCAT declaration:

::

   {attribute 'pack mode' := 1}
   TYPE sample_structure :
   STRUCT
       rVar : LREAL;
       rVar2 : REAL;
       iVar : INT;
       iVar2 : ARRAY [1..3] OF DINT;
       sVar : STRING;
   END_STRUCT
   END_TYPE

Python code:

First declare a tuple which defines the PLC structure. This should match
the order as declared in the PLC. Information is passed and returned
using the OrderedDict type.

.. code:: python

   >>> structure_def = (
   ...    ('rVar', pyads.PLCTYPE_LREAL, 1),
   ...    ('rVar2', pyads.PLCTYPE_REAL, 1),
   ...    ('iVar', pyads.PLCTYPE_INT, 1),
   ...    ('iVar2', pyads.PLCTYPE_DINT, 3),
   ...    ('sVar', pyads.PLCTYPE_STRING, 1)
   ... )

   >>> vars_to_write = OrderedDict([
   ...     ('rVar', 11.1),
   ...     ('rar2', 22.2),
   ...     ('iVar', 3),
   ...     ('iVar2', [4, 44, 444]),
   ...     ('sVar', 'abc')]
   ... )

   >>> plc.write_structure_by_name('global.sample_structure', vars_to_write, structure_def)
   >>> plc.read_structure_by_name('global.sample_structure', structure_def)
   OrderedDict([('rVar', 11.1), ('rVar2', 22.2), ('iVar', 3), ('iVar2', [4, 44, 444]), ('sVar', 'abc')])

Read and write by handle
^^^^^^^^^^^^^^^^^^^^^^^^

When reading and writing by name, internally pyads is acquiring a handle
from the PLC, reading/writing the value using that handle, before
releasing the handle. A handle is just a unique identifier that the PLC
associates to an address meaning that should an address change, the ADS
client does not need to know the new address.

It is possible to manage the acquiring, tracking and releasing of
handles yourself, which is advantageous if you plan on reading/writing
the value frequently in your program, or wish to speed up the
reading/writing by up to three times; as by default when reading/writing
by name it makes 3 ADS calls (acquire, read/write, release), where as if
you track the handles manually it only makes a single ADS call.

Using the Connection class:

.. code:: python

   >>> var_handle = plc.get_handle('global.bool_value')
   >>> plc.write_by_name('', True, pyads.PLCTYPE_BOOL, handle=var_handle)
   >>> plc.read_by_name('', pyads.PLCTYPE_BOOL, handle=var_handle)
   True
   >>> plc.release_handle(var_handle)

**Be aware to release handles before closing the port to the PLC.**
Leaving handles open reduces the available bandwidth in the ADS router.

Read and write by address
^^^^^^^^^^^^^^^^^^^^^^^^^

Read and write *UDINT* variables by address.

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> plc.open()
   >>> # write 65536 to memory byte MDW0
   >>> plc.write(INDEXGROUP_MEMORYBYTE, 0, 65536, pyads.PLCTYPE_UDINT)
   >>> # write memory byte MDW0
   >>> plc.read(INDEXGROUP_MEMORYBYTE, 0, pyads.PLCTYPE_UDINT)
   65536
   >>> plc.close()

Toggle bitsize variables by address.

.. code:: python

   >>> # read memory bit MX100.0
   >>> data = plc.read(INDEXGROUP_MEMORYBIT, 100*8 + 0, pyads.PLCTYPE_BOOL)
   >>> # write inverted value to memory bit MX100.0
   >>> plc.write(INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)

Read and write multiple variables with one command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reading and writing of multiple values can be performed in a single
transaction. After the first operation, the symbol info is cached for
future use.

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> var_list = ['MAIN.b_Execute', 'MAIN.str_TestString', 'MAIN.r32_TestReal']
   >>> plc.read_list_by_name(var_list)
   {'MAIN.b_Execute': True, 'MAIN.str_TestString': 'Hello World', 'MAIN.r32_TestReal': 123.45}
   >>> write_dict = {'MAIN.b_Execute': False, 'MAIN.str_TestString': 'Goodbye World', 'MAIN.r32_TestReal': 54.321}
   >>> plc.write_list_by_name(write_dict)
   {'MAIN.b_Execute': 'no error', 'MAIN.str_TestString': 'no error', 'MAIN.r32_TestReal': 'no error'}

Device Notifications
^^^^^^^^^^^^^^^^^^^^

ADS supports device notifications, meaning you can pass a callback that
gets executed if a certain variable changes its state. However as the
callback gets called directly from the ADS DLL you need to extract the
information you need from the ctypes variables which are passed as
arguments to the callback function. A sample for adding a notification
for an integer variable can be seen here:

.. code:: python

   >>> import pyads
   >>> from ctypes import sizeof
   >>>
   >>> # define the callback which extracts the value of the variable
   >>> def callback(notification, data):
   >>>     contents = notification.contents
   >>>     var = next(map(int, bytearray(contents.data)[0:contents.cbSampleSize]))
   >>>
   >>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
   >>> plc.open()
   >>> attr = pyads.NotificationAttrib(sizeof(pyads.PLCTYPE_INT))
   >>>
   >>> # add_device_notification returns a tuple of notification_handle and
   >>> # user_handle which we just store in handles
   >>> handles = plc.add_device_notification('GVL.integer_value', attr, callback)
   >>>
   >>> # To remove the device notification just use the del_device_notication
       # function.
   >>> plc.del_device_notification(*handles)

This examples uses the default values for :py:class:`.NotificationAttrib`. The
default behaviour is that you get notified when the value of the
variable changes on the server. If you want to change this behaviour you
can set the :py:attr:`.NotificationAttrib.trans_mode` attribute to one of the
following values:

* :py:const:`.ADSTRANS_SERVERONCHA` *(default)*
    a notification will be sent everytime the value of the specified variable changes
* :py:const:`.ADSTRANS_SERVERCYCLE`
    a notification will be sent on a cyclic base, the interval is specified by the :py:attr:`cycle_time` property
* :py:const:`.ADSTRANS_NOTRANS`
    no notifications will be sent

For more information about the NotificationAttrib settings have a look
at `Beckhoffs specification of the AdsNotificationAttrib
struct <https://infosys.beckhoff.de/content/1033/tcadsdll2/html/tcadsdll_strucadsnotificationattrib.htm>`__.

**Here are some examples of callbacks for other datatypes:**

.. code:: python

   def callbackBool(notification, data):
           contents = notification.contents
           var = map(bool, bytearray(contents.data)[0:contents.cbSampleSize])[0]

   def callbackInt(notification, data):
           contents = notification.contents
           var = map(int, bytearray(contents.data)[0:contents.cbSampleSize])[0]

   def callbackString(notification, data):
           dest = (c_ubyte * contents.cbSampleSize)()
           memmove(addressof(dest), addressof(contents.data), contents.cbSampleSize)
           # Remove nullbytes
           var = str(bytearray(dest)).split('\x00')[0]

Device Notification callback decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To make the handling of notifications more pythonic a notification
decorator has been introduced in version 2.2.4. This decorator takes
care of converting the ctype values transferred via ADS to python
datatypes.

.. code:: python

   >>> import pyads
   >>> plc = pyads.Connection('127.0.0.1.1.1', 48898)
   >>> plc.open()
   >>>
   >>> @plc.notification(pyads.PLCTYPE_INT)
   >>> def callback(handle, name, timestamp, value):
   >>>     print(
   >>>         '{1}: received new notitifiction for variable "{0}", value: {2}'
   >>>         .format(name, timestamp, value)
   >>>     )
   >>>
   >>> plc.add_device_notification('GVL.intvar', pyads.NotificationAttrib(2),
                                   callback)
   >>> # Write to the variable to trigger a notification
   >>> plc.write_by_name('GVL.intvar', 123, pyads.PLCTYPE_INT)

   2017-10-01 10:41:23.640000: received new notitifiction for variable "GVL.intvar", value: abc

Structures can be read in a this way by requesting bytes directly from
the PLC. Usage is similar to reading structures by name where you must
first declare a tuple defining the PLC structure.

.. code:: python

   >>> structure_def = (
   ...     ('rVar', pyads.PLCTYPE_LREAL, 1),
   ...     ('rVar2', pyads.PLCTYPE_REAL, 1),
   ...     ('iVar', pyads.PLCTYPE_INT, 1),
   ...     ('iVar2', pyads.PLCTYPE_DINT, 3),
   ...     ('sVar', pyads.PLCTYPE_STRING, 1))
   >>>
   >>> size_of_struct = pyads.size_of_structure(structure_def)
   >>>
   >>> @plc.notification(size_of_struct)
   >>> def callback(handle, name, timestamp, value):
   ...     values = pyads.dict_from_bytes(value, structure_def)
   ...     print(values)
   >>>
   >>> attr = pyads.NotificationAttrib(ctypes.sizeof(size_of_struct))
   >>> plc.add_device_notification('global.sample_structure', attr, callback)

   OrderedDict([('rVar', 11.1), ('rVar2', 22.2), ('iVar', 3), ('iVar2', [4, 44, 444]), ('sVar', 'abc')])

The notification callback works for all basic plc datatypes but not for
arrays. Since version 3.0.5 the ``ctypes.Structure`` datatype is
supported. Find an example below:

.. code:: python

   >>> class TowerEvent(Structure):
   >>>     _fields_ = [
   >>>         ("Category", c_char * 21),
   >>>         ("Name", c_char * 81),
   >>>         ("Message", c_char * 81)
   >>>     ]
   >>>
   >>> @plc.notification(TowerEvent)
   >>> def callback(handle, name, timestamp, value):
   >>>     print(f'Received new event notification for {name}.Message = {value.Message}')
