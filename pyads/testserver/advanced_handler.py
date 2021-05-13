"""Advanced handler module for testserver.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2017-09-15

"""
from typing import Optional, Union, Dict, Tuple, List
import struct
import ctypes
from datetime import datetime

from .handler import AbstractHandler, AmsPacket, AmsResponseData, logger
from pyads import constants, structs
from pyads.filetimes import dt_to_filetime
from pyads.pyads_ex import callback_store


class PLCVariable:
    """Storage item for named data.

    Also include variable type so it can be retrieved later.
    This basically mirrors SAdsSymbolEntry or AdsSymbol, however we want to
    avoid using those directly since they are test subjects.
    """

    handle_count = 10000  # Keep track of the latest awarded handle
    notification_count = 10  # Keep track the latest notification handle

    INDEX_GROUP = 12345
    INDEX_OFFSET_BASE = 10000

    def __init__(
        self,
        name: str,
        value: Union[int, float, bytes],
        ads_type: int,
        symbol_type: str,
        index_group: Optional[int] = None,
        index_offset: Optional[int] = None,
    ) -> None:
        """
        Handle and indices are set by default (to random but safe values)

        :param str name: variable name
        :param bytes value: variable value as bytes
        :param int ads_type: constants.ADST_*
        :param str symbol_type: PLC-style name of type
        :param Optional[int] index_group: set index_group manually
        :param Optional[int] index_offset: set index_offset manually
        """
        self.name = name.strip("\x00")

        # value is stored in binary!
        if isinstance(value, bytes):
            self.value = value
        else:
            # try to pack value according to ads_type
            fmt = constants.DATATYPE_MAP[constants.ads_type_to_ctype[ads_type]]
            self.value = struct.pack(fmt, value)

        self.ads_type = ads_type
        self.symbol_type = symbol_type

        self.handle = PLCVariable.handle_count
        PLCVariable.handle_count += 1

        if index_group is None:
            self.index_group = (
                PLCVariable.INDEX_GROUP
            )  # default value - shouldn't matter much
        else:
            self.index_group = index_group

        if index_offset is None:
            # cheat by using the handle as offset (since we know it will be unique)
            self.index_offset = PLCVariable.INDEX_OFFSET_BASE + self.handle
        else:
            self.index_offset = index_offset

        self.comment: str = ""

        self.notifications: List[int] = []  # List of associated notification handles

    @property
    def size(self) -> int:
        """Return size of value."""
        return len(self.value)

    def get_packed_info(self) -> bytes:
        """Get bytes array of symbol info"""
        if self.comment is None:
            self.comment = ""
        name_bytes = self.name.encode("utf-8")
        symbol_type_bytes = self.symbol_type.encode("utf-8")
        comment_bytes = self.comment.encode("utf-8")

        entry_length = (
            6 * 4
            + 3 * 2
            + len(name_bytes)
            + 1
            + len(symbol_type_bytes)
            + 1
            + len(comment_bytes)
        )

        read_data = (
            struct.pack(
                "<IIIIIIHHH",
                entry_length,  # Number of packed bytes
                self.index_group,
                self.index_offset,
                self.size,
                self.ads_type,
                0,  # Flags
                len(name_bytes),
                len(symbol_type_bytes),
                len(comment_bytes),
            )
            + name_bytes
            + b"\x20"
            + symbol_type_bytes
            + b"\x20"
            + comment_bytes
        )

        return read_data

    def write(self, value: bytes, request: AmsPacket = None):
        """Update the variable value, respecting notifications"""

        if self.value != value:
            if self.notifications:

                header = structs.SAdsNotificationHeader()
                header.hNotification = 0
                header.nTimeStamp = dt_to_filetime(datetime.now())
                header.cbSampleSize = len(value)

                # Perform byte-write into the header
                dst = ctypes.addressof(header) + structs.SAdsNotificationHeader.data.offset
                ctypes.memmove(dst, value, len(value))

                for notification_handle in self.notifications:

                    # It's hard to guess the exact AmsAddr from here, so instead
                    # ignore the address and search for the note_handle

                    for key, func in callback_store.items():

                        # callback_store is keyed by (AmsAddr, int)
                        if key[1] != notification_handle:
                            continue

                        header.hNotification = notification_handle
                        addr = key[0]

                        # Call c-wrapper for user callback
                        func(addr.amsAddrStruct(), header, 0)

        self.value = value

    def register_notification(self) -> int:
        """Register a new notification."""

        handle = self.notification_count
        self.notifications.append(handle)
        self.notification_count += 1
        return handle

    def unregister_notification(self, handle: int = None):
        """Unregister a notification.

        :param handle: Set to `None` (default) to unregister all notifications
        """

        if handle is None:
            self.notifications = []
        else:
            if handle in self.notifications:
                self.notifications.remove(handle)


