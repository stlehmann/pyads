#-*- coding: utf-8 -*-

'''
@requires: ctypes, Beckhoff TwinCAT mit ADS-DLL
@version: 1
@note: Wrapper for the Beckhoff TwinCAT AdsDLL.dll  

pyads uses the C API I{AdsDLL.dll}. The documentation for the ADS API is available on U{infosys.beckhoff.de<http://infosys.beckhoff.de/index.php?content=../content/1031/TcAdsDll2/HTML/TcAdsDll_Api_Overview.htm&id=>}

B{samples:}

opening port, set port number to 801
    >>> port = adsPortOpen()
    >>> adr = adsGetLocalAddress()
    >>> adr.setPort(PORT_SPS1)

setting ADS-state and machine-state 
    >>> errCode = adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, 0)
    >>> print errCode
     
reading bit %MX100.0, toggle it and writing back    
    >>> (errCode, data) = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, PLCTYPE_BOOL)
    >>> errCode = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100*8 + 0, not data)
    
writing an UDINT value to MW0 and reading it
    >>> errCode = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, 65536, PLCTYPE_UDINT)
    >>> (errCode, val) = adsSyncReadReq(adr, INDEXGROUP_MEMORYBYTE, 0, PLCTYPE_UDINT)
    >>> print errCode, val
    
writing a string value in MW0 and reading it
    >>> errCode = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBYTE, 0, "Hallo, wie geht es?", PLCTYPE_STRING)
    >>> (errCode, val) = ads

close port
    >>> adsPortClose()
'''


from pyads import *