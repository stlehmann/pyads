"""Pythonic ADS functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53

"""
from typing import Optional, Union, Tuple, Any, Type, Callable, Dict
from datetime import datetime
import struct
from ctypes import memmove, addressof, c_ubyte, Array, Structure, sizeof
from collections import OrderedDict

from .utils import platform_is_linux, deprecated
from .filetimes import filetime_to_dt

from .pyads_ex import (
    adsAddRoute,
    adsAddRouteToPLC,
    adsDelRoute,
    adsPortOpenEx,
    adsPortCloseEx,
    adsGetLocalAddressEx,
    adsSyncReadStateReqEx,
    adsSyncReadDeviceInfoReqEx,
    adsSyncWriteControlReqEx,
    adsSyncWriteReqEx,
    adsSyncReadWriteReqEx2,
    adsSyncReadReqEx2,
    adsGetHandle,
    adsReleaseHandle,
    adsSyncReadByNameEx,
    adsSyncWriteByNameEx,
    adsSyncAddDeviceNotificationReqEx,
    adsSyncDelDeviceNotificationReqEx,
    adsSyncSetTimeoutEx,
    adsSetLocalAddress,
    ADSError,
)

from .constants import (
    PLCTYPE_BOOL,
    PLCTYPE_BYTE,
    PLCTYPE_DATE,
    PLCTYPE_DINT,
    PLCTYPE_DT,
    PLCTYPE_DWORD,
    PLCTYPE_INT,
    PLCTYPE_LREAL,
    PLCTYPE_REAL,
    PLCTYPE_SINT,
    PLCTYPE_STRING,
    PLCTYPE_TIME,
    PLCTYPE_TOD,
    PLCTYPE_UDINT,
    PLCTYPE_UINT,
    PLCTYPE_USINT,
    PLCTYPE_WORD,
    PLC_DEFAULT_STRING_SIZE,
    DATATYPE_MAP,
)

from .structs import (
    AmsAddr,
    SAmsNetId,
    AdsVersion,
    NotificationAttrib,
    SAdsNotificationHeader,
)

linux = platform_is_linux()
port = None  # type: int


def _parse_ams_netid(ams_netid):
    # type: (str) -> SAmsNetId
    """Parse an AmsNetId from *str* to *SAmsNetId*.

    :param str ams_netid: NetId as a string
    :rtype: SAmsNetId
    :return: NetId as a struct

    """
    try:
        id_numbers = list(map(int, ams_netid.split(".")))
    except ValueError:
        raise ValueError("no valid netid")

    if len(id_numbers) != 6:
        raise ValueError("no valid netid")

    # Fill the netId struct with data
    ams_netid_st = SAmsNetId()
    ams_netid_st.b = (c_ubyte * 6)(*id_numbers)
    return ams_netid_st


def open_port():
    # type: () -> int
    """Connect to the TwinCAT message router.

    :rtype: int
    :return: port number

    """
    global port

    port = port or adsPortOpenEx()
    return port


def close_port():
    # type: () -> None
    """Close the connection to the TwinCAT message router."""
    global port

    if port is not None:
        adsPortCloseEx(port)
        port = None


def get_local_address():
    # type: () -> Optional[AmsAddr]
    """Return the local AMS-address and the port number.

    :rtype: AmsAddr

    """
    if port is not None:
        return adsGetLocalAddressEx(port)

    return None


def set_local_address(ams_netid):
    # type: (Union[str, SAmsNetId]) -> None
    """Set the local NetID (**Linux only**).

    :param str: new AmsNetID
    :rtype: None

    **Usage:**

        >>> import pyads
        >>> pyads.open_port()
        >>> pyads.set_local_address('0.0.0.0.1.1')

    """
    if isinstance(ams_netid, str):
        ams_netid_st = _parse_ams_netid(ams_netid)
    else:
        ams_netid_st = ams_netid

    assert isinstance(ams_netid_st, SAmsNetId)

    if linux:
        return adsSetLocalAddress(ams_netid_st)
    else:
        raise ADSError(
            text="SetLocalAddress is not supported for Windows clients."
        )  # pragma: no cover


