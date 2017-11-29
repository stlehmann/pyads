# Quickstart

Make sure you followed the installation instructions before carrying on.

## Creating routes

ADS uses its own address system named AmsNetId to identify devices. The
assignment of a devices to an AmsNetId happens via routing. Routing
is handled differently on Windows and Linux.

### Creating routes on Linux

Open a port and create a AmsAddr object for the remote machine.

```python
>>> import pyads
>>> pyads.open_port()
32828
```
Add a route to the remote machine (Linux only - Windows routes must be
added in the TwinCat Router UI).

```python
>>> remote_ip = '192.168.0.100'
>>> adr = pyads.AmsAddr('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> pyads.add_route(adr, remote_ip)
```
Get the AMS address of the local machine. This may need to be added to
the routing table of the remote machine.
**NOTE: On Linux machines at least one route must be added before the call
to `get_local_address()` will function properly.**

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
>>> pyads.open_port()
>>> adr = pyads.AmsAddr('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> pyads.add_route(adr, '127.0.0.1')
```

## Usage

### Connect to a remote device

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)
>>> plc.open()
>>> plc.close()
```

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
>>> def callback(addr, notification, user_handle):
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
behaviout is that you get notified when the value of the variable changes on the
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
def callbackBool(adr, notification, user):
        contents = notification.contents
        var = map(bool, bytearray(contents.data)[0:contents.cbSampleSize])[0]

def callbackInt(adr, notification, user):
        contents = notification.contents
        var = map(int, bytearray(contents.data)[0:contents.cbSampleSize])[0]

def callbackString(adr, notification, user):
        dest = (c_ubyte * contents.cbSampleSize)()
        memmove(addressof(dest), addressof(contents.data), contents.cbSampleSize)
        # Remove nullbytes
        var = str(bytearray(dest)).split('\x00')[0]
```

#### Device Notification callback

To make the handling of notifications more Pythonic a notification decorator has
been introduced in version 2.2.4. This decorator takes care of converting the
ctype values transfered via ADS to python datatypes.

```python
>>> import pyads
>>> plc = pyads.Connection('127.0.0.1.1.1', 48898)
>>> plc.open()
>>>
>>> @plc.notification(pyads.PLCTYPE_INT)
>>> def callback(handle, name, timestamp, value):
>>>     print(
>>>         '{0}: received new notitifiction for variable "{1}", value: {2}'
>>>         .format(name, timestamp, value)
>>>     )
>>>
>>> plc.add_device_notification('GVL.intvar', pyads.NotificationAttrib(2),
                                callback)
>>> # Write to the variable to trigger a notification
>>> plc.write_by_name('GVL.intvar', 123, pyads.PLCTYPE_INT)

2017-10-01 10:41:23.640000: received new notitifiction for variable "GVL.intvar", value: abc

```

The notification callback works for all basic plc datatypes but not for arrays
or structures.

[0]: https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=
[1]: https://infosys.beckhoff.de/content/1033/tcadsdll2/html/tcadsdll_strucadsnotificationattrib.htm