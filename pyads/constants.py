# -*- coding: utf-8 -*-
"""Constants for the work with the ADS API.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on 2018-06-11 18:15:53
:last modified by: Stefan Lehmann
:last modified time: 2018-07-12 14:33:30

"""
from typing import Type
from ctypes import (
    Array,
    c_bool,
    c_byte,
    c_int8,
    c_uint8,
    c_int16,
    c_uint16,
    c_int32,
    c_uint32,
    c_float,
    c_double,
    c_char,
    c_int64,
    c_uint64,
)

STRING_BUFFER = 1024

# plc data types:
PLCTYPE_BOOL = c_bool
PLCTYPE_BYTE = c_byte
PLCTYPE_DATE = c_int32
PLCTYPE_DINT = c_int32
PLCTYPE_DT = c_int32
PLCTYPE_DWORD = c_uint32
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
PLCTYPE_WORD = c_uint16
PLCTYPE_LINT = c_int64
PLCTYPE_ULINT = c_uint64


def PLCTYPE_ARR_REAL(n):
    # type: (int) -> Type[Array[c_float]]
    """Return an array with n float values."""
    return c_float * n


def PLCTYPE_ARR_LREAL(n):
    # type: (int) -> Type[Array[c_double]]
    """Return an array with n double values."""
    return c_double * n


def PLCTYPE_ARR_INT(n):
    # type: (int) -> Type[Array[c_int16]]
    """Return an array with n int16 values."""
    return c_int16 * n


def PLCTYPE_ARR_DINT(n):
    # type: (int) -> Type[Array[c_int32]]
    """Return an array with n int32 values."""
    return c_int32 * n


def PLCTYPE_ARR_SHORT(n):
    # type: (int) -> Type[Array[c_int16]]
    """Return an array with n short values."""
    return c_int16 * n


# Index Group
# READ_M - WRITE_M
INDEXGROUP_MEMORYBYTE = 0x4020  #: plc memory area (%M), offset means byte-offset
# READ_MX - WRITE_MX
INDEXGROUP_MEMORYBIT = (
    0x4021
)  #: plc memory area (%MX), offset means the bit adress, calculatedb by bytenumber * 8 + bitnumber  # noqa: E501
# PLCADS_IGR_RMSIZE
INDEXGROUP_MEMORYSIZE = 0x4025  #: size of the memory area in bytes
# PLCADS_IGR_RWRB
INDEXGROUP_RETAIN = 0x4030  #: plc retain memory area, offset means byte-offset
# PLCADS_IGR_RRSIZE
INDEXGROUP_RETAINSIZE = 0x4035  #: size of the retain area in bytes
# PLCADS_IGR_RWDB
INDEXGROUP_DATA = 0x4040  #: data area, offset means byte-offset
# PLCADS_IGR_RDSIZE
INDEXGROUP_DATASIZE = 0x4045  #: size of the data area in bytes


ADSIGRP_SYMTAB = 0xF000
ADSIGRP_SYMNAME = 0xF001
ADSIGRP_SYMVAL = 0xF002

ADSIGRP_SYM_HNDBYNAME = 0xF003
ADSIGRP_SYM_VALBYNAME = 0xF004
ADSIGRP_SYM_VALBYHND = 0xF005
ADSIGRP_SYM_RELEASEHND = 0xF006
ADSIGRP_SYM_INFOBYNAME = 0xF007
ADSIGRP_SYM_VERSION = 0xF008
ADSIGRP_SYM_INFOBYNAMEEX = 0xF009

ADSIGRP_SYM_DOWNLOAD = 0xF00A
ADSIGRP_SYM_UPLOAD = 0xF00B
ADSIGRP_SYM_UPLOADINFO = 0xF00C

ADSIGRP_SYMNOTE = 0xF010  #: notification of named handle
ADSIGRP_IOIMAGE_RWIB = 0xF020  #: read/write input byte(s)
ADSIGRP_IOIMAGE_RWIX = 0xF021  #: read/write input bit
ADSIGRP_IOIMAGE_RWOB = 0xF030  #: read/write output byte(s)
ADSIGRP_IOIMAGE_RWOX = 0xF031  #: read/write output bit
ADSIGRP_IOIMAGE_CLEARI = 0xF040  #: write inputs to null
ADSIGRP_IOIMAGE_CLEARO = 0xF050  #: write outputs to null

ADSIGRP_DEVICE_DATA = 0xF100  #: state, name, etc...
ADSIOFFS_DEVDATA_ADSSTATE = 0x0000  #: ads state of device
ADSIOFFS_DEVDATA_DEVSTATE = 0x0002  #: device state


# PORTS
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
PORT_TC2PLC1 = PORT_SPS1
PORT_TC2PLC2 = PORT_SPS2
PORT_TC2PLC3 = PORT_SPS3
PORT_TC2PLC4 = PORT_SPS4
PORT_TC3PLC1 = 851
PORT_NOCKE = 900
PORT_CAM = PORT_NOCKE
PORT_SYSTEMSERVICE = 10000
PORT_SCOPE = 14000

# ADSState-constants
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

# ADSTransmode
ADSTRANS_NOTRANS = 0
ADSTRANS_CLIENTCYCLE = 1
ADSTRANS_CLIENT1REQ = 2
ADSTRANS_SERVERCYCLE = 3
ADSTRANS_SERVERONCHA = 4

# symbol flags
ADSSYMBOLFLAG_PERSISTENT = 0x00000001
ADSSYMBOLFLAG_BITVALUE = 0x00000002
ADSSYMBOLFLAG_REFERENCETO = 0x0004
ADSSYMBOLFLAG_TYPEGUID = 0x0008
ADSSYMBOLFLAG_TCCOMIFACEPTR = 0x0010
ADSSYMBOLFLAG_READONLY = 0x0020
ADSSYMBOLFLAG_CONTEXTMASK = 0x0F00

# ADS Command IDs
ADSCOMMAND_INVALID = 0x00
ADSCOMMAND_READDEVICEINFO = 0x01
ADSCOMMAND_READ = 0x02
ADSCOMMAND_WRITE = 0x03
ADSCOMMAND_READSTATE = 0x04
ADSCOMMAND_WRITECTRL = 0x05
ADSCOMMAND_ADDDEVICENOTE = 0x06
ADSCOMMAND_DELDEVICENOTE = 0x07
ADSCOMMAND_DEVICENOTE = 0x08
ADSCOMMAND_READWRITE = 0x09

# STATE Flags
ADSSTATEFLAG_REQRESP = 0x0001
ADSSTATEFLAG_COMMAND = 0x0004
