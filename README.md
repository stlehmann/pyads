pyads - Python package
======================

[![Build Status](https://travis-ci.org/stlehmann/pyads.svg?branch=master)](https://travis-ci.org/stlehmann/pyads)
[![Coverage Status](https://coveralls.io/repos/github/MrLeeh/pyads/badge.svg?branch=master)](https://coveralls.io/github/MrLeeh/pyads?branch=master)
[![Documentation Status](https://readthedocs.org/projects/pyads/badge/?version=latest)](http://pyads.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/pyads.svg)](https://badge.fury.io/py/pyads)


This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API provided by *TcAdsDll.dll* on Windows *adslib.so* on Linux. The documentation for the ADS API is available on [infosys.beckhoff.com](http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557).


Documentation: http://pyads.readthedocs.io/en/latest/index.html

# Installation

From PyPi:

```bash
$ pip install pyads
```

From Github:

```bash
$ git clone https://github.com/MrLeeh/pyads.git --recursive
$ cd pyads
$ python setup.py install
```

# Quickstart

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
>>> plc.write(pyads.INDEXGROUP_MEMORYBYTE, 0, 65536, pyads.PLCTYPE_UDINT)
>>> # write memory byte MDW0
>>> plc.read(pyads.INDEXGROUP_MEMORYBYTE, 0, pyads.PLCTYPE_UDINT)
65536
>>> plc.close()
```

Toggle bitsize variables by address.

```python
>>> # read memory bit MX100.0
>>> data = plc.read(pyads.INDEXGROUP_MEMORYBIT, 100*8 + 0, pyads.PLCTYPE_BOOL)
>>> # write inverted value to memory bit MX100.0
>>> plc.write(pyads.INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)
```

### Simple handling of notification callbacks

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
>>> handles = plc.add_device_notification('GVL.intvar',
                                          pyads.NotificationAttrib(2), callback)
>>> # Write to the variable to trigger a notification
>>> plc.write_by_name('GVL.intvar', 123, pyads.PLCTYPE_INT)

2017-10-01 10:41:23.640000: received new notitifiction for variable "GVL.intvar", value: abc

>>> # remove notification
>>> plc.del_device_notification(handles)

```

The notification callback works for all basic plc datatypes but not for arrays
or structures.


[0]: https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=

