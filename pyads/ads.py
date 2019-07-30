"""Pythonic ADS functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53
:last modified by: Adrian Garcia
:last modified time: 2019-06-12 11:18:00

"""
from typing import Optional, Union, Tuple, Any, Type, Callable, Dict
from datetime import datetime
import struct
from ctypes import memmove, addressof, c_ubyte, Structure, sizeof

from .utils import platform_is_linux
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
)

from .structs import AmsAddr, SAmsNetId, AdsVersion, NotificationAttrib, SAdsNotificationHeader

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


def read_write(
    adr,
    index_group,
    index_offset,
    plc_read_datatype,
    value,
    plc_write_datatype,
    return_ctypes=False,
):
    # type: (AmsAddr, int, int, Type, Any, Type, bool) -> Any
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
        )

    return None


def read(adr, index_group, index_offset, plc_datatype, return_ctypes=False):
    # type: (AmsAddr, int, int, Type, bool) -> Any
    """Read data synchronous from an ADS-device.

        :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :return: value: **value**

    """
    if port is not None:
        return adsSyncReadReqEx2(
            port, adr, index_group, index_offset, plc_datatype, return_ctypes
        )

    return None


def read_by_name(adr, data_name, plc_datatype, return_ctypes=False):
    # type: (AmsAddr, str, Type, bool) -> Any
    """Read data synchronous from an ADS-device from data name.

    :param AmsAddr adr: local or remote AmsAddr
    :param string data_name: data name
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :return: value: **value**

    """
    if port is not None:
        return adsSyncReadByNameEx(port, adr, data_name, plc_datatype, return_ctypes)

    return None


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
    # type: (AmsAddr, str) -> None
    """Establish a new route in the AMS Router (linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address of routing endpoint
    :param str ip_address: ip address of the routing endpoint
    """
    return adsAddRoute(adr.netIdStruct(), ip_address)

def add_route_to_plc(sending_net_id, adding_host_name, ip_address, username, password, route_name=None, added_net_id=None):
    # type: (AmsAddr, str, str, str, str, str, AmsAddr) -> None
    """Embed a new route in the PLC.

    :param pyads.structs.SAmsNetId sending_net_id: sending net id
    :param str adding_host_name: host name (or IP) of the PC being added, defaults to hostname of this PC
    :param str ip_address: ip address of the routing endpoint
    :param str username: username for PLC
    :param str password: password for PLC
    :param str route_name: PLC side name for route, defaults to adding_host_name or the current hostename of this PC
    :param pyads.structs.SAmsNetId added_net_id: net id that is being added to the PLC, defaults to sending_net_id

    """
    return adsAddRouteToPLC(sending_net_id, adding_host_name, ip_address, username, password, route_name=route_name, added_net_id=added_net_id)

def delete_route(adr):
    # type: (AmsAddr) -> None
    """Remove existing route from the AMS Router (Linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    """
    return adsDelRoute(adr.netIdStruct())


def add_device_notification(adr, data_name, attr, callback, user_handle=None):
    # type: (AmsAddr, str, NotificationAttrib, Callable, int) -> Optional[Tuple[int, int]]  # noqa: E501
    """Add a device notification.

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    :param str data_name: PLC storage address
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
            port, adr, data_name, attr, callback, user_handle
        )

    return None


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


class Connection(object):
    """Class for managing the connection to an ADS device.

    :ivar str ams_net_id: AMS net id of the remote device
    :ivar int ams_net_port: port of the remote device
    :ivar str ip_address: the ip address of the device

    :note: If no IP Adress is given the ip address is automatically set
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
    ):
        # type: (int, int, Type, Any, Type, bool) -> Any
        """Read and write data synchronous from/to an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param int plc_read_datatype: type of the data given to the PLC to
            respond to, according to PLCTYPE constants
        :param value: value to write to the storage address of the PLC
        :param plc_write_datatype: type of the data given to the PLC,
            according to PLCTYPE constants
            :rtype: PLCTYPE
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
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
            )

        return None

    def read(self, index_group, index_offset, plc_datatype, return_ctypes=False):
        # type: (int, int, Type, bool) -> Any
        """Read data synchronous from an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
            :return: value: **value**
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)

        """
        if self._port is not None:
            return adsSyncReadReqEx2(
                self._port, self._adr, index_group, index_offset, plc_datatype, return_ctypes
            )

        return None

    def read_by_name(self, data_name, plc_datatype, return_ctypes=False):
        # type: (str, Type, bool) -> Any
        """Read data synchronous from an ADS-device from data name.

        :param string data_name: data name
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
            :return: value: **value**
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)

        """
        if self._port:
            return adsSyncReadByNameEx(self._port, self._adr, data_name, plc_datatype, return_ctypes)

        return None

    def write_by_name(self, data_name, value, plc_datatype):
        # type: (str, Any, Type) -> None
        """Send data synchronous to an ADS-device from data name.

        :param string data_name: PLC storage address
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants

        """
        if self._port:
            return adsSyncWriteByNameEx(
                self._port, self._adr, data_name, value, plc_datatype
            )

    def add_device_notification(self, data_name, attr, callback, user_handle=None):
        # type: (str, NotificationAttrib, Callable, int) -> Optional[Tuple[int, int]]
        """Add a device notification.

        :param str data_name: PLC storage address
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
                self._port, self._adr, data_name, attr, callback, user_handle
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

    def notification(self, plc_datatype=None):
        # type: (Optional[Type[Any]]) -> Callable
        """Decorate a callback function.

        **Decorator**.

        A decorator that can be used for callback functions in order to
        convert the data of the NotificationHeader into the fitting
        Python type.

        :param plc_datatype: The PLC datatype that needs to be converted. This can
        be any basic PLC datatype or a `ctypes.Structure`.

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
            # type: (Callable[[int, str, datetime, Any], None]) -> Callable[[Any, str], None] # noqa: E501

            def func_wrapper(notification, data_name):
                # type: (Any, str) -> None
                contents = notification.contents
                data_size = contents.cbSampleSize
                # Get dynamically sized data array
                data = (c_ubyte * data_size).from_address(addressof(contents) + SAdsNotificationHeader.data.offset)

                datatype_map = {
                    PLCTYPE_BOOL: "<?",
                    PLCTYPE_BYTE: "<c",
                    PLCTYPE_DINT: "<i",
                    PLCTYPE_DWORD: "<I",
                    PLCTYPE_INT: "<h",
                    PLCTYPE_LREAL: "<d",
                    PLCTYPE_REAL: "<f",
                    PLCTYPE_SINT: "<b",
                    PLCTYPE_UDINT: "<L",
                    PLCTYPE_UINT: "<H",
                    PLCTYPE_USINT: "<B",
                    PLCTYPE_WORD: "<H",
                }  # type: Dict[Type, str]

                if plc_datatype == PLCTYPE_STRING:
                    # read only until null-termination character
                    value = bytearray(data).split(b"\0", 1)[0].decode("utf-8")

                elif issubclass(plc_datatype, Structure):
                    value = plc_datatype()
                    fit_size = min(data_size, sizeof(value))
                    memmove(addressof(value), addressof(data), fit_size)

                elif plc_datatype not in datatype_map:
                    value = bytearray(data)

                else:
                    value = struct.unpack(
                        datatype_map[plc_datatype], bytearray(data)
                    )[0]

                dt = filetime_to_dt(contents.nTimeStamp)

                return func(contents.hNotification, data_name, dt, value)

            return func_wrapper

        return notification_decorator