@deprecated()
def read_state(adr):
    # type: (AmsAddr) -> Optional[Tuple[int, int]]
    """Read the current ADS-state and the machine-state.

    Read the current ADS-state and the machine-state from the
    ADS-server.

    :param AmsAddr adr: local or remote AmsAddr
    :rtype: (int, int)
    :return: adsState, deviceState

    """
    if port is not None:
        return adsSyncReadStateReqEx(port, adr)

    return None


@deprecated()
def write_control(adr, ads_state, device_state, data, plc_datatype):
    # type: (AmsAddr, int, int, Any, Type) -> None
    """Change the ADS state and the machine-state of the ADS-server.

    :param AmsAddr adr: local or remote AmsAddr
    :param int ads_state: new ADS-state, according to ADSTATE constants
    :param int device_state: new machine-state
    :param data: additional data
    :param int plc_datatype: datatype, according to PLCTYPE constants

    :note: Despite changing the ADS-state and the machine-state it is possible
           to send additional data to the ADS-server. For current ADS-devices
           additional data is not progressed.
           Every ADS-device is able to communicate its current state to other
           devices.
           There is a difference between the device-state and the state of the
           ADS-interface (AdsState). The possible states of an ADS-interface
           are defined in the ADS-specification.

    """
    if port is not None:
        return adsSyncWriteControlReqEx(
            port, adr, ads_state, device_state, data, plc_datatype
        )


@deprecated()
def read_device_info(adr):
    # type: (AmsAddr) -> Optional[Tuple[str, AdsVersion]]
    """Read the name and the version number of the ADS-server.

    :param AmsAddr adr: local or remote AmsAddr
    :rtype: string, AdsVersion
    :return: device name, version

    """
    if port is not None:
        return adsSyncReadDeviceInfoReqEx(port, adr)

    return None


@deprecated()
def write(adr, index_group, index_offset, value, plc_datatype):
    # type: (AmsAddr, int, int, Any, Type) -> None
    """Send data synchronous to an ADS-device.

    :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param Type plc_datatype: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    if port is not None:
        return adsSyncWriteReqEx(
            port, adr, index_group, index_offset, value, plc_datatype
        )


@deprecated()
def read_write(
    adr,
    index_group,
    index_offset,
    plc_read_datatype,
    value,
    plc_write_datatype,
    return_ctypes=False,
    check_length=True,
):
    # type: (AmsAddr, int, int, Type, Any, Type, bool, bool) -> Any
    """Read and write data synchronous from/to an ADS-device.

    :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param Type plc_read_datatype: type of the data given to the PLC to respond
            to, according to PLCTYPE constants
        :param value: value to write to the storage address of the PLC
    :param Type plc_write_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :rtype: PLCTYPE
    :return: value: **value**

    """
    if port is not None:
        return adsSyncReadWriteReqEx2(
            port,
            adr,
            index_group,
            index_offset,
            plc_read_datatype,
            value,
            plc_write_datatype,
            return_ctypes,
            check_length,
        )

    return None


@deprecated()
def read(
    adr, index_group, index_offset, plc_datatype, return_ctypes=False, check_length=True
):
    # type: (AmsAddr, int, int, Type, bool, bool) -> Any
    """Read data synchronous from an ADS-device.

        :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :return: value: **value**

    """
    if port is not None:
        return adsSyncReadReqEx2(
            port,
            adr,
            index_group,
            index_offset,
            plc_datatype,
            return_ctypes,
            check_length,
        )

    return None


@deprecated()
def read_by_name(adr, data_name, plc_datatype, return_ctypes=False, check_length=True):
    # type: (AmsAddr, str, Type, bool) -> Any
    """Read data synchronous from an ADS-device from data name.

    :param AmsAddr adr: local or remote AmsAddr
    :param string data_name: data name
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :return: value: **value**

    """
    if port is not None:
        return adsSyncReadByNameEx(
            port, adr, data_name, plc_datatype, return_ctypes, check_length=check_length
        )

    return None


@deprecated()
def write_by_name(adr, data_name, value, plc_datatype):
    # type: (AmsAddr, str, Any, Type) -> None
    """Send data synchronous to an ADS-device from data name.

    :param AmsAddr adr: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plc_datatype: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    if port is not None:
        return adsSyncWriteByNameEx(port, adr, data_name, value, plc_datatype)


