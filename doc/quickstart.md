# Quickstart

Make sure you followed the installation instructions before carrying on.

## Creating routes

ADS uses its own address system named AmsNetId to identify devices. The
assignment of a devices to an AmsNetId happens via routing. Routing
is handled differently on Windows and Linux.

### Creating routes on Linux

Open a port and create an AmsAddr object for the remote machine.

```python
>>> import pyads
>>> pyads.open_port()
32828
```

Add a route to the remote machine (Linux only - Windows routes must be
added in the TwinCat Router UI).

```python
>>> pyads.add_route("192.168.0.100.1.1", "192.168.0.100")
```

A better option is to use the Connection class.
```python
>>> import pyads
>>> remote_ip = '192.168.0.100'
>>> remote_ads = '5.12.82.20.1.1'
>>> with pyads.Connection(remote_ads, pyads.PORT_SPS1, remote_ip) as plc:
>>>     plc.read_by_name('.TAG_NAME', pyads.PLCTYPE_INT)
```

Get the AMS address of the local machine. This may need to be added to
the routing table of the remote machine.
**NOTE: On Linux machines at least one route must be added before the call
to `get_local_address()` will function properly.**

Optionally, a local AmsNetId can be manually set before adding a route.
Set this to match the expected AMS ID in the remote machine's routing table.
```python
>>> import pyads
>>> pyads.open_port()
>>> pyads.set_local_address('1.2.3.4.1.1')
>>> pyads.close_port()
```

### Adding routes to a PLC on Linux
Beckhoff PLCs require that a route be added to the routing table of the PLC. On Windows this is handled in the TwinCAT router, but on Linux there is no such option.
This only needs to be done once when initially setting up a connection to a remote PLC.

Adding a route to a remote PLC to allow connections to a PC with the Hostname "MyPC"
```python
>>> import pyads
>>> SENDER_AMS = '1.2.3.4.1.1'
>>> PLC_IP = '192.168.0.100'
>>> PLC_USERNAME = 'plc_username'
>>> PLC_PASSWORD = 'plc_password'
>>> ROUTE_NAME = 'RouteToMyPC'
>>> HOSTNAME = 'MyPC'  # or IP
>>> PLC_AMS_ID = '11.22.33.44.1.1'
>>> pyads.add_route_to_plc(SENDER_AMS, HOSTNAME, PLC_IP, PLC_USERNAME, PLC_PASSWORD, route_name=ROUTE_NAME)
```

### Creating routes on Windows

On Windows you don't need to manually add the routes with pyads but instead you
use the TwinCAT Router UI (TcSystemManager) which comes with the TwinCAT
installation. Have a look at the TwinCAT documentation
[infosys.beckhoff.com TcSystemManager][0] for further details.

## Testserver

For first tests you can use the simple testserver that is provided with
the *pyads* package. To start it up simply run the following command from
a separate console window.

```bash
$ python -m pyads.testserver
```

This will create a new device on 127.0.0.1 port 48898. In the next step
the route to the testserver needs to be added from another python console.

```python
>>> import pyads
>>> pyads.add_route("127.0.0.1.1.1", '127.0.0.1')
```

## Usage

### Connect to a remote device

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
>>> plc.close()
```

### ADS Symbol

#### Symbol creation

Reading from or writing to an ADS variable (= an ADS symbol) can be done through an `AdsSymbol` instance:

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
>>> symbol = plc.get_symbol('global.bool_value')
```

The address and type of the symbol will be automatically determined using a READ_WRITE request to the ADS server, based on the variable name. This lookup is skipped when all the information has already been provided:

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
# Remaining info will be looked up:
>>> symbol = plc.get_symbol('global.bool_value')
# Alternatively, specify all information and no lookup will be done:
>>> symbol = plc.get_symbol('global.bool_value', index_group=123,
                            index_offset=12345, symbol_type='BOOL')
```

Here the indices are same as used in `plc.read()` and `plc.write()`. The symbol type is a string of the variable type in PLC-style, e.g. 'LREAL', 'INT', 'UDINT', etc.

#### Read and write through symbols

Reading from and writing to symbols is straightforward:

```python
>>> symbol.read()
True
>>> symbol.write(False)
>>> symbol.read()
False
>>> plc.close()
```

The symbol objects have the `value` property, which is the buffered symbol value:

```python
if symbol.read() > 0.5:
    print(symbol.value)
```

The example above will perform a single READ request. `value` is updated on every read and write of the symbol.  
When `None` is passed to `symbol.write()` (the default parameter), the buffer will be written:

```python
symbol.write(3.14)

