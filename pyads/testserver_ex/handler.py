import logging
import struct
from collections import defaultdict, namedtuple
from .. import constants
from .structs import AmsPacket, AmsTcpHeader, AmsHeader


logger = logging.getLogger(__name__)


NotifyClient = namedtuple("NotifyClient", "length client handle")


class PLCVariable:
    """ Storage item for named data """

    def __init__(self, name, value):
        self.name = name
        self._value = value
        self.notify_clients = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        for notify_client in self.notify_clients:
            notify_client.client.pending_notifications.append(
                (self, notify_client.length, notify_client.handle)
            )


class AdvancedHandler:
    def __init__(self):
        self._data = defaultdict(lambda: bytearray(16))
        self._named_data = []
        self.notification_count = 0

    def handle_request(self, request, client):
        def handle_read_device_info():
            """
            Create dummy response: version 1.2.3, device name 'TestServer'

            """
            logger.info("Command received: READ_DEVICE_INFO")

            major_version = "\x01".encode("utf-8")
            minor_version = "\x02".encode("utf-8")
            version_build = "\x03\x00".encode("utf-8")
            device_name = "TestServer\x00".encode("utf-8")
            result = b"\x00" * 4

            return result + major_version + minor_version + version_build + device_name

        def handle_read():
            data = request.ads_data
            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]

            logger.info(
                (
                    "Command received: READ (index group={}, index offset={}, "
                    "data length={})"
                ).format(index_group, index_offset, plc_datatype)
            )

            # value by handle is demanded return from named data store
            if index_group == constants.ADSIGRP_SYM_VALBYHND:

                response_value = self._named_data[index_offset].value

            else:
                # Create response of repeated 0x0F with a null
                # terminator for strings
                response_value = self._data[(index_group, index_offset)][:plc_datatype]

            result = b"\x00" * 4

            return result + struct.pack("<I", len(response_value)) + response_value

        def handle_write():
            data = request.ads_data

            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]
            value = data[12 : (12 + plc_datatype)]

            logger.info(
                (
                    "Command received: WRITE (index group={0}, index offset={1}, "
                    "length={2}, value={3})"
                ).format(index_group, index_offset, plc_datatype, value)
            )

            if index_group == constants.ADSIGRP_SYM_RELEASEHND:
                return b""

            elif index_group == constants.ADSIGRP_SYM_VALBYHND:
                self._named_data[index_offset].value = value
                return b""

            self._data[(index_group, index_offset)] = value

            # no return value needed
            return b""

        def handle_read_write():
            data = request.ads_data

            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            read_length = struct.unpack("<I", data[8:12])[0]
            write_length = struct.unpack("<I", data[12:16])[0]
            write_data = data[16 : (16 + write_length)]

            logger.info(
                (
                    "Command received: READWRITE "
                    "(index group={}, index offset={}, read length={}, "
                    "write length={}, write data={})"
                ).format(
                    index_group, index_offset, read_length, write_length, write_data
                )
            )

            # Get variable handle by name if  demanded
            # else just return the value stored
            if index_group == constants.ADSIGRP_SYM_HNDBYNAME:

                var_name = write_data.decode()

                # Try to find var name in named vars
                names = [x.name for x in self._named_data]

                try:
                    handle = names.index(var_name)
                except ValueError:
                    self._named_data.append(
                        PLCVariable(name=var_name, value=bytearray(16))
                    )
                    handle = len(self._named_data) - 1

                read_data = struct.pack("<I", handle)

            else:

                # read stored data
                read_data = self._data[(index_group, index_offset)][:read_length]

                # store write data
                self._data[(index_group, index_offset)] = write_data

            result = b"\x00" * 4
            return result + struct.pack("<I", len(read_data)) + read_data

        def handle_read_state():
            logger.info("Command received: READ_STATE")
            ads_state = struct.pack("<H", constants.ADSSTATE_RUN)
            # I don't know what an appropriate value for device state is.
            # I suspect it may be unsued..
            device_state = struct.pack("<H", 0)
            result = b"\x00" * 4
            return result + ads_state + device_state

        def handle_writectrl():
            logger.info("Command received: WRITE_CONTROL")
            # No response data required
            result = b"\x00" * 4
            return result

        def handle_add_devicenote():
            data = request.ads_data
            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            length = struct.unpack("<I", data[8:12])[0]

            if index_group == constants.ADSIGRP_SYM_VALBYHND:
                plc_var = self._named_data[index_offset]
                plc_var.notify_clients.append(
                    NotifyClient(length, client, handle=self.notification_count)
                )

            logger.info("Command received: ADD_DEVICE_NOTIFICATION")

            handle = struct.pack("<I", self.notification_count)
            result = b"\x00" * 4
            self.notification_count += 1
            return result + handle

        def handle_delete_devicenote():
            logger.info("Command received: DELETE_DEVICE_NOTIFICATION")
            # No response data required
            result = b"\x00" * 4
            return result

        def handle_devicenote():
            logger.info("Command received: DEVICE_NOTIFICATION")
            # No response data required
            result = b"\x00" * 4
            return result

        function_map = {
            constants.ADSCOMMAND_READDEVICEINFO: handle_read_device_info,
            constants.ADSCOMMAND_READ: handle_read,
            constants.ADSCOMMAND_WRITE: handle_write,
            constants.ADSCOMMAND_READWRITE: handle_read_write,
            constants.ADSCOMMAND_READSTATE: handle_read_state,
            constants.ADSCOMMAND_WRITECTRL: handle_writectrl,
            constants.ADSCOMMAND_ADDDEVICENOTE: handle_add_devicenote,
            constants.ADSCOMMAND_DELDEVICENOTE: handle_delete_devicenote,
            constants.ADSCOMMAND_DEVICENOTE: handle_devicenote,
        }

        response_content = function_map[request.ams_header.command_id]()

        return AmsPacket(
            amstcp_header=AmsTcpHeader(37 + len(response_content)),
            ams_header=AmsHeader(
                # swap target and source ams-id and port
                target_net_id=request.ams_header.source_net_id,
                target_port=request.ams_header.source_port,
                source_net_id=request.ams_header.target_net_id,
                source_port=request.ams_header.target_port,
                # mirror the command id from the request
                command_id=request.ams_header.command_id,
                # set response flag
                state_flags=request.ams_header.state_flags | 0x0001,
                data_length=len(response_content),
                error_code=0,
                invoke_id=request.ams_header.invoke_id,
            ),
            ads_data=response_content,
        )
