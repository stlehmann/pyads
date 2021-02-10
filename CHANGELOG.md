# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
## 3.3.3 [unreleased]

### Added

### Changed

### Removed

## 3.3.2

### Added

### Changed
* fixed error with source distribution not containing adslib directory
* [#192](https://github.com/stlehmann/pyads/pull/192) make AdsSymbol even more pythonic
  * replace AdsSymbol.set_auto_update function by AdsSymbol.auto_update property
  * make AdsSymbol.value a property
  * AdsSymbol.value setter writes to plc if AdsSymbol.auto_update is True  
 
### Removed

## 3.3.1

### Added
* [#174](https://github.com/stlehmann/pyads/pull/174) Add `AdsSymbol` class for pythonic access
* [#169](https://github.com/stlehmann/pyads/pull/169) Add adsGetNetIdForPLC to pyads_ex
* [#179](https://github.com/stlehmann/pyads/pull/179) Added destructor to `pyads.Connection`

### Changed

### Removed

## 3.3.0

### Added
* [#155](https://github.com/stlehmann/pyads/pull/155) Add get_all_symbols method to Connection
* [#157](https://github.com/stlehmann/pyads/pull/157) Add write_structure_by_name method to Connection
* [#161](https://github.com/stlehmann/pyads/pull/161) Add sum read and write commands

### Changed
* [#150](https://github.com/stlehmann/pyads/pull/150) Use function annotations and variable annotations for type annotations

### Removed
* [#152](https://github.com/stlehmann/pyads/pull/152) Remove deprecated functions
* [#150](https://github.com/stlehmann/pyads/pull/150) Drop support for Python 2.7 and Python 3.5

## 3.2.2

### Added
* [#141](https://github.com/stlehmann/pyads/issues/141) Add ULINT support to read_structure_by_name
* [#143](https://github.com/stlehmann/pyads/issues/143) Add parse_notification method to Connection

### Changed
* [#140](https://github.com/stlehmann/pyads/pull/140) Fix lineendings to LF in the repository
* [#139](https://github.com/stlehmann/pyads/pull/139) Fix documentation and test issues with DeviceNotifications
* [ea707](https://github.com/stlehmann/pyads/tree/ea7073d93feac75c1864d1fe8ab2e14a2068b552) Fix documentation on
 ReadTheDocs
* [45859](https://github.com/stlehmann/pyads/tree/45859d6e9038b55d319efdbda95d3d6eeadd45e3) Fix issue with async handling in adslib

### Removed

## 3.2.1

### Added
* [#130](https://github.com/stlehmann/pyads/pull/130) Allow read_write with NULL read/write data
* [#131](https://github.com/stlehmann/pyads/pull/131) Add FILETIME passthrough to notification decorator

### Changed
* [#135](https://github.com/stlehmann/pyads/pull/135) Bug fix for setting up remote route from linux
* [#137](https://github.com/stlehmann/pyads/pull/137) Update adslib from upstream

### Removed

## 3.2.0

### Added
* [#111](https://github.com/stlehmann/pyads/pull/111) test cases for notification decorators
* [#113](https://github.com/stlehmann/pyads/pull/113) Add option not to check for data size
* [#118](https://github.com/stlehmann/pyads/pull/118) Add support for arrays in notification decorator
* [#112](https://github.com/stlehmann/pyads/pull/112) Add getters/setters for connection netid and port 

### Changed
* [#128](https://github.com/stlehmann/pyads/pull/128) Deprecation warning for older non-class functions. In
future versions only methods of the Connection class are supported.

### Removed
* [#127](https://github.com/stlehmann/pyads/pull/127) Drop support for Python 2

## 3.1.3

### Added
* [#120](https://github.com/stlehmann/pyads/pull/120) Allow to write ctypes directly

### Changed
* [#125](https://github.com/stlehmann/pyads/pull/125) Add notifications by address. The `data_name
` parameter changed to `data` as now not only strings can be passed but also a tuple with index group and offset.
* [#123](https://github.com/stlehmann/pyads/pull/123) Add ULINT data type
* [#106](https://github.com/stlehmann/pyads/pull/106) Store notification callbacks per AmsAddr 

### Removed

## 3.1.2
* new function read_structure_by_name to read a structure with multiple 
datatypes from the plc (issue #82, many thanks to @chrisbeardy)
* simplify pyads.add_route, now the ams address can be supplied by a string
instead of an AmsAddr object

## 3.1.1
* get/release handle methods for faster read/write by name

## 3.1.0

* add routes to a plc remotely with pyads.add_route_to_plc()

## 3.0.12

* update adslib to current upstream version (2018-03-22)
* fix structure definition inaccurarcies (issue #72)
* fix compatibility issue with new version of adslib (issue #78)

## 3.0.11

* fixed bug where parameter return_ctypes has not been passed through call
hierarchy of all calls, thanks to pyhannes

## 3.0.10

* rename src directory to adslib to prevent naming conflicts

## 3.0.9

* add return_ctypes parameter for read functions to omit time-costy time conversion

## 3.0.8

* add array datatype support for read_write function
* add test with array datatype for read and read/write function
* add section for usage of array datatypes in Readme

## 3.0.6

*  AdsLib: allow UNIX flavors to build more easily

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