def add_route(adr, ip_address):
    # type: (Union[str, AmsAddr], str) -> None
    """Establish a new route in the AMS Router (linux Only).

    :param adr: AMS Address of routing endpoint as str or AmsAddr object
    :param str ip_address: ip address of the routing endpoint
    """
    if isinstance(adr, str):
        adr = AmsAddr(adr)

    return adsAddRoute(adr.netIdStruct(), ip_address)


def add_route_to_plc(
    sending_net_id,
    adding_host_name,
    ip_address,
    username,
    password,
    route_name=None,
    added_net_id=None,
):
    # type: (str, str, str, str, str, str, str) -> bool
    """Embed a new route in the PLC.

    :param pyads.structs.SAmsNetId sending_net_id: sending net id
    :param str adding_host_name: host name (or IP) of the PC being added
    :param str ip_address: ip address of the PLC
    :param str username: username for PLC
    :param str password: password for PLC
    :param str route_name: PLC side name for route, defaults to adding_host_name or the current hostname of this PC
    :param pyads.structs.SAmsNetId added_net_id: net id that is being added to the PLC, defaults to sending_net_id

    """
    return adsAddRouteToPLC(
        sending_net_id,
        adding_host_name,
        ip_address,
        username,
        password,
        route_name=route_name,
        added_net_id=added_net_id,
    )


def delete_route(adr):
    # type: (AmsAddr) -> None
    """Remove existing route from the AMS Router (Linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    """
    return adsDelRoute(adr.netIdStruct())


@deprecated()
def add_device_notification(adr, data, attr, callback, user_handle=None):
    # type: (AmsAddr, Union[str, Tuple[int, int]], NotificationAttrib, Callable, int) -> Optional[Tuple[int, int]]  # noqa: E501
    """Add a device notification.

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    :param Union[str, Tuple[int, int] data: PLC storage address as string or Tuple with index group and offset
    :param pyads.structs.NotificationAttrib attr: object that contains
        all the attributes for the definition of a notification
    :param callback: callback function that gets executed on in the event
        of a notification

    :rtype: (int, int)
    :returns: notification handle, user handle

    Save the notification handle and the user handle on creating a
    notification if you want to be able to remove the notification
    later in your code.

    """
    if port is not None:
        return adsSyncAddDeviceNotificationReqEx(
            port, adr, data, attr, callback, user_handle
        )

    return None


@deprecated()
def del_device_notification(adr, notification_handle, user_handle):
    # type: (AmsAddr, int, int) -> None
    """Remove a device notification.

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    :param notification_handle: address of the variable that contains
        the handle of the notification
    :param user_handle: user handle

    """
    if port is not None:
        return adsSyncDelDeviceNotificationReqEx(
            port, adr, notification_handle, user_handle
        )


def set_timeout(ms):
    # type: (int) -> None
    """Set timeout."""
    if port is not None:
        return adsSyncSetTimeoutEx(port, ms)


