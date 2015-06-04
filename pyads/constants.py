# -*- coding: utf-8 -*-
"""
    pyads.constants
    ~~~~~~~~~~~~~~~

    Constants for the work with the ADS API.

    :copyright: © 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
from ctypes import *


# plc data types
PLCTYPE_BOOL = c_bool
PLCTYPE_BYTE = c_byte
PLCTYPE_DATE = c_int32 
PLCTYPE_DINT = c_int32
PLCTYPE_DT = c_int32 
PLCTYPE_DWORD = c_int32 
PLCTYPE_INT = c_int16
PLCTYPE_LREAL = c_double
PLCTYPE_REAL = c_float
PLCTYPE_SINT = c_int8
PLCTYPE_STRING = c_char
PLCTYPE_TIME = c_int32
PLCTYPE_TOD = c_int32
PLCTYPE_UDINT = c_uint32
PLCTYPE_UINT = c_uint16
PLCTYPE_USINT = c_uint8
PLCTYPE_WORD = c_int16
PLCTYPE_ARR_LREAL = lambda n: c_double*n
PLCTYPE_ARR_DINT = lambda n: c_int32*n
PLCTYPE_ARR_SHORT = lambda n: c_short*n



#Index Group
#READ_M - WRITE_M
INDEXGROUP_MEMORYBYTE = 0x4020    #:plc memory area (%M), offset means byte-offset
#READ_MX - WRITE_MX
INDEXGROUP_MEMORYBIT = 0x4021     #:plc memory area (%MX), offset means the bit adress, calculatedb by bytenumber * 8 + bitnumber
#PLCADS_IGR_RMSIZE
INDEXGROUP_MEMORYSIZE = 0x4025    #:size of the memory area in bytes
#PLCADS_IGR_RWRB
INDEXGROUP_RETAIN = 0x4030        #:plc retain memory area, offset means byte-offset
#PLCADS_IGR_RRSIZE
INDEXGROUP_RETAINSIZE = 0x4035    #:size of the retain area in bytes
#PLCADS_IGR_RWDB
INDEXGROUP_DATA = 0x4040          #:data area, offset means byte-offset
#PLCADS_IGR_RDSIZE
INDEXGROUP_DATASIZE = 0x4045      #:size of the data area in bytes

#PORTS
PORT_LOGGER = 100
PORT_EVENTLOGGER = 110
PORT_IO = 300
PORT_SPECIALTASK1 = 301
PORT_SPECIALTASK2 = 302
PORT_NC = 500
PORT_SPS1 = 801
PORT_SPS2 = 811
PORT_SPS3 = 821
PORT_SPS4 = 831
PORT_NOCKE = 900
PORT_SYSTEMSERVICE = 10000
PORT_SCOPE = 14000 

#ADSState-constants
ADSSTATE_INVALID = 0
ADSSTATE_IDLE = 1
ADSSTATE_RESET = 2
ADSSTATE_INIT = 3
ADSSTATE_START = 4
ADSSTATE_RUN = 5
ADSSTATE_STOP = 6
ADSSTATE_SAVECFG = 7
ADSSTATE_LOADCFG = 8
ADSSTATE_POWERFAILURE = 9
ADSSTATE_POWERGOOD = 10
ADSSTATE_ERROR = 11
ADSSTATE_SHUTDOWN = 12
ADSSTATE_SUSPEND = 13
ADSSTATE_RESUME = 14
ADSSTATE_CONFIG = 15
ADSSTATE_RECONFIG = 16

#ADSTransmode
ADSTRANS_NOTRANS = 0
ADSTRANS_CLIENTCYCLE = 1
ADSTRANS_CLIENT1REQ = 2
ADSTRANS_SERVERCYCLE = 3
ADSTRANS_SERVERONCHA = 4


