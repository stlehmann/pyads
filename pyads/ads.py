"""
    Pythonic ADS functions.

    :copyright: (c) 2016 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
from .utils import platform_is_linux

from .pyads import (
    adsPortOpen, adsPortClose,
    adsSyncWriteReq, adsSyncReadWriteReq, adsSyncReadReq,
    adsSyncReadByName, adsSyncWriteByName, adsSyncReadStateReq,
    adsSyncWriteControlReq, adsSyncReadDeviceInfoReq, adsGetLocalAddress,
    adsSyncAddDeviceNotificationReq, adsSyncDelDeviceNotificationReq
)

from .pyads_ex import (
    adsAddRoute, adsDelRoute, adsPortOpenEx, adsPortCloseEx,
    adsGetLocalAddressEx, adsSyncReadStateReqEx, adsSyncReadDeviceInfoReqEx,
    adsSyncWriteControlReqEx, adsSyncWriteReqEx, adsSyncReadWriteReqEx2,
    adsSyncReadReqEx2, adsSyncReadByNameEx, adsSyncWriteByNameEx,
    adsSyncAddDeviceNotificationReqEx, adsSyncDelDeviceNotificationReqEx
)

from .structs import AmsAddr

linux = platform_is_linux()
port = None


def open_port():
    """
    :summary:  Connect to the TwinCAT message router.
    :rtype: int
    :return: port number

    """
    global port

    if linux:
        port = port or adsPortOpenEx()
        return port

    return adsPortOpen()


def close_port():
    """
    :summary: Close the connection to the TwinCAT message router.

    """
    global port

    if linux:
        adsPortCloseEx(port)
        port = None
        return

    adsPortClose()


def get_local_address():
    """
    :summary: Return the local AMS-address and the port number.
    :rtype: AmsAddr

    """
    if linux:
        return adsGetLocalAddressEx(port)

    return adsGetLocalAddress()


def read_state(adr):
    """
    :summary: Read the current ADS-state and the machine-state from the
        ADS-server
    :param AmsAddr adr: local or remote AmsAddr
    :rtype: (int, int)
    :return: adsState, deviceState

    """
    if linux:
        return adsSyncReadStateReqEx(port, adr)

    return adsSyncReadStateReq(adr)


def write_control(adr, ads_state, device_state, data, plc_datatype):
    """
    :summary: Change the ADS state and the machine-state of the ADS-server

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
    if linux:
        return adsSyncWriteControlReqEx(
            port, adr, ads_state, device_state, data, plc_datatype
        )

    return adsSyncWriteControlReq(
        adr, ads_state, device_state, data, plc_datatype
    )


def read_device_info(adr):
    """
    :summary: Read the name and the version number of the ADS-server
    :param AmsAddr adr: local or remote AmsAddr
    :rtype: string, AdsVersion
    :return: device name, version

    """
    if linux:
        return adsSyncReadDeviceInfoReqEx(port, adr)

    return adsSyncReadDeviceInfoReq(adr)


def write(adr, index_group, index_offset, value, plc_datatype):
    """
    :summary: Send data synchronous to an ADS-device

    :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plc_datatype: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    if linux:
        return adsSyncWriteReqEx(
            port, adr, index_group, index_offset, value, plc_datatype
        )

    adsSyncWriteReq(adr, index_group, index_offset, value, plc_datatype)


def read_write(adr, index_group, index_offset, plc_read_datatype,
               value, plc_write_datatype):
    """
    :summary: Read and write data synchronous from/to an ADS-device
    :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int plc_read_datatype: type of the data given to the PLC to respond
        to, according to PLCTYPE constants
    :param value: value to write to the storage address of the PLC
    :param plc_write_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: PLCTYPE
    :return: value: **value**

    """
    if linux:
        return adsSyncReadWriteReqEx2(
            port, adr, index_group, index_offset, plc_read_datatype,
            value, plc_write_datatype
        )

    return adsSyncReadWriteReq(
        adr, index_group, index_offset, plc_read_datatype,
        value, plc_write_datatype
    )


def read(adr, index_group, index_offset, plc_datatype):
    """
    :summary: Read data synchronous from an ADS-device
    :param AmsAddr adr: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :return: value: **value**

    """
    if linux:
        return adsSyncReadReqEx2(
            port, adr, index_group, index_offset, plc_datatype
        )

    return adsSyncReadReq(adr, index_group, index_offset, plc_datatype)


def read_by_name(adr, data_name, plc_datatype):
    """
    :summary: Read data synchronous from an ADS-device from data name
    :param AmsAddr adr: local or remote AmsAddr
    :param string data_name: data name
    :param int plc_datatype: type of the data given to the PLC, according to
        PLCTYPE constants
    :return: value: **value**

    """
    if linux:
        return adsSyncReadByNameEx(port, adr, data_name, plc_datatype)

    return adsSyncReadByName(adr, data_name, plc_datatype)


def write_by_name(adr, data_name, value, plc_datatype):
    """
    :summary: Send data synchronous to an ADS-device from data name

    :param AmsAddr adr: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plc_datatype: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    if linux:
        return adsSyncWriteByNameEx(port, adr, data_name, value, plc_datatype)

    return adsSyncWriteByName(adr, data_name, value, plc_datatype)


