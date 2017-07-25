pyads - Python package
======================

[![Build Status](https://travis-ci.org/MrLeeh/pyads.svg?branch=master)](https://travis-ci.org/MrLeeh/pyads)
[![Coverage Status](https://coveralls.io/repos/github/MrLeeh/pyads/badge.svg?branch=master)](https://coveralls.io/github/MrLeeh/pyads?branch=master)
[![Documentation Status](https://readthedocs.org/projects/pyads/badge/?version=latest)](http://pyads.readthedocs.io/en/latest/?badge=latest)

This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API provided by *TcAdsDll.dll* on Windows *adslib.so* on Linux. The documentation for the ADS API is available on [infosys.beckhoff.com](http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557).


Documentation: http://pyads.readthedocs.io/en/master/index.html

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
$ python -m pyads.testerver

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

# Changelog

## Version 2.2.0

Include shared library for Linux ADS communication. No manual installation
necessary anymore.

`Connection` class to allow a more convenient object oriented workflow. Each
device connection is now an object with methods for reading, writing, ... 
However it is still possible to use the old-style functional approach.

Added device notifications. Device notifications can now be used to monitor
values on the PLC. On certain changes callbacks can be used to react. Thanks
to the great implementation by Peter Janeck.

## Version 2.1.0
Linux support!

Pyads now has Linux compatibility by wrapping the [open source ADS library](https://github.com/dabrowne/ADS) provided by Beckhoff. The main API is identical on both Linux and Windows, however the Linux implementation includes a built in router which needs to be managed programmatically using `pyads.add_route(ams_address, ip_address)` and `pyads.delete_route(ams_address)`.

Version 2.1.0 also features vastly improved test coverage of the API, and the addition of a dummy test server for full integration testing.

## Version 2.0.0

I wanted to make the Wrapper more pythonic so I created a new module named
pyads.ads that contains all the functions from pyads.pyads but in a more
pythonic way. You can still access the old functions by using the pyads.pyads
module.

Improvements:

* more pythonic function names (e.g. 'write' instead of 'adsSyncWrite')
* easier handling of reading and writing Strings
* no error codes, if errors occur an Exception with the error code will be
raised


[0]: https://infosys.beckhoff.de/english.php?content=../content/1033/TcSystemManager/Basics/TcSysMgr_AddRouteDialog.htm&id=