# Is identical to:
symbol.value = 3.14
symbol.write()
```

The symbol can be set to auto-update through a device notification. See the subsection below.

#### Device notifications through symbols

Notifications (function callbacks) can also be attached directly to a symbol:

```python
symbol.add_device_notification(my_func)
```

The symbol will track the handles of the notifications attached to it and free them up when the object runs out of scope.

You can delete specific notifications or clear all of them:

```python
handles = symbol.add_device_notification(my_func)
symbol.del_device_notification(handles)

# Or clear all:
symbol.clear_device_notifications()
```

`symbol.add_device_notification` will automatically create a notification attribute object with the right variable length.

Like `plc.add_device_notification()`, through the symbol interface you can also specify an optional notification attribute and/or user handle:

```python
attr = NotificationAttrib(length=sizeof(pyads.PLCTYPE_BOOL), max_delay=1.0, cycle_time=1.0)
user_handle = 123
symbol.add_device_notification(my_func, attr=attr, user_handle=user_handle)
```

#### Auto-update

A built-in notification is available to automatically update the symbol buffer based on the remote value. This is disabled by default, enable it with:

```python
symbol.auto_update = True
```

This will create a new notification callback to update `symbol.value`. This can be efficient if the remote variable changes less frequently then your code runs. The number of notification callbacks will then be less than what the number of read operations would have been. 

It can be disabled again with:

```python
symbol.auto_update = False
```

Using auto_update will also write the value immediately to the plc when `symbol.value` is changed.

Take care that `symbol.clear_notifications()` will *also* remove the auto-update notification. Like all symbol notifications, the auto-update will also be cleared automatically in the object destructor.

The connection will also be closed automatically when the object runs out of scope, making `plc.close()` optional.

A context notation (using `with:`) can also be used to open the connection:

```python
import pyads
plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
with plc:
    # ...
```

The context manager will make sure the connection is closed, either when the `with` clause runs out, or an uncaught error is thrown.

### Read and write values by name

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
>>> plc.read_by_name('global.bool_value', pyads.PLCTYPE_BOOL)
True
>>> plc.write_by_name('global.bool_value', False, pyads.PLCTYPE_BOOL)
>>> plc.read_by_name('global.bool_value', pyads.PLCTYPE_BOOL)
False
>>> plc.close()
```

If the name could not be found an Exception containing the error message and ADS Error number is raised.

```python
>>> plc.read_by_name('global.wrong_name', pyads.PLCTYPE_BOOL)
ADSError: ADSError: symbol not found (1808)
```

For reading strings the maximum buffer length is 1024.

```python
>>> plc.read_by_name('global.sample_string', pyads.PLCTYPE_STRING)
'Hello World'
>>> plc.write_by_name('global.sample_string', 'abc', pyads.PLCTYPE_STRING)
>>> plc.read_by_name(adr, 'global.sample_string', pyads.PLCTYPE_STRING)
'abc'
```

### Read and write arrays by name

You can also read/write arrays. For this you simply need to multiply the datatype by
the number of elements in the array or structure you want to read/write. 

```python
>>> plc.write_by_name('global.sample_array', [1, 2, 3], pyads.PLCTYPE_INT * 3)
>>> plc.read_by_name('global.sample_array', pyads.PLCTYPE_INT * 3)
[1, 2, 3]
```

```python
>>> plc.write_by_name('global.sample_array[0]', 5, pyads.PLCTYPE_INT)
>>> plc.read_by_name('global.sample_array[0]', pyads.PLCTYPE_INT)
5
```

### Read and write structures by name

#### Structures of the same datatype

TwinCAT declaration:
```
TYPE sample_structure :
STRUCT
	rVar : LREAL;
	rVar2 : LREAL;
	rVar3 : LREAL;
	rVar4 : ARRAY [1..3] OF LREAL;
END_STRUCT
END_TYPE
```

Python code:
```python
>>> plc.write_by_name('global.sample_structure',
                      [11.1, 22.2, 33.3, 44.4, 55.5, 66.6],
                      pyads.PLCTYPE_LREAL * 6)
>>> plc.read_by_name('global.sample_structure', pyads.PLCTYPE_LREAL * 6)
[11.1, 22.2, 33.3, 44.4, 55.5, 66.6]
```

```python
>>> plc.write_by_name('global.sample_structure.rVar2', 1234.5, pyads.PLCTYPE_LREAL)
>>> plc.read_by_name('global.sample_structure.rVar2', pyads.PLCTYPE_LREAL)
1234.5
```

#### Structures with multiple datatypes