class AdvancedHandler(AbstractHandler):
    """The advanced handler allows to store and restore data.

    The advanced handler allows to store and restore data via read, write and
    read_write functions. There is a storage area for each symbol. The
    purpose of this handler to test read/write access and test basic
    interaction.
    Variables can be read/write through indices, name and handle.

    An error will be thrown when an attempt is made to read from a
    non-existent variable. You can either: i) write the variable first (it
    is implicitly created) or ii) create the variable yourself and place it
    in the handler.
    Note that the variable type cannot be set correctly in the implicit
    creation! (It will default to UINT16.) Use explicit creation if a
    non-default type is important.
    """

    def __init__(self) -> None:
        self._data: Dict[Tuple[int, int], PLCVariable] = {}
        # This will be our variables database
        # We won't both with indexing it by handle or name, speed is not
        # important. We store by group + offset index and will have to
        # search inefficiently for name or handle. (Unlike real ADS!)

        self.reset()

    def reset(self) -> None:
        """Clear saved variables in handler"""
        self._data = {}

    def handle_request(self, request: AmsPacket) -> AmsResponseData:
        """Handle incoming requests and create a response."""
        # Extract command id from the request
        command_id_bytes = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id_bytes)[0]

        # Set AMS state correctly for response
        state = struct.unpack("<H", request.ams_header.state_flags)[0]
        state = state | 0x0001  # Set response flag
        state = struct.pack("<H", state)

        def handle_read_device_info() -> bytes:
            """Create dummy response: version 1.2.3, device name 'TestServer'."""
            logger.info("Command received: READ_DEVICE_INFO")

            major_version = "\x01".encode("utf-8")
            minor_version = "\x02".encode("utf-8")
            version_build = "\x03\x00".encode("utf-8")
            device_name = "TestServer\x00".encode("utf-8")

            response_content = (
                major_version + minor_version + version_build + device_name
            )

            return response_content

        def handle_read() -> bytes:
            """Handle read request."""
            data = request.ams_header.data

            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]

            logger.info(
                (
                    "Command received: READ (index group={}, index offset={}, "
                    "data length={})"
                ).format(hex(index_group), hex(index_offset), plc_datatype)
            )

            # value by handle is demanded return from named data store
            if index_group == constants.ADSIGRP_SYM_VALBYHND:
                response_value = self.get_variable_by_handle(index_offset).value

            elif index_group == constants.ADSIGRP_SYM_UPLOADINFO2:
                symbol_count = len(self._data)
                response_length = 120 * symbol_count
                response_value = struct.pack("II", symbol_count, response_length)

            elif index_group == constants.ADSIGRP_SYM_UPLOAD:
                response_value = b""
                for (group, offset) in self._data.keys():
                    response_value += struct.pack("III", 120, group, offset)
                    response_value += b"\x00" * 108

            else:
                # Create response of repeated 0x0F with a null
                # terminator for strings
                var = self.get_variable_by_indices(index_group, index_offset)
                response_value = var.value[:plc_datatype]

            return struct.pack("<I", len(response_value)) + response_value

        def handle_write() -> bytes:
            """Handle write request."""
            data = request.ams_header.data

            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]
            value = data[12 : (12 + plc_datatype)]

            logger.info(
                (
                    "Command received: WRITE (index group={}, index offset={}, "
                    "data length={}, value={}"
                ).format(hex(index_group), hex(index_offset), plc_datatype, value)
            )

            if index_group == constants.ADSIGRP_SYM_RELEASEHND:
                return b""

            elif index_group == constants.ADSIGRP_SYM_VALBYHND:
                var = self.get_variable_by_handle(index_offset)
                var.write(value, request)
                return b""

            var = self.get_variable_by_indices(index_group, index_offset)

            var.write(value, request)

            # no return value needed
            return b""

        def handle_read_write() -> bytes:
            """Handle read-write request."""
            data = request.ams_header.data

            # parse the request
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
                    hex(index_group),
                    hex(index_offset),
                    read_length,
                    write_length,
                    write_data,
                )
            )

            # Get variable handle by name if demanded
            if index_group == constants.ADSIGRP_SYM_HNDBYNAME:

                var_name = write_data.decode()

                # This could be part of a write-by-name, so create the
                # variable if it does not yet exist
                var = self.get_variable_by_name(var_name)

                read_data = struct.pack("<I", var.handle)

            # Get the symbol if requested
            elif index_group == constants.ADSIGRP_SYM_INFOBYNAMEEX:

                var_name = write_data.decode()
                var = self.get_variable_by_name(var_name)

                read_data = var.get_packed_info()

            # Write to a list of variables
            elif index_group == constants.ADSIGRP_SUMUP_WRITE:
                num_requests = index_offset  # number of requests is coded in the offset for sumup_write
                rq_list = [
                    (
                        struct.unpack("<I", write_data[i : i + 4])[0],  # index_group
                        struct.unpack("<I", write_data[i + 4 : i + 8])[
                            0
                        ],  # index_offset
                        struct.unpack("<I", write_data[i + 8 : i + 12])[0],  # size
                    )
                    for i in range(0, num_requests * 12, 12)
                ]

                data = write_data[num_requests * 12 :]
                offset = 0

                for index_group, index_offset, size in rq_list:
                    var = self.get_variable_by_indices(index_group, index_offset)
                    var.write(data[offset : offset + size], request)
                    offset += size

                read_data = struct.pack("<" + num_requests * "I", *(num_requests * [0]))

            # Read a list of variables
            elif index_group == constants.ADSIGRP_SUMUP_READ:
                num_requests = index_offset
                rq_list = [
                    (
                        struct.unpack("<I", write_data[i : i + 4])[0],  # index_group
                        struct.unpack("<I", write_data[i + 4 : i + 8])[
                            0
                        ],  # index_offset
                        struct.unpack("<I", write_data[i + 8 : i + 12])[0],  # size
                    )
                    for i in range(0, num_requests * 12, 12)
                ]

                read_data = struct.pack("<" + num_requests * "I", *(num_requests * [0]))
                for index_group, index_offset, size in rq_list:
                    var = self.get_variable_by_indices(index_group, index_offset)
                    read_data += var.value

            # Else just return the value stored
            else:

                # read stored data
                var = self.get_variable_by_indices(index_group, index_offset)
                read_data = var.value[:read_length]

                # store write data
                var.write(write_data, request)

            return struct.pack("<I", len(read_data)) + read_data

        def handle_read_state() -> bytes:
            """Handle read-state request."""
            logger.info("Command received: READ_STATE")
            ads_state = struct.pack("<H", constants.ADSSTATE_RUN)
            # I don't know what an appropriate value for device state is.
            # I suspect it may be unused..
            device_state = struct.pack("<H", 0)
            return ads_state + device_state

        def handle_writectrl() -> bytes:
            """Handle writectrl request."""
            logger.info("Command received: WRITE_CONTROL")
            # No response data required
            return b""

        def handle_add_devicenote() -> bytes:
            """Handle add_devicenode request.

            The actual callback is stored in `pyads_ex.callback_store`. All we need to do
            here is remember to prompt the client with an updated value if a callback was
            placed. The client will remember which callback belongs to it.
            """

            data = request.ams_header.data

            index_group, index_offset, length, mode, max_delay, cycle_time = \
                struct.unpack("<IIIIII", data[:24])

            logger.info(
                "Command received: ADD_DEVICE_NOTIFICATION (index_group={}, "
                "index_group={})".format(index_group, index_offset)
            )

            # Return value is the notification_handle
            # The notification handle is an incrementing value

            var = self.get_variable_by_indices(index_group, index_offset)

            handle = var.register_notification()

            return handle.to_bytes(4, byteorder='little')

        def handle_delete_devicenote() -> bytes:
            """Handle delete_devicenode request."""

            data = request.ams_header.data

            handle = struct.unpack("<I", data[:4])[0]

            logger.info("Command received: DELETE_DEVICE_NOTIFICATION (handle={})".format(handle))

            var = self.get_variable_by_notification_handle(handle)
            var.unregister_notification(handle)

            # No response data required
            return b""

        def handle_devicenote() -> bytes:
            """Handle a device notification."""
            logger.info("Command received: DEVICE_NOTIFICATION")
            # No response data required
            return b""

        # Function map
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

        # Try to map the command id to a function, else return error code
        if command_id in function_map:
            content = function_map[command_id]()

        else:
            logger.info("Unknown Command: {0}".format(hex(command_id)))
            # Set error code to 'unknown command ID'
            error_code = "\x08\x00\x00\x00".encode("utf-8")
            return AmsResponseData(state, error_code, "".encode("utf-8"))

        # Set no error in response
        error_code = ("\x00" * 4).encode("utf-8")
        response_data = error_code + content

        return AmsResponseData(state, request.ams_header.error_code, response_data)

    def get_variable_by_handle(self, handle: int) -> PLCVariable:
        """Get PLC variable by handle, throw error when not found"""
        for idx, var in self._data.items():
            if var.handle == handle:
                return var

        raise KeyError(
            "Variable with handle `{}` not found - Create it first "
            "explicitly or write to it".format(handle)
        )

    def get_variable_by_indices(
        self, index_group: int, index_offset: int
    ) -> PLCVariable:
        """Get PLC variable by handle, throw error when not found"""
        tup = (index_group, index_offset)
        if tup in self._data:
            return self._data[tup]
        raise KeyError(
            "Variable with indices ({}, {}) not found - Create "
            "it first explicitly or write to it".format(index_group, index_offset)
        )

    def get_variable_by_name(self, name: str) -> PLCVariable:
        """Get variable by name, throw error if not found"""
        name = name.strip("\x00")
        for key, var in self._data.items():
            if var.name == name:
                return var
        raise KeyError(
            "Variable with name `{}` not found - Create it first "
            "explicitly or write to it".format(name)
        )

    def get_variable_by_notification_handle(self, handle: int) -> PLCVariable:
        """Get variable by a notification handle, throw error if not found"""
        for _, var in self._data.items():
            if handle in var.notifications:
                return var

        raise KeyError("Notification handle `{}` could not be resolved".format(handle))

    def add_variable(self, var: PLCVariable) -> None:
        """Add a new variable."""
        tup = (var.index_group, var.index_offset)
        self._data[tup] = var