def add_route(adr, ip_address):
    """
    :summary:  Establish a new route in the AMS Router (linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address of routing endpoint
    :param str ip_address: ip address of the routing endpoint
    """
    return adsAddRoute(adr.netIdStruct(), ip_address)


def delete_route(adr):
    """
    :summary:  Remove existing route from the AMS Router (Linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing
        entry which is to be removed from the router.
    """
    return adsDelRoute(adr.netIdStruct())


def add_device_notification(adr, data_name, attr, callback):
    if linux:
        return adsSyncAddDeviceNotificationReqEx(port, adr, data_name, attr,
                                                 callback)
    else:
        return adsSyncAddDeviceNotificationReq(adr, data_name, attr, callback)


def del_device_notification(adr, notification, hUser):
    if linux:
        adsSyncDelDeviceNotificationReqEx(port, adr, notification, hUser)
    else:
        adsSyncDelDeviceNotificationReq(adr, notification, hUser)


class Connection(object):
    """
    Class for managing the connection to an ADS device.

    :ivar str ams_net_id: AMS net id of the remote device
    :ivar int ams_net_port: port of the remote device
    :ivar str ip_address: the ip address of the device

    :note: If no IP Adress is given the ip address is automatically set
        to first 4 parts of the Ams net id.

    """
    def __init__(self, ams_net_id, ams_net_port, ip_address=None):
        self._port = None
        self._adr = AmsAddr(ams_net_id, ams_net_port)
        if ip_address is None:
            self.ip_address = '.'.join(ams_net_id.split('.')[:4])
        else:
            self.ip_address = ip_address
        self._open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _type, _val, _traceback):
        self.close()

    def open(self):
        """
        :summary:  Connect to the TwinCAT message router.

        """
        if self._open:
            return
        if linux:
            self._port = adsPortOpenEx()
            adsAddRoute(self._adr.netIdStruct(), self.ip_address)
        else:
            self._port = adsPortOpen()
        self._open = True

    def close(self):
        """
        :summary: Close the connection to the TwinCAT message router.

        """
        if not self._open:
            return
        if linux:
            adsDelRoute(self._adr.netIdStruct())
            adsPortCloseEx(self._port)
            self._port = None
        else:
            adsPortClose()
        self._open = False

    def get_local_address(self):
        """
        :summary: Return the local AMS-address and the port number.
        :rtype: AmsAddr

        """
        if linux:
            return adsGetLocalAddressEx(self._port)
        else:
            return adsGetLocalAddress()

    def read_state(self):
        """
        :summary: Read the current ADS-state and the machine-state from the
            ADS-server
        :rtype: (int, int)
        :return: adsState, deviceState

        """
        if linux:
            return adsSyncReadStateReqEx(self._port, self._adr)
        else:
            return adsSyncReadStateReq(self._adr)

    def write_control(self, ads_state, device_state, data, plc_datatype):
        """
        :summary: Change the ADS state and the machine-state of the ADS-server

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
        if linux:
            return adsSyncWriteControlReqEx(self._port, self._adr, ads_state,
                                            device_state, data, plc_datatype)
        else:
            return adsSyncWriteControlReq(self._adr, ads_state, device_state,
                                          data, plc_datatype)

    def read_device_info(self):
        """
        :summary: Read the name and the version number of the ADS-server
        :rtype: string, AdsVersion
        :return: device name, version

        """
        if linux:
            return adsSyncReadDeviceInfoReqEx(self._port, self._adr)
        else:
            return adsSyncReadDeviceInfoReq(self._adr)

    def write(self, index_group, index_offset, value, plc_datatype):
        """
        :summary: Send data synchronous to an ADS-device

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants

        """
        if linux:
            return adsSyncWriteReqEx(self._port, self._adr, index_group,
                                     index_offset, value, plc_datatype)
        else:
            adsSyncWriteReq(self._adr, index_group, index_offset, value,
                            plc_datatype)

    def read_write(self, index_group, index_offset, plc_read_datatype,
                   value, plc_write_datatype):
        """
        :summary: Read and write data synchronous from/to an ADS-device
        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param int plc_read_datatype: type of the data given to the PLC to
            respond to, according to PLCTYPE constants
        :param value: value to write to the storage address of the PLC
        :param plc_write_datatype: type of the data given to the PLC,
            according to PLCTYPE constants
        :rtype: PLCTYPE
        :return: value: **value**

        """
        if linux:
            return adsSyncReadWriteReqEx2(self._port, self._adr, index_group,
                                          index_offset, plc_read_datatype,
                                          value, plc_write_datatype)
        else:
            return adsSyncReadWriteReq(self._adr, index_group, index_offset,
                                       plc_read_datatype, value,
                                       plc_write_datatype)

    def read(self, index_group, index_offset, plc_datatype):
        """
        :summary: Read data synchronous from an ADS-device
        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
        :return: value: **value**

        """
        if linux:
            return adsSyncReadReqEx2(self._port, self._adr, index_group,
                                     index_offset, plc_datatype)
        else:
            return adsSyncReadReq(self._adr, index_group, index_offset,
                                  plc_datatype)

    def read_by_name(self, data_name, plc_datatype):
        """
        :summary: Read data synchronous from an ADS-device from data name
        :param string data_name: data name
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
        :return: value: **value**

        """
        if linux:
            return adsSyncReadByNameEx(self._port, self._adr, data_name,
                                       plc_datatype)
        else:
            return adsSyncReadByName(self._adr, data_name, plc_datatype)

    def write_by_name(self, data_name, value, plc_datatype):
        """
        :summary: Send data synchronous to an ADS-device from data name

        :param string data_name: PLC storage address
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants

        """
        if linux:
            return adsSyncWriteByNameEx(self._port, self._adr, data_name,
                                        value, plc_datatype)
        else:
            return adsSyncWriteByName(self._adr, data_name, value,
                                      plc_datatype)

    def add_device_notification(self, data_name, attr, callback):
        """
        :summary: Add a device notification

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
            >>> plc = pyads.Connection('127.0.0.1.1.1', 851)
            >>>
            >>> # Create callback function
            >>> def mycallback(adr, notification, user):
            >>>     pass
            >>>
            >>> with plc:
            >>>
            >>>     # Add notification
            >>>     attr = pyads.NotificationAttrib()
            >>>     hnotification, huser = plc.add_device_notification(
            >>>         adr, attr, mycallback)
            >>>
            >>>     # Remove notification
            >>>     plc.del_device_notification(hnotification, huser)

        """
        if linux:
            return adsSyncAddDeviceNotificationReqEx(self._port, self._adr,
                                                     data_name, attr, callback)
        else:
            return adsSyncAddDeviceNotificationReq(self._adr, data_name,
                                                   attr, callback)

    def del_device_notification(self, notification, hUser):
        """
        :summary: Remove a device notification

        :param notification: address of the variable that contains the handle
            of the notification
        :param hUser: user handle

        """
        if linux:
            adsSyncDelDeviceNotificationReqEx(self._port, self._adr,
                                              notification, hUser)
        else:
            adsSyncDelDeviceNotificationReq(self._adr, notification,
                                            hUser)
    
    @property
    def is_open(self):
        """
        Shows the current connection state.

        :return: True if connection is open
        """
        return self._open
