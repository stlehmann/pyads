#-*- coding: utf-8 -*-

"""
:requires: ctypes, Beckhoff TwinCAT with ADS-DLL
:note: Wrapper for the Beckhoff TwinCAT AdsDLL.dll

*pyads* uses the C API *AdsDLL.dll*. The documentation for the ADS API is
available on `infosys.backhoff.com <http://infosys.beckhoff.com/english.php?content=../content/1033/tcadsdll2/html/tcadsdll_api_overview.htm&id=20557>`_.

**samples:**

opening port, set port number to 801
    >>> port = adsPortOpen()
    >>> adr = adsGetLocalAddress()
    >>> adr.setPort(PORT_SPS1)

setting ADS-state and machine-state
    >>> adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, 0)

read bit %MX100.0, toggle it and writing back
    >>> data = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, PLCTYPE_BOOL)
    >>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)

write an UDINT value to MW0 and reading it
    >>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, 65536, PLCTYPE_UDINT)
    >>> adsSyncReadReq(adr, INDEXGROUP_MEMORYBYTE, 0, PLCTYPE_UDINT)

write a string value in MW0 and reading it
    >>> adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, "Hallo, wie geht es?", PLCTYPE_STRING)
    >>> adsSyncReadReq(adr, INDEXGROUP_MEMORY_BYTE, 0, PLCTYPE_STRING)

read a value of type real from global variable foo
    >>> adsSyncReadByName(adr, ".foo", PLCTYPE_REAL)

write a value of type real to global variable bar
    >>> adsSyncWriteByName(adr, ".bar", 1.234, PLCTYPE_REAL)

close port
    >>> adsPortClose()

"""
from pyads import *

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
