"""
Connector for use with the qthmi package.

"""

__author__ = 'Stefan Lehmann'

from qthmi.connector import AbstractPLCConnector, ConnectionError
from pyads import adsPortOpen, adsGetLocalAddress, adsSyncReadReq, adsSyncWriteReq
from constants import *


class ADSConnector(AbstractPLCConnector):
    """
    @type port: int
    @ivar port: port number

    @type ams_addr: AmsAddr
    @ivar ams_addr: ams address of device


    """

    def __init__(self):
        super(ADSConnector, self).__init__()
        self.port = adsPortOpen()
        self.ams_addr = adsGetLocalAddress()

        if self.ams_addr.errCode:
            raise ADSError(self.adsAdr.errCode())

        self.ams_addr.setPort(PORT_SPS1)

    def read_from_plc(self, address, datatype):
        index_group = INDEXGROUP_MEMORYBIT if datatype == PLCTYPE_BOOL else INDEXGROUP_MEMORYBYTE
        (errcode, value) = adsSyncReadReq(self.ams_addr, index_group, address, datatype)
        if errcode:
            raise ConnectionError("Reading from address %i (ErrorCode %i)" % (address, errcode))
        return value

    def write_to_plc(self, address, value, datatype):
        index_group = INDEXGROUP_MEMORYBIT if datatype == PLCTYPE_BOOL else INDEXGROUP_MEMORYBYTE
        errcode = adsSyncWriteReq(self.ams_addr, index_group, address, value, datatype)
        if errcode:
            raise ConnectionError("Writing on address %i (ErrorCode %i)" % (address, errcode))

