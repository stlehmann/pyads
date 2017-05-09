pyads - Python package
======================

[![Code Issues](http://www.quantifiedcode.com/api/v1/project/3e884877fac4408ea0d33ec4a788a212/badge.svg)](http://www.quantifiedcode.com/app/project/3e884877fac4408ea0d33ec4a788a212)
[![Build Status](https://travis-ci.org/MrLeeh/pyads.svg?branch=master)](https://travis-ci.org/MrLeeh/pyads)

This is a python wrapper for TwinCATs ADS library. It provides python functions
for communicating with TwinCAT devices. *pyads* uses the C API provided by *TcAdsDll.dll* on Windows *adslib.so* on Linux. The documentation for the ADS API is available on [infosys.beckhoff.com](http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557).

## Installation
```bash
$ pip install pyads
```
or
```bash
$ git clone https://github.com/MrLeeh/pyads.git
$ python setup.py install

```

### Windows
Make sure that you have the `TcAdsDll.dll` provided by Beckhoff installed on your PATH.

### Linux
Install the Linux ADS library from https://github.com/dabrowne/ADS
```bash
git clone https://github.com/dabrowne/ADS.git
cd ADS
sudo make install
```
## Documentation

Read the API documentation on http://pythonhosted.org/pyads/.

## Usage

Open port and create a AmsAddr object for remote machine.

```python
>>> import pyads
>>> pyads.open_port()
32828
```

Add a route to the remote machine (Linux only - Windows routes must be added in the TwinCat Router UI).
```python
>>> remote_ip = '192.168.0.100'
>>> pyads.add_route(adr, remote_ip)
```

Get the AMS address of the local machine. This may need to be added to the routing table of the remote machine.
__NOTE: On Linux machines at least one route must be added before the call to `get_local_address` will function properly.__
```python
>>> pyads.get_local_address()
<AmsAddress 192.168.0.109.1.1:32828>
>>> adr = pyads.AmsAddr('5.33.160.54.1.1', 851)
```

Read and write a variable by name from a remote machine.

```python
>>> pyads.read_by_name(adr, 'global.bool_value', pyads.PLCTYPE_BOOL)
True
>>> pyads.write_by_name(adr, 'global.bool_value', False, pyads.PLCTYPE_BOOL)
>>> pyads.read_by_name(adr, 'global.bool_value', pyads.PLCTYPE_BOOL)
False

```

If the name could not be found an Exception containing the error
message and ADS Error number is raised.

```python
>>> pyads.read_by_name(adr, 'global.wrong_name', pyads.PLCTYPE_BOOL)
ADSError: ADSError: symbol not found (1808)

```

Reading and writing Strings is now easier as you don' t have to supply the
length of a string anymore. For reading strings the maximum buffer length
is 1024.

```python
>>> pyads.read_by_name(adr, 'global.sample_string', pyads.PLCTYPE_STRING)
'Hello World'
>>> pyads.write_by_name(adr, 'global.sample_string', 'abc', pyads.PLCTYPE_STRING)
>>> pyads.read_by_name(adr, 'global.sample_string', pyads.PLCTYPE_STRING)
'abc'
```

Setting the ADS state and machine state.

```
>>> pyads.write_control(adr, pyads.ADSSTATE_STOP, 0, 0)
```


Toggle bitsize variables by address.

```python
>>> data = pyads.read(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, pyads.PLCTYPE_BOOL)
>>> pyads.write(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)
```

Read and write udint variable by address.

```python
>>> pyads.write(adr, INDEXGROUP_MEMORYBYTE, 0, 65536, pyads.PLCTYPE_UDINT)
>>> pyads.read(adr, INDEXGROUP_MEMORYBYTE, 0, pyads.PLCTYPE_UDINT)
65536
```

Finally close the ADS port.

```python
>>> pyads.close_port()
```


## Offline Testing
Pyads includes a locally hosted dummy server which can be used to test your code without the need to connect to a physical device.
```python
import pyads
from pyads.testserver import AdsTestServer
dummy_server = AdsTestServer()
dummy_server.start()
# Your code goes here
dummy_server.stop()

# Or as a context manager
with AdsTestServer() as dummy_server:
    # Your code goes here

```

The dummy server response can be customized by defining a request handler and passing it to the server. This function will be passed the packet received by the server, and is expected to return response data.
```python
dummy_server = AdsTestServer(handler=request_handler_fn)
```

For an example handler function, see `pyads.utils.testserver.default_handler`.

## Changelog

### Version 2.1.0
Linux support!

Pyads now has Linux compatibility by wrapping the [open source ADS library](https://github.com/dabrowne/ADS) provided by Beckhoff. The main API is identical on both Linux and Windows, however the Linux implementation includes a built in router which needs to be managed programmatically using `pyads.add_route(ams_address, ip_address)` and `pyads.delete_route(ams_address)`.

Version 2.1.0 also features vastly improved test coverage of the API, and the addition of a dummy test server for full integration testing.

### Version 2.0.0

I wanted to make the Wrapper more pythonic so I created a new module named
pyads.ads that contains all the functions from pyads.pyads but in a more
pythonic way. You can still access the old functions by using the pyads.pyads
module.

Improvements:

* more pythonic function names (e.g. 'write' instead of 'adsSyncWrite')
* easier handling of reading and writing Strings
* no error codes, if errors occur an Exception with the error code will be
raised
