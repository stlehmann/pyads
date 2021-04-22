# -*- coding: utf-8 -*-
"""Constants for the work with the ADS API.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

"""
from typing import Type, Dict, Callable, Union
from ctypes import (
    Array,
    c_bool,
    c_ubyte,
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

STRING_BUFFER: int = 1024
PLC_DEFAULT_STRING_SIZE: int = 80

MAX_ADS_SUB_COMMANDS: int = 500

# plc data types:
PLCTYPE_BOOL = c_bool
PLCTYPE_BYTE = c_ubyte
PLCTYPE_DWORD = c_uint32
PLCTYPE_DINT = c_int32
PLCTYPE_INT = c_int16
PLCTYPE_LREAL = c_double
PLCTYPE_REAL = c_float
PLCTYPE_SINT = c_int8
PLCTYPE_STRING = c_char
PLCTYPE_TOD = c_int32
PLCTYPE_UBYTE = c_ubyte
PLCTYPE_UDINT = c_uint32
PLCTYPE_UINT = c_uint16
PLCTYPE_USINT = c_uint8
PLCTYPE_WORD = c_uint16
PLCTYPE_LINT = c_int64
PLCTYPE_ULINT = c_uint64

PLCTYPE_DATE = PLCTYPE_DWORD
PLCTYPE_DATE_AND_TIME = PLCTYPE_DWORD
PLCTYPE_DT = PLCTYPE_DWORD
PLCTYPE_TIME = PLCTYPE_DWORD

# Typing
PLCSimpleDataType = Union[
    PLCTYPE_BOOL,
    PLCTYPE_BYTE,
    PLCTYPE_DWORD,
    PLCTYPE_DINT,
    PLCTYPE_INT,
    PLCTYPE_LREAL,
    PLCTYPE_REAL,
    PLCTYPE_SINT,
    PLCTYPE_STRING,
    PLCTYPE_TOD,
    PLCTYPE_UBYTE,
    PLCTYPE_UDINT,
    PLCTYPE_UINT,
    PLCTYPE_USINT,
    PLCTYPE_WORD,
    PLCTYPE_LINT,
    PLCTYPE_ULINT,
    PLCTYPE_DATE,
    PLCTYPE_DATE_AND_TIME,
    PLCTYPE_DT,
    PLCTYPE_TIME,
]
PLCDataType = Union[Array, PLCSimpleDataType]

# Datatype unpacking values
DATATYPE_MAP: Dict[Type, str] = {
    PLCTYPE_BOOL: "<?",
    PLCTYPE_BYTE: "<B",
    PLCTYPE_DINT: "<i",
    PLCTYPE_DWORD: "<I",
    PLCTYPE_INT: "<h",
    PLCTYPE_LREAL: "<d",
    PLCTYPE_REAL: "<f",
    PLCTYPE_SINT: "<b",
    PLCTYPE_UDINT: "<I",
    PLCTYPE_UINT: "<H",
    PLCTYPE_USINT: "<B",
    PLCTYPE_LINT: "<q",
    PLCTYPE_ULINT: "<Q",
    PLCTYPE_WORD: "<H",
}


# ADS data types
ADST_VOID: int = 0
ADST_INT8: int = 16
ADST_UINT8: int = 17
ADST_INT16: int = 2
ADST_UINT16: int = 18
ADST_INT32: int = 3
ADST_UINT32: int = 19
ADST_INT64: int = 20
ADST_UINT64: int = 21
ADST_REAL32: int = 4
ADST_REAL64: int = 5
ADST_BIGTYPE: int= 65
ADST_STRING: int = 30
ADST_WSTRING: int = 31
ADST_REAL80: int = 32
ADST_BIT: int = 33
ADST_MAXTYPES: int = 34


ads_type_to_ctype = {
    # ADST_VOID
    ADST_INT8: PLCTYPE_BYTE,
    ADST_UINT8: PLCTYPE_UBYTE,
    ADST_INT16: PLCTYPE_INT,
    ADST_UINT16: PLCTYPE_UINT,
    ADST_INT32: PLCTYPE_DINT,
    ADST_UINT32: PLCTYPE_UDINT,
    ADST_INT64: PLCTYPE_LINT,
    ADST_UINT64: PLCTYPE_ULINT,
    ADST_REAL32: PLCTYPE_REAL,
    ADST_REAL64: PLCTYPE_LREAL,
    # ADST_BIGTYPE
    ADST_STRING: PLCTYPE_STRING,
    # ADST_WSTRING
    # ADST_REAL80
    ADST_BIT: PLCTYPE_BOOL,
}


def PLCTYPE_ARR_REAL(n: int) -> Type[Array]:
    """Return an array with n float values."""
    return c_float * n


def PLCTYPE_ARR_LREAL(n: int) -> Type[Array]:
    """Return an array with n double values."""
    return c_double * n


def PLCTYPE_ARR_BOOL(n: int) -> Type[Array]:
    """Return an array with n boolean values."""
    return c_bool * n


def PLCTYPE_ARR_INT(n: int) -> Type[Array]:
    """Return an array with n int16 values."""
    return c_int16 * n


def PLCTYPE_ARR_UINT(n: int) -> Type[Array]:
    """Return an array with n uint16 values."""
    return c_uint16 * n


def PLCTYPE_ARR_SHORT(n: int) -> Type[Array]:
    """Return an array with n short values."""
    return c_int16 * n


def PLCTYPE_ARR_USHORT(n: int) -> Type[Array]:
    """Return an array with n ushort values."""
    return c_uint16 * n


def PLCTYPE_ARR_DINT(n: int) -> Type[Array]:
    """Return an array with n int32 values."""
    return c_int32 * n


def PLCTYPE_ARR_UDINT(n: int) -> Type[Array]:
    """Return an array with n uint32 values."""
    return c_uint32 * n


def PLCTYPE_ARR_SINT(n: int) -> Type[Array]:
    """Return an array with n int8 values."""
    return c_int8 * n


def PLCTYPE_ARR_USINT(n: int) -> Type[Array]:
    """Return an array with n uint8 values."""
    return c_uint8 * n


# Map c-type array names to PLCTYPE_* arrays
PLC_ARRAY_MAP: Dict[str, Callable] = {
    'real': PLCTYPE_ARR_LREAL,  # LREAL, not REAL
    'boolean': PLCTYPE_ARR_BOOL,
    'int32': PLCTYPE_ARR_DINT,
    'uint32': PLCTYPE_ARR_UDINT,
    'int16': PLCTYPE_ARR_INT,
    'uint16': PLCTYPE_ARR_UINT,
    'int8': PLCTYPE_ARR_SINT,
    'uint8': PLCTYPE_ARR_USINT,
}


# Index Group
# READ_M - WRITE_M
INDEXGROUP_MEMORYBYTE = 0x4020  #: plc memory area (%M), offset means byte-offset
# READ_MX - WRITE_MX
INDEXGROUP_MEMORYBIT = (
    0x4021
)  #: plc memory area (%MX), offset means the bit address, calculatedb by bytenumber * 8 + bitnumber  # noqa: E501
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
ADSIGRP_SYM_DOWNLOAD2 = 0xF00D
ADSIGRP_SYM_DT_UPLOAD = 0xF00E
ADSIGRP_SYM_UPLOADINFO2 = 0xF00F

ADSIGRP_SYMNOTE = 0xF010  #: notification of named handle
ADSIGRP_IOIMAGE_RWIB = 0xF020  #: read/write input byte(s)
ADSIGRP_IOIMAGE_RWIX = 0xF021  #: read/write input bit
ADSIGRP_IOIMAGE_RWOB = 0xF030  #: read/write output byte(s)
ADSIGRP_IOIMAGE_RWOX = 0xF031  #: read/write output bit
ADSIGRP_IOIMAGE_CLEARI = 0xF040  #: write inputs to null
ADSIGRP_IOIMAGE_CLEARO = 0xF050  #: write outputs to null

ADSIGRP_SUMUP_READ = 0xF080  #: ADS Sum Read Request
ADSIGRP_SUMUP_WRITE = 0xF081  #: ADS Sum Write Request

ADSIGRP_DEVICE_DATA = 0xF100  #: state, name, etc...
ADSIOFFS_DEVDATA_ADSSTATE = 0x0000  #: ads state of device
ADSIOFFS_DEVDATA_DEVSTATE = 0x0002  #: device state


# PORTS
PORT_LOGGER: int = 100
PORT_EVENTLOGGER: int = 110
PORT_IO: int = 300
PORT_SPECIALTASK1: int = 301
PORT_SPECIALTASK2: int = 302
PORT_NC: int = 500
PORT_SPS1: int = 801
PORT_SPS2: int = 811
PORT_SPS3: int = 821
PORT_SPS4: int = 831
PORT_TC2PLC1: int = PORT_SPS1
PORT_TC2PLC2: int = PORT_SPS2
PORT_TC2PLC3: int = PORT_SPS3
PORT_TC2PLC4: int = PORT_SPS4
PORT_TC3PLC1: int = 851
PORT_NOCKE: int = 900
PORT_CAM: int = PORT_NOCKE
PORT_SYSTEMSERVICE: int = 10000
PORT_SCOPE: int = 14000
PORT_REMOTE_UDP: int = 48899

# ADSState-constants
ADSSTATE_INVALID: int = 0
ADSSTATE_IDLE: int = 1
ADSSTATE_RESET: int = 2
ADSSTATE_INIT: int = 3
ADSSTATE_START: int = 4
ADSSTATE_RUN: int = 5
ADSSTATE_STOP: int = 6
ADSSTATE_SAVECFG: int = 7
ADSSTATE_LOADCFG: int = 8
ADSSTATE_POWERFAILURE: int = 9
ADSSTATE_POWERGOOD: int = 10
ADSSTATE_ERROR: int = 11
ADSSTATE_SHUTDOWN: int = 12
ADSSTATE_SUSPEND: int = 13
ADSSTATE_RESUME: int = 14
ADSSTATE_CONFIG: int = 15
ADSSTATE_RECONFIG: int = 16

# ADSTransmode
ADSTRANS_NOTRANS: int = 0  #: no notifications
ADSTRANS_CLIENTCYCLE: int = 1
ADSTRANS_CLIENT1REQ: int = 2
ADSTRANS_SERVERCYCLE: int = 3  #: notify on a cyclic base
ADSTRANS_SERVERONCHA: int = 4  #: notify everytime the value changes

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
