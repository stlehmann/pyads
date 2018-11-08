# Changelog

## 3.0.5

* add support for ctypes.Structure in notification callback decorators

## 3.0.4

* remove race-condition related to the notification decorator, thanks to Luka
Belingar for the bugfix

## Version 3.0.3

* bugfix: notifications on Windows didn't work

## Version 3.0.2

* bugfix: do not call add_route or delete_rout on Windows platform in Connection class
* increased coverage


## Version 3.0.1

With version **3.0.1** only the extended ADS functions will be used. This allows to use
the same library functions for Linux and Windows. As a result the *pyads.py* module has
been removed from the package. Certain older versions of TcAdsDll don't support the 'Ex'
set of functions. If you experience trouble please update your TwinCAT version.

The new version also comes with completely covered PEP484 compliant type-annotations. So
you can conveniently apply static type-checking with mypy or others.

## Version 2.2.13

* Apply to new PyPi
* Add `set_local_address` function to change local address on Linuxjk:w

## Version 2.2.7

Long Description for PyPi

## Version 2.2.6

Fix error with older TwinCAT2 versions and notifications.

## Version 2.2.5

Extended Testserver supports multiple device notifications

## Version 2.2.4

Notification callback decorator

## Version 2.2.3

Extended testserver that keeps written values and supports Device Notifications.

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
