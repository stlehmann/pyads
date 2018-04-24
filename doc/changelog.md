# Changelog

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