def size_of_structure(structure_def):
    """Calculate the size of a structure in number of BYTEs.

    :param tuple structure_def: special tuple defining the structure and
            types contained within it according o PLCTYPE constants

            Expected input example:

            structure_def = (
                ('rVar', pyads.PLCTYPE_LREAL, 1),
                ('sVar', pyads.PLCTYPE_STRING, 2, 35),
                ('rVar1', pyads.PLCTYPE_REAL, 1),
                ('iVar', pyads.PLCTYPE_DINT, 1),
                ('iVar1', pyads.PLCTYPE_INT, 3),
                ('ivar2', pyads.PLCTYPE_UDINT, 1),
                ('iVar3', pyads.PLCTYPE_UINT, 1),
                ('iVar4', pyads.PLCTYPE_BYTE, 1),
                ('iVar5', pyads.PLCTYPE_SINT, 1),
                ('iVar6', pyads.PLCTYPE_USINT, 1),
                ('bVar', pyads.PLCTYPE_BOOL, 4),
                ('iVar7', pyads.PLCTYPE_WORD, 1),
                ('iVar8', pyads.PLCTYPE_DWORD, 1),
            )
            i.e ('Variable Name', variable type, arr size (1 if not array),
                 length of string (if defined in PLC))

            If array of structure multiply structure_def input by array size

    :return: c_ubyte_Array: data size required to read/write a structure of multiple types
    """
    num_of_bytes = 0
    for item in structure_def:
        try:
            var, plc_datatype, size = item
            str_len = None
        except ValueError:
            var, plc_datatype, size, str_len = item

        if plc_datatype == PLCTYPE_STRING:
            if str_len is not None:
                num_of_bytes += (str_len + 1) * size
            else:
                num_of_bytes += (PLC_DEFAULT_STRING_SIZE + 1) * size
        elif plc_datatype not in DATATYPE_MAP:
            raise RuntimeError("Datatype not found")
        else:
            num_of_bytes += sizeof(plc_datatype) * size

    return c_ubyte * num_of_bytes


def dict_from_bytes(byte_list, structure_def, array_size=1):
    """Return an ordered dict of PLC values from a list of BYTE values read from PLC.

    :param byte_list: list of byte values for an entire structure
    :param tuple structure_def: special tuple defining the structure and
            types contained within it according o PLCTYPE constants

            Expected input example:

            structure_def = (
                ('rVar', pyads.PLCTYPE_LREAL, 1),
                ('sVar', pyads.PLCTYPE_STRING, 2, 35),
                ('rVar1', pyads.PLCTYPE_REAL, 1),
                ('iVar', pyads.PLCTYPE_DINT, 1),
                ('iVar1', pyads.PLCTYPE_INT, 3),
                ('ivar2', pyads.PLCTYPE_UDINT, 1),
                ('iVar3', pyads.PLCTYPE_UINT, 1),
                ('iVar4', pyads.PLCTYPE_BYTE, 1),
                ('iVar5', pyads.PLCTYPE_SINT, 1),
                ('iVar6', pyads.PLCTYPE_USINT, 1),
                ('bVar', pyads.PLCTYPE_BOOL, 4),
                ('iVar7', pyads.PLCTYPE_WORD, 1),
                ('iVar8', pyads.PLCTYPE_DWORD, 1),
            )
            i.e ('Variable Name', variable type, arr size (1 if not array),
                 length of string (if defined in PLC))

    :param array_size: size of array if reading array of structure, defaults to 1
    :type array_size: int, optional

    :return: ordered dictionary of values for each variable type in order of structure
    """
    values_list = []
    index = 0
    for structure in range(0, array_size):
        values = OrderedDict()
        for item in structure_def:
            try:
                var, plc_datatype, size = item
                str_len = None
            except ValueError:
                var, plc_datatype, size, str_len = item

            var_array = []
            for i in range(size):
                if plc_datatype == PLCTYPE_STRING:
                    if str_len is None:
                        str_len = PLC_DEFAULT_STRING_SIZE
                    var_array.append(
                        bytearray(byte_list[index : (index + (str_len + 1))])
                        .partition(b"\0")[0]
                        .decode("utf-8")
                    )
                    index += str_len + 1
                elif plc_datatype not in DATATYPE_MAP:
                    raise RuntimeError("Datatype not found. Check structure definition")
                else:
                    n_bytes = sizeof(plc_datatype)
                    var_array.append(
                        struct.unpack(
                            DATATYPE_MAP[plc_datatype],
                            bytearray(byte_list[index : (index + n_bytes)]),
                        )[0]
                    )
                    index += n_bytes
            if size == 1:  # if not an array, don't want a list in the dict return
                values[var] = var_array[0]
            else:
                values[var] = var_array
        values_list.append(values)

    if array_size != 1:
        return values_list
    else:
        return values_list[0]


