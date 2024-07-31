# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 3.4.2

### Changed

* [#402](https://github.com/stlehmann/pyads/pull/402) Universal DLL path for TwinCat 4026 and 4024 

## 3.4.1

### Changed
* [#392](https://github.com/stlehmann/pyads/pull/392) Fixed bug where port left open in Linux if exception during connecting
* [#389](https://github.com/stlehmann/pyads/pull/389) / [#393](https://github.com/stlehmann/pyads/pull/393) Fix for DLL path in TwinCT 4026
* [#369](https://github.com/stlehmann/pyads/pull/304) Add test for [#304](https://github.com/stlehmann/pyads/pull/304) in `tests/test_testserver.py`
* [#304](https://github.com/stlehmann/pyads/pull/304) Implemented try-catch when closing ADS notifications in AdsSymbol destructor
* [#325](https://github.com/stlehmann/pyads/pull/325) Added missing ADS return codes

## 3.4.0

### Added
* [#293](https://github.com/stlehmann/pyads/pull/2939) Support WSTRINGS in structures

### Changed
* [#292](https://github.com/stlehmann/pyads/pull/292) Improve performance of get_value_from_ctype_data for arrays
* [#363](https://github.com/stlehmann/pyads/pull/363) Allow for platform independent builds
* [#384](https://github.com/stlehmann/pyads/pull/384) Enable processing of nested structures

### Removed

## 3.3.9

### Added
* [#273](https://github.com/stlehmann/pyads/pull/273) Add TC3 port 2, 3, 4 constants
* [#247](https://github.com/stlehmann/pyads/pull/247) Add support for FreeBSD (tc/bsd)
* [#274](https://github.com/stlehmann/pyads/pull/274) Support WSTRING datatype

### Changed
* [#269](https://github.com/stlehmann/pyads/pull/269) Refactor Connection class in its own module, add helper functions
* [#260](https://github.com/stlehmann/pyads/pull/260) Fix decoding of symbol comments

### Removed
* [#282](https://github.com/stlehmann/pyads/pull/282]) Removed sample project in adslib to fix install error on Windows

## 3.3.8

### Added

### Changed
* [#264](https://github.com/stlehmann/pyads/pull/264) Fix error when using read_list_by_name on Linux machines

### Removed

## 3.3.6

### Added
* [#249](https://github.com/stlehmann/pyads/pull/249) Add testserver package to setup.py

### Changed

### Removed

## 3.3.5

### Added
* [#223](https://github.com/stlehmann/pyads/pull/223) Add structure support for symbols
* [#238](https://github.com/stlehmann/pyads/pull/238) Add LINT type to DATATYPE_MAP
* [#239](https://github.com/stlehmann/pyads/pull/239) Add device notification handling for AdvancedHandler in testserver

### Changed
* [#221](https://github.com/stlehmann/pyads/pull/221) CI now uses Github Actions instead of TravisCI. Also Upload to PyPi is now on automatic.
* [#242](https://github.com/stlehmann/pyads/pull/242) Upgrade requirements.txt
* [#243](https://github.com/stlehmann/pyads/pull/243) Refactor testserver as a package with multiple files
* Use TwinCAT3 default port 851 (PORT_TC3PLC1) in docs

### Removed

## 3.3.4

### Added
* [#187](https://github.com/stlehmann/pyads/pull/187) Support structured data types in `read_list_by_name`
* [#220](https://github.com/stlehmann/pyads/pull/220) Support structured data types in `write_list_by_name`. Also the
  AdvancedHandler of the testserver now support sumup_read and sumup_write commands.
* [#195](https://github.com/stlehmann/pyads/pull/195) Read/write by name without passing the datatype
* [#200](https://github.com/stlehmann/pyads/pull/200) Split read write by list into max-ads-sub-comands chunks
* [#206](https://github.com/stlehmann/pyads/pull/206) AdsSymbol now supports DT, DATE_TIME and TIME datatypes 

### Changed
* [#202](https://github.com/stlehmann/pyads/pull/202) Testserver now support variable sumread and sumwrite with 
  variable length for uint8 and string datatypes
* [#209](https://github.com/stlehmann/pyads/pull/209) Removed duplicate tests and added addtional asserts to existing tests
* [#212](https://github.com/stlehmann/pyads/pull/212) Add type annotations to structs.py

### Removed

## 3.3.3

### Added
* comprehensive documentation and short Quickstart guide

### Changed
* [#192](https://github.com/stlehmann/pyads/pull/192) Make AdsSymbol even more pythonic
  * Replace AdsSymbol.set_auto_update function by AdsSymbol.auto_update property
  * Make AdsSymbol.value a property
  * AdsSymbol.value setter writes to plc if AdsSymbol.auto_update is True

### Removed
* [#193](https://github.com/stlehmann/pyads/pull/193) Remove testserver_ex package which is still in development. 
  The testserver_ex package can be found in the [testserver_ex branch](https://github.
  com/stlehmann/pyads/tree/testserver_ex).

## 3.3.2

### Added

### Changed
* fixed error with source distribution not containing adslib directory

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
