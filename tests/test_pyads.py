"""
    Copyright (c) 2015 by Stefan Lehmann

"""
from pyads.constants import PORT_SPS1, ADSSTATE_STOP, PLCTYPE_STRING, \
    ADSSTATE_START, ADSSTATE_RUN, INDEXGROUP_MEMORYBIT, PLCTYPE_BOOL, \
    PLCTYPE_INT
from pyads.pyads import adsGetDllVersion, adsPortOpen, adsPortClose, \
    adsGetLocalAddress, adsSyncReadStateReq, adsSyncReadDeviceInfoReq, \
    adsSyncWriteControlReq, adsSyncWriteReq, adsSyncReadReq, adsSyncReadWriteReq, \
    adsSyncReadByName, adsSyncWriteByName
from pyads.structs import AmsAddr, AdsVersion
import pytest

ADS_ADDRESS = "5.25.223.158.1.1"
ADS_VAR_NAME = "MAIN.i"
ADS_VAR_TYPE = PLCTYPE_INT

@pytest.fixture
def connect():
    adsPortOpen()
    adr = adsGetLocalAddress()
    if ADS_ADDRESS is not None:
        adr.setAdr(ADS_ADDRESS)
    adr.setPort(PORT_SPS1)
    return adr

def test_adsGetDllVersion():
    version = adsGetDllVersion()
    assert isinstance(version, AdsVersion)
    assert isinstance(version.revision, int)
    assert isinstance(version.build, int)
    assert isinstance(version.version, int)

def test_adsPortOpenClose():
    port = adsPortOpen()
    assert isinstance(port, int)
    assert port > 0
    errCode = adsPortClose()
    assert errCode == 0

def test_adsGetLocalAddress():
    adsPortOpen()
    adr = adsGetLocalAddress()
    assert adr is not None
    assert isinstance(adr, AmsAddr)
    adsPortClose()

def test_adsSyncReadStateReq(connect):
    adr = connect
    err, ads_state, dev_state = adsSyncReadStateReq(adr)
    assert err == 0
    assert ads_state in (5, 6) # ads in run state
    adsPortClose()

def test_adsSyncReadDeviceInfoReq(connect):
    adr = connect
    err, name, version = adsSyncReadDeviceInfoReq(adr)
    assert err == 0
    assert name == "TCatPlcCtrl"
    assert isinstance(version, AdsVersion)
    adsPortClose()

def test_adsSyncWriteControlReq(connect):
    adr = connect
    err, ads_state, dev_state = adsSyncReadStateReq(adr)
    assert err == 0
    if ads_state == ADSSTATE_STOP:
        err = adsSyncWriteControlReq(adr, ADSSTATE_RUN, 0, "", PLCTYPE_STRING)
        assert err == 0
        err = adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, "", PLCTYPE_STRING)
        assert err == 0
    else:
        err = adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, "", PLCTYPE_STRING)
        assert err == 0
        err = adsSyncWriteControlReq(adr, ADSSTATE_RUN, 0, "", PLCTYPE_STRING)
        assert err == 0
    adsPortClose()

def test_adsRead_and_adsWrite(connect):
    adr = connect
    err, org_val = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, PLCTYPE_BOOL)
    assert err == 0
    err = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, True, PLCTYPE_BOOL)
    assert err == 0
    err, val = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, PLCTYPE_BOOL)
    assert err == 0
    assert val == True
    err = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, False, PLCTYPE_BOOL)
    assert err == 0
    err, val = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, PLCTYPE_BOOL)
    assert err == 0
    assert val == False
    err = adsSyncWriteReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, org_val, PLCTYPE_BOOL)
    assert err == 0
    adsPortClose()

def test_adsReadWrite(connect):
    adr = connect
    err, org_val = adsSyncReadReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, PLCTYPE_BOOL)
    assert err == 0
    err, val = adsSyncReadWriteReq(adr, INDEXGROUP_MEMORYBIT, 100 * 8 + 0, PLCTYPE_BOOL, False, PLCTYPE_BOOL)
    assert err == 1793 # service not supported by server
    adsPortClose()

def test_read_and_write_byname(connect):
    adr = connect
    # stop plc on server
    err = adsSyncWriteControlReq(adr, ADSSTATE_STOP, 0, "", PLCTYPE_STRING)
    assert err in (0, 1810)

    # read and write named value
    err, org_val = adsSyncReadByName(adr, ADS_VAR_NAME, ADS_VAR_TYPE)
    assert err == 0
    err = adsSyncWriteByName(adr, ADS_VAR_NAME, 10, ADS_VAR_TYPE)
    assert err == 0
    err, val = adsSyncReadByName(adr, ADS_VAR_NAME, ADS_VAR_TYPE)
    assert err == 0
    assert val == 10
    err = adsSyncWriteByName(adr, ADS_VAR_NAME, org_val, ADS_VAR_TYPE)
    assert err == 0