class Connection(object):
    """Class for managing the connection to an ADS device.

    :ivar str ams_net_id: AMS net id of the remote device
    :ivar int ams_net_port: port of the remote device
    :ivar str ip_address: the ip address of the device

    :note: If no IP address is given the ip address is automatically set
        to first 4 parts of the Ams net id.

    """

    def __init__(self, ams_net_id, ams_net_port, ip_address=None):
        # type: (str, int, str) -> None
        self._port = None  # type: Optional[int]
        self._adr = AmsAddr(ams_net_id, ams_net_port)
        if ip_address is None:
            self.ip_address = ".".join(ams_net_id.split(".")[:4])
        else:
            self.ip_address = ip_address
        self._open = False
        self._notifications = {}  # type: Dict[int, str]

    @property
    def ams_netid(self):
        # type: () -> str
        return self._adr.netid

    @ams_netid.setter
    def ams_netid(self, netid):
        # type: (str) -> None
        if self._open:
            raise AttributeError("Setting netid is not allowed while connection is open.")
        self._adr.netid = netid

    @property
    def ams_port(self):
        # type: () -> int
        return self._adr.port

    @ams_port.setter
    def ams_port(self, port):
        # type: (int) -> None
        if self._open:
            raise AttributeError("Setting port is not allowed while connection is open.")
        self._adr.port = port

    def __enter__(self):
        # type: () -> Connection
        """Open on entering with-block."""
        self.open()
        return self

    def __exit__(self, _type, _val, _traceback):
        # type: (Type, Any, Any) -> None
        """Close on leaving with-block."""
        self.close()

    def open(self):
        # type: () -> None
        """Connect to the TwinCAT message router."""
        if self._open:
            return

        self._port = adsPortOpenEx()

        if linux:
            adsAddRoute(self._adr.netIdStruct(), self.ip_address)

        self._open = True

    def close(self):
        # type: () -> None
        """:summary: Close the connection to the TwinCAT message router."""
        if not self._open:
            return

        if linux:
            adsDelRoute(self._adr.netIdStruct())

        if self._port is not None:
            adsPortCloseEx(self._port)
            self._port = None

        self._open = False

    def get_local_address(self):
        # type: () -> Optional[AmsAddr]
        """Return the local AMS-address and the port number.

        :rtype: AmsAddr

        """
        if self._port is not None:
            return adsGetLocalAddressEx(self._port)

        return None

    def read_state(self):
        # type: () -> Optional[Tuple[int, int]]
        """Read the current ADS-state and the machine-state.

        Read the current ADS-state and the machine-state from the ADS-server.

        :rtype: (int, int)
        :return: adsState, deviceState

        """
        if self._port is not None:
            return adsSyncReadStateReqEx(self._port, self._adr)

        return None

    def write_control(self, ads_state, device_state, data, plc_datatype):
        # type: (int, int, Any, Type) -> None
        """Change the ADS state and the machine-state of the ADS-server.

        :param int ads_state: new ADS-state, according to ADSTATE constants
        :param int device_state: new machine-state
        :param data: additional data
        :param int plc_datatype: datatype, according to PLCTYPE constants

        :note: Despite changing the ADS-state and the machine-state it is
            possible to send additional data to the ADS-server. For current
            ADS-devices additional data is not progressed.
            Every ADS-device is able to communicate its current state to other
            devices. There is a difference between the device-state and the
            state of the ADS-interface (AdsState). The possible states of an
            ADS-interface are defined in the ADS-specification.

        """
        if self._port is not None:
            return adsSyncWriteControlReqEx(
                self._port, self._adr, ads_state, device_state, data, plc_datatype
            )

    def read_device_info(self):
        # type: () -> Optional[Tuple[str, AdsVersion]]
        """Read the name and the version number of the ADS-server.

        :rtype: string, AdsVersion
        :return: device name, version

        """
        if self._port is not None:
            return adsSyncReadDeviceInfoReqEx(self._port, self._adr)

        return None

    def write(self, index_group, index_offset, value, plc_datatype):
        # type: (int, int, Any, Type) -> None
        """Send data synchronous to an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants

        """
        if self._port is not None:
            return adsSyncWriteReqEx(
                self._port, self._adr, index_group, index_offset, value, plc_datatype
            )

    def read_write(
        self,
        index_group,
        index_offset,
        plc_read_datatype,
        value,
        plc_write_datatype,
        return_ctypes=False,
        check_length=True,
    ):
        # type: (int, int, Optional[Type], Any, Optional[Type], bool, bool) -> Any
        """Read and write data synchronous from/to an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param Type plc_read_datatype: type of the data given to the PLC to respond to,
            according to PLCTYPE constants, or None to not read anything
        :param value: value to write to the storage address of the PLC
        :param Type plc_write_datatype: type of the data given to the PLC, according to
            PLCTYPE constants, or None to not write anything
        :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)
        :return: value: **value**

        """
        if self._port is not None:
            return adsSyncReadWriteReqEx2(
                self._port,
                self._adr,
                index_group,
                index_offset,
                plc_read_datatype,
                value,
                plc_write_datatype,
                return_ctypes,
                check_length,
            )

        return None

    def read(
        self,
        index_group,
        index_offset,
        plc_datatype,
        return_ctypes=False,
        check_length=True,
    ):
        # type: (int, int, Type, bool, bool) -> Any
        """Read data synchronous from an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
            :return: value: **value**
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)

        """
        if self._port is not None:
            return adsSyncReadReqEx2(
                self._port,
                self._adr,
                index_group,
                index_offset,
                plc_datatype,
                return_ctypes,
                check_length,
            )

        return None

    def get_handle(self, data_name):
        # type: (str) -> int
        """Get the handle of the PLC-variable, handles obtained using this
         method should be released using method 'release_handle'.

        :param string data_name: data name

        :rtype: int
        :return: int: PLC-variable handle
        """
        if self._port is not None:
            return adsGetHandle(self._port, self._adr, data_name)

        return None

    def release_handle(self, handle):
        # type: (int) -> None
        """ Release handle of a PLC-variable.

        :param int handle: handle of PLC-variable to be released
        """
        if self._port is not None:
            adsReleaseHandle(self._port, self._adr, handle)

    def read_by_name(
        self,
        data_name,
        plc_datatype,
        return_ctypes=False,
        handle=None,
        check_length=True,
    ):
        # type: (str, Type, bool, int) -> Any
        """Read data synchronous from an ADS-device from data name.

        :param string data_name: data name,  can be empty string if handle is used
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
            :return: value: **value**
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)
        :param int handle: PLC-variable handle, pass in handle if previously
            obtained to speed up reading (default: None)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)

        """
        if self._port:
            return adsSyncReadByNameEx(
                self._port,
                self._adr,
                data_name,
                plc_datatype,
                return_ctypes=return_ctypes,
                handle=handle,
                check_length=check_length,
            )

        return None

    def read_structure_by_name(
        self, data_name, structure_def, array_size=1, structure_size=None, handle=None
    ):
        """Read a structure of multiple types.

        :param string data_name: data name
        :param tuple structure_def: special tuple defining the structure and
            types contained within it according to PLCTYPE constants, must match
            the structure defined in the PLC, PLC structure must be defined with
            {attribute 'pack_mode' :=  '1'}

            Expected input example:
            structure_def = (
                ('rVar', pyads.PLCTYPE_LREAL, 1),
                ('sVar', pyads.PLCTYPE_STRING, 2, 35),
                ('rVar1', pyads.PLCTYPE_REAL, 1),
                ('iVar', pyads.PLCTYPE_DINT, 1),
                ('iVar1', pyads.PLCTYPE_INT, 3),
                ('ivar2', pyads.PLCTYPE_UDINT, 1),
                ('iVar3', pyads.PLCTYPE_UINT, 1),
                ('iVar4', pyads.PLCTYPE_BYTE, 1),
                ('iVar5', pyads.PLCTYPE_SINT, 1),
                ('iVar6', pyads.PLCTYPE_USINT, 1),
                ('bVar', pyads.PLCTYPE_BOOL, 4),
                ('iVar7', pyads.PLCTYPE_WORD, 1),
                ('iVar8', pyads.PLCTYPE_DWORD, 1),
            )
            i.e ('Variable Name', variable type, arr size (1 if not array),
                 length of string (if defined in PLC))

        :param array_size: size of array if reading array of structure, defaults to 1
        :type array_size: int, optional
        :param structure_size: size of structure if known by previous use of
            size_of_structure, defaults to None
        :type structure_size: , optional
        :param handle: PLC-variable handle, pass in handle if previously
            obtained to speed up reading, defaults to None
        :type handle: int, optional

        :return: values_dict: ordered dictionary of all values corresponding to the structure
            definition
        """
        if structure_size is None:
            structure_size = size_of_structure(structure_def * array_size)
        values = self.read_by_name(data_name, structure_size, handle=handle)
        if values is not None:
            return dict_from_bytes(values, structure_def, array_size=array_size)

        return None

    def write_by_name(self, data_name, value, plc_datatype, handle=None):
        # type: (str, Any, Type, int) -> None
        """Send data synchronous to an ADS-device from data name.

        :param string data_name: data name, can be empty string if handle is used
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants
        :param int handle: PLC-variable handle, pass in handle if previously
            obtained to speed up writing (default: None)
        """
        if self._port:
            return adsSyncWriteByNameEx(
                self._port, self._adr, data_name, value, plc_datatype, handle=handle
            )

    def add_device_notification(self, data, attr, callback, user_handle=None):
        # type: (Union[str, Tuple[int, int]], NotificationAttrib, Callable, int) -> Optional[Tuple[int, int]]
        """Add a device notification.

        :param Union[str, Tuple[int, int] data: PLC storage address as string or Tuple with index group and offset
        :param pyads.structs.NotificationAttrib attr: object that contains
            all the attributes for the definition of a notification
        :param callback: callback function that gets executed on in the event
            of a notification

        :rtype: (int, int)
        :returns: notification handle, user handle

        Save the notification handle and the user handle on creating a
        notification if you want to be able to remove the notification
        later in your code.

        **Usage**:

            >>> import pyads
            >>> from ctypes import size_of
            >>>
            >>> # Connect to the local TwinCAT PLC
            >>> plc = pyads.Connection('127.0.0.1.1.1', 851)
            >>>
            >>> # Create callback function that prints the value
            >>> def mycallback(adr, notification, user):
            >>>     contents = notification.contents
            >>>     value = next(
            >>>         map(int,
            >>>             bytearray(contents.data)[0:contents.cbSampleSize])
            >>>     )
            >>>     print(value)
            >>>
            >>> with plc:
            >>>     # Add notification with default settings
            >>>     attr = pyads.NotificationAttrib(size_of(pyads.PLCTYPE_INT))
            >>>
            >>>     hnotification, huser = plc.add_device_notification(
            >>>         adr, attr, mycallback)
            >>>
            >>>     # Remove notification
            >>>     plc.del_device_notification(hnotification, huser)

        """
        if self._port is not None:
            notification_handle, user_handle = adsSyncAddDeviceNotificationReqEx(
                self._port, self._adr, data, attr, callback, user_handle
            )
            return notification_handle, user_handle

        return None

    def del_device_notification(self, notification_handle, user_handle):
        # type: (int, int) -> None
        """Remove a device notification.

        :param notification_handle: address of the variable that contains
            the handle of the notification
        :param user_handle: user handle

        """
        if self._port is not None:
            adsSyncDelDeviceNotificationReqEx(
                self._port, self._adr, notification_handle, user_handle
            )

    @property
    def is_open(self):
        # type: () -> bool
        """Show the current connection state.

        :return: True if connection is open

        """
        return self._open

    def set_timeout(self, ms):
        # type: (int) -> None
        """Set Timeout."""
        if self._port is not None:
            adsSyncSetTimeoutEx(self._port, ms)

    def notification(self, plc_datatype=None, timestamp_as_filetime=False):
        # type: (Optional[Type], bool) -> Callable
        """Decorate a callback function.

        **Decorator**.

        A decorator that can be used for callback functions in order to
        convert the data of the NotificationHeader into the fitting
        Python type.

        :param plc_datatype: The PLC datatype that needs to be converted. This can
        be any basic PLC datatype or a `ctypes.Structure`.
        :param timestamp_as_filetime: Whether the notification timestamp should be returned
        as `datetime.datetime` (False) or Windows `FILETIME` as originally transmitted
        via ADS (True). Be aware that the precision of `datetime.datetime` is limited to
        microseconds, while FILETIME allows for 100 ns. This may be relevant when using
        task cycle times such as 62.5 µs. Default: False.

        The callback functions need to be of the following type:

        >>> def callback(handle, name, timestamp, value)

        * `handle`: the notification handle
        * `name`: the variable name
        * `timestamp`: the timestamp as datetime value
        * `value`: the converted value of the variable

        **Usage**:

            >>> import pyads
            >>>
            >>> plc = pyads.Connection('172.18.3.25.1.1', 851)
            >>>
            >>>
            >>> @plc.notification(pyads.PLCTYPE_STRING)
            >>> def callback(handle, name, timestamp, value):
            >>>     print(handle, name, timestamp, value)
            >>>
            >>>
            >>> with plc:
            >>>    attr = pyads.NotificationAttrib(20,
            >>>                                    pyads.ADSTRANS_SERVERCYCLE)
            >>>    handles = plc.add_device_notification('GVL.test', attr,
            >>>                                          callback)
            >>>    while True:
            >>>        pass

        """

        def notification_decorator(func):
            # type: (Union[Callable[[int, str, datetime, Any], None], Callable[[int, str, int, Any], None]]) -> Callable[[Any, str], None] # noqa: E501

            def func_wrapper(notification, data_name):
                # type: (Any, str) -> None
                contents = notification.contents
                data_size = contents.cbSampleSize
                # Get dynamically sized data array
                data = (c_ubyte * data_size).from_address(
                    addressof(contents) + SAdsNotificationHeader.data.offset
                )

                if plc_datatype == PLCTYPE_STRING:
                    # read only until null-termination character
                    value = bytearray(data).split(b"\0", 1)[0].decode("utf-8")

                elif plc_datatype is not None and issubclass(plc_datatype, Structure):
                    value = plc_datatype()
                    fit_size = min(data_size, sizeof(value))
                    memmove(addressof(value), addressof(data), fit_size)

                elif plc_datatype is not None and issubclass(plc_datatype, Array):
                    if data_size == sizeof(plc_datatype):
                        value = list(plc_datatype.from_buffer_copy(bytes(data)))
                    else:
                        # invalid size
                        value = None

                elif plc_datatype not in DATATYPE_MAP:
                    value = bytearray(data)

                else:
                    value = struct.unpack(DATATYPE_MAP[plc_datatype], bytearray(data))[
                        0
                    ]

                if timestamp_as_filetime:
                    timestamp = contents.nTimeStamp
                else:
                    timestamp = filetime_to_dt(contents.nTimeStamp)

                return func(contents.hNotification, data_name, timestamp, value)

            return func_wrapper

        return notification_decorator
