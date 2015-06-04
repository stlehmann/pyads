# -*- coding: utf-8 -*-
'''
Created on 19.09.2013
@author: lehmann
'''

from ctypes import *
from constants import *

#ADS-DLL laden
_adsDLL = CDLL("AdsDll.dll") #: ADS-DLL (Beckhoff TwinCAT)


def adsGetDllVersion():
    '''
    @summary: returns version, revision and build of the ads-dll
    
    @rtype: AdsVersion
    @return: version, revision and build of the ads-dll
    '''
    #Aufruf der API-Funktion, Rückgabetyp ist Long
    resLong = c_long(_adsDLL.AdsGetDllVersion())

    #Struktur-Objekt erstellen
    stVersion = SAdsVersion()
    #Speicherbereich des Long-Wertes in die Struktur kopieren
    fit = min(sizeof(stVersion), sizeof(resLong))
    memmove(addressof(stVersion), addressof(resLong), fit)

    return AdsVersion(stVersion.version, stVersion.revision, stVersion.build)

def adsPortOpen():
    """
    @summary:  connects to the TwinCAT message router
    @rtype: int
    @return: port number
    """
    adsPortOpenFct = _adsDLL.AdsPortOpen
    adsPortOpenFct.restype = c_long

    portNr = adsPortOpenFct()
    return portNr

def adsPortClose():
    """
    @summary: closes the connection to the TwinCAT message router
    @rtype: int
    @return: error state
    """
    adsPortCloseFct = _adsDLL.AdsPortClose
    adsPortCloseFct.restype = c_long

    errCode = adsPortCloseFct()
    return errCode

def adsGetLocalAddress():
    """
    @summary: returns the local AMS-address and the port number
    @rtype: AmsAddr 
    @return: AMS-address
    """
    adsGetLocalAddressFct = _adsDLL.AdsGetLocalAddress
    stAmsAddr = SAmsAddr()

    errCode = adsGetLocalAddressFct(pointer(stAmsAddr))
    
    if errCode: 
        return None
    
    adsLocalAddr = AmsAddr(errCode, stAmsAddr)
   
    return adsLocalAddr

def adsSyncReadStateReq(adr):
    """
    @summary: reads the current ADS-state and the machine-state from the ADS-server
    @type adr: AmsAddr
    @param adr: local or remote AmsAddr
    @rtype: (int, int, int)
    @return: errCode, adsState, deviceState
    """
    adsSyncReadStateReqFct = _adsDLL.AdsSyncReadStateReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    adsState = c_int()
    pAdsState = pointer(adsState)
    deviceState = c_int()
    pDeviceState = pointer(deviceState)

    errCode = adsSyncReadStateReqFct(pAmsAddr, pAdsState, pDeviceState)
    return (errCode, adsState.value, deviceState.value)

def adsSyncReadDeviceInfoReq(adr):
    """
    @summary: reads the name and the version-number of the ADS-server
    @type adr: AmsAddr
    @param adr: local or remote AmsAddr
    @rtype: int, string, AdsVersion
    @return: errCode, device name, version
    """
    adsSyncReadDeviceInfoReqFct = _adsDLL.AdsSyncReadDeviceInfoReq
    
    pAmsAddr = pointer(adr.amsAddrStruct())
    devNameStringBuffer = create_string_buffer(20)
    pDevName = pointer(devNameStringBuffer)
    stVersion = SAdsVersion() 
    pVersion = pointer(stVersion)

    errCode = adsSyncReadDeviceInfoReqFct(pAmsAddr, pDevName, pVersion)
    return (errCode, devNameStringBuffer.value, AdsVersion(stVersion))

def adsSyncWriteControlReq(adr, adsState, deviceState, data, plcDataType):
    """
    @summary: changes the ads-state and the machine-state of the ADS-server
    
    @type adr: AmsAddr
    @param adr: local or remote AmsAddr
    
    @type adsState: int
    @param adsState: new ADS-state, according to ADSTATE constants
    
    @type deviceState: int 
    @param deviceState: new machine-state
    
    @param data: additional data
    
    @type plcDataType: int
    @param plcDataType: PLC-datatype, according to PLCTYPE constants
    
    @rtype: int
    @return: error-state of the function
    
    @note: Despite changing the ADS-state and the machine-state it is possible to send additional
    data to the ADS-server. For current ADS-devices additional data is not progressed. 
    Every ADS-device is able to communicate its current state to other devices. There is a difference
    between the device-state and the state of the ADS-interface (AdsState). The possible states of an
    ADS-interface are defined in the ADS-specification.
    """
    adsSyncWriteControlReqFct = _adsDLL.AdsSyncWriteControlReq
    
    pAddr = pointer(adr.amsAddrStruct())
    nAdsState = c_ulong(adsState)
    nDeviceState = c_ulong(deviceState)
    
    if plcDataType == PLCTYPE_STRING:
        nData = c_char_p(data)
        pData = nData
        nLength = len(pData.value)+1       
    else:
        nData = plcDataType(data)
        pData = pointer(nData)
        nLength = sizeof(nData)
    
    errCode = adsSyncWriteControlReqFct(pAddr, nAdsState, nDeviceState, nLength, pData)
    return errCode
    
def adsSyncWriteReq(adr, indexGroup, indexOffset, value, plcDataType):
    """
    @summary: sends data synchronous to an ADS-device
    
    @type adr: AmsAddr
    @param adr: local or remote AmsAddr
    
    @type indexGroup: int
    @param indexGroup: PLC storage area, according to the INDEXGROUP constants
    
    @type indexOffset: int
    @param indexOffset: PLC storage address
    
    @param value: value to write to the storage address of the PLC
    
    @type plcDataType: int
    @param plcDataType: type of the data given to the PLC, according to PLCTYPE constants
    
    @rtype: int
    @return: error-state of the function
    """

    adsSyncWriteReqFct = _adsDLL.AdsSyncWriteReq
    
    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)  
    
    if plcDataType == PLCTYPE_STRING:
        nData = c_char_p(value)
        pData = nData
        nLength = len(pData.value)+1       
    else:
        nData = plcDataType(value)
        pData = pointer(nData)
        nLength = sizeof(nData)
        
    
    errCode = adsSyncWriteReqFct(pAmsAddr, nIndexGroup, nIndexOffset, nLength, pData)
    return errCode

def adsSyncReadReq(adr, indexGroup, indexOffset, plcDataType):
    """
    @summary: reads data synchronous from an ADS-device
        
    @type adr: AmsAddr
    @param adr: local or remote AmsAddr
    
    @type indexGroup: int
    @param indexGroup: PLC storage area, according to the INDEXGROUP constants
    
    @type indexOffset: int
    @param indexOffset: PLC storage address   
    
    @type plcDataType: int
    @param plcDataType: type of the data given to the PLC, according to PLCTYPE constants
    
    @rtype: (int, PLCTYPE)
    @return: (errCode, value): B{errCode} error-state of the function, B{value}  
    """
    
    adsSyncReadReqFct = _adsDLL.AdsSyncReadReq
    
    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)
     
    data = plcDataType()
    pData = pointer(data)  
    nLength = c_ulong(sizeof(data))    
    errCode = adsSyncReadReqFct(pAmsAddr, nIndexGroup, nIndexOffset, nLength, pData)      
        
    return (errCode, data.value)

'''
def adsSyncAddDeviceNotificationReq(adr, indexGroup, indexOffset, noteAttrib, noteFunc, user, notification):
    adsSyncAddDeviceNotificationReq = _adsDLL.AdsSyncAddDeviceNotificationReq
    
    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)
    #pNoteAttrib =
''' 
        