**The structure in the PLC must be defined with `{attribute ‘pack_mode’ := ‘1’}.**

TwinCAT declaration:
```
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
```

Python code:

First declare a tuple which defines the PLC structure. This should match the order
as declared in the PLC. Information is passed and returned using the OrderedDict type. 

```python
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
```

### Read and write values by handle

When reading and writing by name, internally pyads is acquiring a handle from the PLC, 
reading/writing the value using that handle, before releasing the handle. A handle is 
just a unique identifier that the PLC associates to an address meaning that should an 
address change, the ADS client does not need to know the new address.

It is possible to manage the acquiring, tracking and releasing of handles yourself, which is 
advantageous if you plan on reading/writing the value frequently in your program, or 
wish to speed up the reading/writing by up to three times; as by default when reading/writing 
by name it makes 3 ADS calls (acquire, read/write, release), where as if you track the 
handles manually it only makes a single ADS call.

Using the Connection class:

```python
>>> var_handle = plc.get_handle('global.bool_value')
>>> plc.write_by_name('', True, pyads.PLCTYPE_BOOL, handle=var_handle)
>>> plc.read_by_name('', pyads.PLCTYPE_BOOL, handle=var_handle)
True
>>> plc.release_handle(var_handle)
```

**Be aware to release handles before closing the port to the PLC.** Leaving handles open 
reduces the available bandwidth in the ADS router.


### Read and write values by address

Read and write *UDINT* variables by address.

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
>>> # write 65536 to memory byte MDW0
>>> plc.write(INDEXGROUP_MEMORYBYTE, 0, 65536, pyads.PLCTYPE_UDINT)
>>> # write memory byte MDW0
>>> plc.read(INDEXGROUP_MEMORYBYTE, 0, pyads.PLCTYPE_UDINT)
65536
>>> plc.close()
```

Toggle bitsize variables by address.

```python
>>> # read memory bit MX100.0
>>> data = plc.read(INDEXGROUP_MEMORYBIT, 100*8 + 0, pyads.PLCTYPE_BOOL)
>>> # write inverted value to memory bit MX100.0
>>> plc.write(INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)
```

### Read and write lists of values

Reading and writing of multiple values can be performed in a single transaction. After the first operation, the symbol info is cached for future use.

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> var_list = ['MAIN.b_Execute', 'MAIN.str_TestString', 'MAIN.r32_TestReal']
>>> plc.read_list_by_name(var_list)
{'MAIN.b_Execute': True, 'MAIN.str_TestString': 'Hello World', 'MAIN.r32_TestReal': 123.45}
>>> write_dict = {'MAIN.b_Execute': False, 'MAIN.str_TestString': 'Goodbye World', 'MAIN.r32_TestReal': 54.321}
>>> plc.write_list_by_name(write_dict)
{'MAIN.b_Execute': 'no error', 'MAIN.str_TestString': 'no error', 'MAIN.r32_TestReal': 'no error'}
```

### Get all symbols

In order to get a list of the device's declared variables, use the `get_all_symbols` method.

```python
>>> symbols = plc.get_all_symbols()
>>> print('\n'.join("%s: %s" % item for item in vars(symbols[0]).items()))
index_group: 16448
index_offset: 384800
name: Constants.bFPUSupport
symtype: BOOL
comment: Does the target support multiple cores?
```

### Device Notifications

ADS supports device notifications, meaning you can pass a callback that gets
executed if a certain variable changes its state. However as the callback
gets called directly from the ADS DLL you need to extract the information
you need from the ctypes variables which are passed as arguments to the
callback function. A sample for adding a notification for an integer variable
can be seen here:

```python
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
```

This examples uses the default values for NotificationAttrib. The default
behaviour is that you get notified when the value of the variable changes on the
server. If you want to change this behaviour you can set `trans_mode` attribute
to one of the following values:

**`ADSTRANS_SERVERONCHA`**
This is the default. A notification will be sent everytime the value of the
specified variable changes.

**`ADSTRANS_SERVERCYCLE`**
A notification will be sent on a cyclic base. The interval is specified by
the`cycle_time` property.

**`ADSTRANS_NOTRANS`**
No notifications will be sent.

For more information about the NotificationAttrib settings have a look at
[Beckhoffs specification of the AdsNotificationAttrib struct][1].

**Here are some examples of callbacks for other datatypes:**

```python
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
```

#### Device Notification callback decorator

To make the handling of notifications more pythonic a notification decorator has
been introduced in version 2.2.4. This decorator takes care of converting the
ctype values transferred via ADS to python datatypes.

```python
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

```

Structures can be read in a this way by requesting bytes directly from the PLC.
Usage is similar to reading structures by name where you must first declare a tuple 
defining the PLC structure.

```python
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
```

The notification callback works for all basic plc datatypes but not for
arrays. Since version 3.0.5 the `ctypes.Structure` datatype is supported. Find
an example below:

```python
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

```

[0]: https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=
[1]: https://infosys.beckhoff.de/content/1033/tcadsdll2/html/tcadsdll_strucadsnotificationattrib.htm
