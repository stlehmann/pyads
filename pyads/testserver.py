# -*- coding: utf-8 -*-
"""Extended ADS TCP/IP server implementation.

Extended ADS TCP/IP server implementation to allow for functional testing of
the ADS protocol without connection to a physical device.

Consists of a server thread which will listen for connections and delegate
each new connection to a separate client thread, allowing for multiple clients
to connect at once.

Each client connection thread listens for incoming data, and delegates parsing
and response construction to the handler. A handler function is injectable at
server level by specifying the `handler` kwarg in the server constructor.

:author: David Browne <davidabrowne@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53
:last modified by:   Stefan Lehmann
:last modified time: 2018-08-26 22:38:06

"""
from __future__ import absolute_import
from typing import Any, List, Type, Optional, Dict, Tuple
from types import TracebackType
import atexit
import logging
import select
import socket
import struct
import threading

from collections import namedtuple

from pyads import constants

# Log to stdout by default
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(levelname)s:%(message)s")
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False  # "Overwrite" default handler

null_logger = logging.getLogger(__name__ + "_null")
null_logger.addHandler(logging.NullHandler())

ADS_PORT = 0xBF02

# Container for data in the 'AMS/TCP header' component of an AMS packet
AmsTcpHeader = namedtuple("AmsTcpHeader", ("length",))

# Container for data in the 'AMS header' component of an AMS packet
AmsHeader = namedtuple(
    "AmsHeader",
    (
        "target_net_id",
        "target_port",
        "source_net_id",
        "source_port",
        "command_id",
        "state_flags",
        "length",
        "error_code",
        "invoke_id",
        "data",
    ),
)

# Container for the entire AMS/TCP packet
AmsPacket = namedtuple("AmsPacket", ("tcp_header", "ams_header"))

# Container for the data required to construct an AMS response given a request
AmsResponseData = namedtuple("AmsResponseData",
                             ("state_flags", "error_code", "data"))


class AdsTestServer(threading.Thread):
    """Simple ADS testing server.

    :ivar function handler: Request handler (see `default_handler` for example)
    :ivar str ip_address: Host address for server. Defaults to ''
    :ivar int port: Host port to listen on, defaults to 48898

    """

    def __init__(
            self, handler=None, ip_address="", port=ADS_PORT,
            logging=True, *args, **kwargs
    ):
        # type: (AbstractHandler, str, int, bool, Any, Any) -> None
        self.handler = handler or BasicHandler()
        self.ip_address = ip_address
        self.port = port
        self._run = True

        global logger
        logger = logger if logging else null_logger

        # Keep track of all received AMS packets
        self.request_history = []  # type: List[AmsPacket]

        # Initialize TCP/IP socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set option to allow instant socket reuse after shutdown
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server.bind((self.ip_address, self.port))

        # Make sure we clean up on exit
        atexit.register(self.close)

        # Daemonize the server thread

        # Container for client connection threads
        self.clients = []  # type: List[AdsClientConnection]

        super(AdsTestServer, self).__init__(*args, **kwargs)
        self.daemon = True

    def __enter__(self):
        # type: () -> AdsTestServer
        """Enter context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None  # noqa: E501
        """Exit context."""
        self.close()

    def stop(self):
        # type: () -> None
        """Close client connections and stop main server loop."""
        # Close all client connections
        for client in self.clients:
            client.close()

        self.clients = []

        if self._run:
            logger.info("Stopping server thread.")
            # Stop server loop execution
            self._run = False

        self.server.close()

    def close(self):
        # type: () -> None
        """Close the server thread."""
        self.stop()

    def run(self):
        # type: () -> None
        """Listen for incoming connections from clients."""
        self._run = True

        # Start server listening
        self.server.listen(5)

        logger.info(
            "Server listening on {0}:{1}".format(
                self.ip_address or "localhost", self.port
            )
        )

        # Server loop
        while self._run:
            # Check for new connections at server socket
            ready, _, _ = select.select([self.server], [], [], 0.1)

            if ready:
                # Accept connection from client
                try:
                    client, address = self.server.accept()
                except:
                    continue

                logger.info("New connection from {0}:{1}".format(*address))

                # Delegate handling of connection to client thread
                client_thread = AdsClientConnection(
                    handler=self.handler, client=client, address=address,
                    server=self
                )

                client_thread.daemon = True
                client_thread.start()
                self.clients.append(client_thread)


class AdsClientConnection(threading.Thread):
    """Connection thread to an ADS client."""

    def __init__(self, handler, client, address, server, *args, **kwargs):
        # type: (AbstractHandler, socket.socket, str, AdsTestServer, Any, Any) -> None
        self.handler = handler
        self.server = server
        self.client = client
        self.client_address = address

        # Make sure we clean up on exit
        atexit.register(self.close)

        # Server loop execution flag
        self._run = True

        super(AdsClientConnection, self).__init__(*args, **kwargs)

    def stop(self):
        # type: () -> None
        """Stop the client thread."""
        if self._run:
            logger.info(
                "Closing client connection {0}:{1}.".format(
                    *self.client_address)
            )
            self._run = False

        self.join()

    def close(self):
        # type: () -> None
        """Close the client connection."""
        if self.is_alive():
            self.stop()
        self.client.close()

    def run(self):
        # type: () -> None
        """Listen for data on client connection and delegate requests."""
        self._run = True

        # Main listening loop
        while self._run:
            ready, _, _ = select.select([self.client], [], [], 0.1)

            if not ready:
                continue

            data, _ = self.client.recvfrom(4096)

            if not data:
                self.client.close()
                self._run = False
                continue

            # Basic data validation
            if len(data) < 38:
                logger.warning(
                    "Malformed packet discarded from {0}:{1}:\n\t{data}".format(
                        *self.client_address, data=data
                    )
                )
                continue

            # Construct AmsPacket tuple containing request data
            request_packet = self.construct_request(data)

            self.server.request_history.append(request_packet)

            # Delegate request handling and get response data
            response = self.handler.handle_request(request_packet)

            if isinstance(response, (AmsResponseData,)):
                # Convert request, response data (tuples) to a valid ADS
                # response (bytes) to return to the client
                response_bytes = self.construct_response(response,
                                                         request_packet)

                self.client.send(response_bytes)

                continue

            logger.error("Request handler failed to return a valid response.")

    def construct_response(self, response_data, request):
        # type: (AmsResponseData, AmsPacket) -> bytes
        """Construct binary AMS response to return to the client.

        :param AmsResponseData response_data: Data to include in the response
        :param AmsPacket request: The originating request for the response

        """
        # Response gets returned to the source, so flip source and target
        target_net_id = request.ams_header.source_net_id
        target_port = request.ams_header.source_port
        source_net_id = request.ams_header.target_net_id
        source_port = request.ams_header.target_port

        # Command ID and invoke ID should be same as in the request
        command_id = request.ams_header.command_id
        invoke_id = request.ams_header.invoke_id

        # Use state flags as specified in response data
        state_flags = response_data.state_flags

        # Calculate payload length and unpack to binary data
        ams_length = struct.pack("<I", len(response_data.data))

        # Use error code specified in response data
        error_code = response_data.error_code

        data = response_data.data

        # Below we [ab]use `encode` to get a py2/3 compatible binary object
        # (str in py2, or bytes in py3)

        # Concatenate ams header data into single binary object
        ams_header = "".encode("utf-8").join(
            (
                target_net_id,
                target_port,
                source_net_id,
                source_port,
                command_id,
                state_flags,
                ams_length,
                error_code,
                invoke_id,
                data,
            )
        )

        ams_tcp_header = "\x00\x00".encode("utf-8") + struct.pack("<I", len(
            ams_header))

        return ams_tcp_header + ams_header

    def construct_request(self, request_bytes):
        # type: (bytes) -> AmsPacket
        """Unpack an AMS packet from binary data.

        :param bytes request_bytes: The raw request data
        :rtype AmsPacket:
        :return: AmsPacket with fields populated from the binary data

        """
        data = request_bytes  # Use a shorter name for brevity

        tcp_header = AmsTcpHeader(data[2:6])

        ams_header = AmsHeader(
            # Extract target/source net ID's and ports
            data[6:12],
            data[12:14],
            data[14:20],
            data[20:22],
            # Extract command ID, state flags, and data length
            data[22:24],
            data[24:26],
            data[26:30],
            # Extract error code, invoke ID, and data
            data[30:34],
            data[34:38],
            data[38:],
        )

        return AmsPacket(tcp_header, ams_header)


class AbstractHandler:
    """Abstract Handler class to provide a base class for handling requests."""

    def handle_request(self, request):
        # type: (AmsPacket) -> AmsResponseData
        """Handle incoming requests.

        :param AmsPacket request: The request data received from the client
        :rtype: AmsResponseData
        :return: Data needed to construct the AMS response packet

        """
        raise not NotImplementedError()  # type: ignore


class BasicHandler(AbstractHandler):
    """Basic request handler.

    Basic request handler to print the request data and return some default values.

    """

    def handle_request(self, request):
        # type: (AmsPacket) -> AmsResponseData
        """Handle incoming requests and send a response."""
        # Extract command id from the request
        command_id_bytes = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id_bytes)[0]

        # Set AMS state correctly for response
        state = struct.unpack("<H", request.ams_header.state_flags)[0]
        state = state | 0x0001  # Set response flag
        state = struct.pack("<H", state)

        # Handle request
        if command_id == constants.ADSCOMMAND_READDEVICEINFO:
            logger.info("Command received: READ_DEVICE_INFO")

            # Create dummy response: version 1.2.3, device name 'TestServer'
            major_version = "\x01".encode("utf-8")
            minor_version = "\x02".encode("utf-8")
            version_build = "\x03\x00".encode("utf-8")
            device_name = "TestServer\x00".encode("utf-8")

            response_content = (
                    major_version + minor_version + version_build + device_name
            )

        elif command_id == constants.ADSCOMMAND_READ:
            logger.info("Command received: READ")
            # Parse requested data length
            response_length = \
                struct.unpack("<I", request.ams_header.data[8:12])[0]
            # Create response of repeated 0x0F with a null terminator for strings
            response_value = (
                    ("\x0F" * (response_length - 1)) + "\x00").encode(
                "utf-8")
            response_content = struct.pack("<I", len(
                response_value)) + response_value

        elif command_id == constants.ADSCOMMAND_WRITE:
            logger.info("Command received: WRITE")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_READSTATE:
            logger.info("Command received: READ_STATE")
            ads_state = struct.pack("<H", constants.ADSSTATE_RUN)
            # I don't know what an appropriate value for device state is.
            # I suspect it may be unsued..
            device_state = struct.pack("<H", 0)

            response_content = ads_state + device_state

        elif command_id == constants.ADSCOMMAND_WRITECTRL:
            logger.info("Command received: WRITE_CONTROL")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_ADDDEVICENOTE:
            logger.info("Command received: ADD_DEVICE_NOTIFICATION")
            handle = ("\x0F" * 4).encode("utf-8")
            response_content = handle

        elif command_id == constants.ADSCOMMAND_DELDEVICENOTE:
            logger.info("Command received: DELETE_DEVICE_NOTIFICATION")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_DEVICENOTE:
            logger.info("Command received: DEVICE_NOTIFICATION")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_READWRITE:
            logger.info("Command received: READ_WRITE")
            # parse the request
            index_group = struct.unpack("<I", request.ams_header.data[:4])[0]
            response_length = \
                struct.unpack("<I", request.ams_header.data[8:12])[0]
            write_length = struct.unpack("<I", request.ams_header.data[12:16])[
                0]
            write_data = request.ams_header.data[16: (16 + write_length)]

            if index_group == constants.ADSIGRP_SYM_INFOBYNAMEEX:
                # Pack the structure in the same format as SAdsSymbolEntry.
                # Only 'EntrySize' (first field) and Type will be filled.
                # Use fixed UINT8 type
                if "str_" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 5, constants.ADST_STRING, 0, 0,
                        0, 0
                    )
                # Non-existant type
                elif "no_type" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 5, 1, 0, 0, 0, 0
                    )
                # Array
                elif "ar_" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 2, constants.ADST_UINT8, 0, 0,
                        0, 0
                    )
                else:
                    logger.info("Packing ADST_UINT8...")
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 1, constants.ADST_UINT8, 0, 0,
                        0, 0
                    )

            elif index_group == constants.ADSIGRP_SUMUP_READ:
                # Could be improved to handle variable length requests
                response_value = struct.pack(
                    "<IIIIBB4sB", 0, 0, 0, 1, 1, 2,
                    ("test" + "\x00").encode("utf-8"), 0
                )

            elif index_group == constants.ADSIGRP_SUMUP_WRITE:
                response_value = struct.pack("<IIII", 0, 0, 0, 1)

            elif response_length > 0:
                # Create response of repeated 0x0F with a null terminator for strings
                response_value = (
                        ("\x0F" * (response_length - 1)) + "\x00").encode(
                    "utf-8"
                )
            else:
                response_value = b""

            response_content = struct.pack("<I", len(
                response_value)) + response_value

        else:
            logger.info("Unknown Command: {0}".format(hex(command_id)))
            # Set error code to 'unknown command ID'
            error_code = "\x08\x00\x00\x00".encode("utf-8")
            return AmsResponseData(state, error_code, "".encode("utf-8"))

        # Set no error in response
        error_code = ("\x00" * 4).encode("utf-8")
        response_data = error_code + response_content

        return AmsResponseData(state, request.ams_header.error_code,
                               response_data)


class PLCVariable:
    """Storage item for named data

    Also include variable type so it can be retrieved later.
    This basically mirrors SAdsSymbolEntry or AdsSymbol, however we want to
    avoid using those directly since they are test subjects.
    """

    handle_count = 0  # Keep track of the latest awarded handle

    INDEX_GROUP = 12345
    INDEX_OFFSET_BASE = 10000

    def __init__(self,
                 name="unnamed",
                 value=bytes(16),
                 ads_type=constants.ADST_UINT8,
                 symbol_type='UINT'):
        # type: (str, bytes, int, str) -> None
        """

        Handle and indices are set by default (to random but safe values)

        :param name:
        :param value:
        :param ads_type: constants.PLCTYPE_*
        :param symbol_type: PLC-style name of type
        """
        self.name = name
        self.value = value  # type: bytes
        # Variable value is stored in binary!

        self.ads_type = None  # type: Optional[int]
        self.symbol_type = None  # type: Optional[str]
        self.plc_type = None  # type: Any

        self.set_type(ads_type, symbol_type)

        self.handle = self.handle_count
        self.index_group = self.INDEX_GROUP  # Default value - shouldn't
        # matter much
        self.index_offset = self.INDEX_OFFSET_BASE + self.handle  # We will
        # cheat by using the handle (since we know it will be unique)

        self.comment = ''  # type: str

        self.size = 2  # Value size in bytes

        self.handle_count += 1  # Increment class property

    def set_type(self, ads_type, symbol_type):
        # type: (int, str) -> None
        """Set a new ADST_ variable type (also update PLCTYPE_

        However, the symbol_type string cannot be updated automatically!
        """
        self.ads_type = ads_type
        if ads_type in constants.ads_type_to_ctype:
            self.plc_type = constants.ads_type_to_ctype[ads_type]
        self.symbol_type = symbol_type

    def get_packed_info(self):
        # type: () -> bytes
        """Get bytes array of symbol info"""
        # str_buffer = var.name.encode('utf-8') + \
        #              var.symbol_type.encode('utf-8')
        if self.comment is None:
            self.comment = ""
        name_bytes = self.name.encode('utf-8')
        symbol_type_bytes = self.symbol_type.encode('utf-8')
        comment_bytes = self.comment.encode('utf-8')

        entry_length = 6 * 4 + 3 * 2 + len(name_bytes) \
                             + 1 + len(symbol_type_bytes) + 1 \
                             + len(comment_bytes)

        read_data = struct.pack(
            "<IIIIIIHHH",
            entry_length,  # Number of packed bytes
            self.index_group,
            self.index_offset,
            self.size,
            self.ads_type,
            0,  # Flags
            len(name_bytes),
            len(symbol_type_bytes),
            len(comment_bytes)
        ) + name_bytes + b'\x20' + symbol_type_bytes + b'\x20' \
          + comment_bytes

        return read_data


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

    def __init__(self):
        # type: () -> None

        self._data = {}  # type: Dict[Tuple[int, int], PLCVariable]
        # This will be our variables database
        # We won't both with indexing it by handle or name, speed is not
        # important. We store by group + offset index and will have to
        # search inefficiently for name or handle. (Unlike real ADS!)

        self.reset()

    def reset(self):
        # type: () -> None
        """Clear saved variables in handler"""
        self._data = {}

    def handle_request(self, request):
        # type: (AmsPacket) -> AmsResponseData
        """Handle incoming requests and create a response."""
        # Extract command id from the request
        command_id_bytes = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id_bytes)[0]

        # Set AMS state correctly for response
        state = struct.unpack("<H", request.ams_header.state_flags)[0]
        state = state | 0x0001  # Set response flag
        state = struct.pack("<H", state)

        def handle_read_device_info():
            # type: () -> bytes
            """Create dummy response: version 1.2.3, device name 'TestServer'
            """
            logger.info("Command received: READ_DEVICE_INFO")

            major_version = "\x01".encode("utf-8")
            minor_version = "\x02".encode("utf-8")
            version_build = "\x03\x00".encode("utf-8")
            device_name = "TestServer\x00".encode("utf-8")

            response_content = (
                    major_version + minor_version + version_build + device_name
            )

            return response_content

        def handle_read():
            # type: () -> bytes
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

                # response_value = self._named_data[index_offset].value
                response_value = self.get_variable_by_handle(
                    index_offset).value

            elif index_group == constants.ADSIGRP_SYM_UPLOADINFO2:
                symbol_count = len(self._data)
                response_length = 120 * symbol_count
                response_value = struct.pack(
                    "II", symbol_count, response_length)

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

        def handle_write():
            # type: () -> bytes
            """Handle write request."""
            data = request.ams_header.data

            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]
            value = data[12:(12 + plc_datatype)]

            logger.info(
                (
                    "Command received: WRITE (index group={}, index offset={}, "
                    "data length={}, value={}"
                ).format(hex(index_group), hex(index_offset), plc_datatype,
                         value)
            )

            if index_group == constants.ADSIGRP_SYM_RELEASEHND:
                return b""

            elif index_group == constants.ADSIGRP_SYM_VALBYHND:
                var = self.get_variable_by_handle(index_offset)
                var.value = value
                return b""

            var = self.get_or_create_variable_by_indices(
                index_group, index_offset)
            var.value = value

            # no return value needed
            return b""

        def handle_read_write():
            # type: () -> bytes
            """Handle read-write request."""
            data = request.ams_header.data

            # parse the request
            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            read_length = struct.unpack("<I", data[8:12])[0]
            write_length = struct.unpack("<I", data[12:16])[0]
            write_data = data[16:(16 + write_length)]

            logger.info(
                (
                    "Command received: READWRITE "
                    "(index group={}, index offset={}, read length={}, "
                    "write length={}, write data={})"
                ).format(
                    hex(index_group), hex(index_offset), read_length,
                    write_length, write_data
                )
            )

            # Get variable handle by name if demanded
            if index_group == constants.ADSIGRP_SYM_HNDBYNAME:

                var_name = write_data.decode()

                # This could be part of a write-by-name, so create the
                # variable if it does not yet exist
                var = self.get_or_create_variable_by_name(var_name)

                read_data = struct.pack("<I", var.handle)

            # Get the symbol if requested
            elif index_group == constants.ADSIGRP_SYM_INFOBYNAMEEX:

                var_name = write_data.decode()
                var = self.get_variable_by_name(var_name)

                read_data = var.get_packed_info()

            # Else just return the value stored
            else:

                # read stored data
                var = self.get_variable_by_indices(index_group, index_offset)
                read_data = var.value[:read_length]

                # store write data
                var.value = write_data

            return struct.pack("<I", len(read_data)) + read_data

        def handle_read_state():
            # type: () -> bytes
            """Handle reas-state request."""
            logger.info("Command received: READ_STATE")
            ads_state = struct.pack("<I", constants.ADSSTATE_RUN)
            # I don't know what an appropriate value for device state is.
            # I suspect it may be unsued..
            device_state = struct.pack("<I", 0)
            return ads_state + device_state

        def handle_writectrl():
            # type: () -> bytes
            """Handle writectrl request."""
            logger.info("Command received: WRITE_CONTROL")
            # No response data required
            return b""

        def handle_add_devicenote():
            # type: () -> bytes
            """Handle add_devicenode request."""
            logger.info("Command received: ADD_DEVICE_NOTIFICATION")
            handle = ("\x0F" * 4).encode("utf-8")
            return handle

        def handle_delete_devicenote():
            # type: () -> bytes
            """Handle delete_devicenode request."""
            logger.info("Command received: DELETE_DEVICE_NOTIFICATION")
            # No response data required
            return b""

        def handle_devicenote():
            # type: () -> bytes
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

        return AmsResponseData(state, request.ams_header.error_code,
                               response_data)

    def get_variable_by_handle(self, handle):
        # type: (int) -> PLCVariable
        """Get PLC variable by handle, throw error when not found"""

        for idx, var in self._data.items():
            if var.handle == handle:
                return var

        raise KeyError('Variable with handle `{}` not found - Create it first '
                       'explicitly or write to it'.format(handle))

    def get_variable_by_indices(self, index_group, index_offset):
        # type: (int, int) -> PLCVariable
        """Get PLC variable by handle, throw error when not found"""

        tup = (index_group, index_offset)

        if tup in self._data:
            return self._data[tup]

        raise KeyError('Variable with indices ({}, {}) not found - Create '
                       'it first explicitly or write to it'
                       .format(index_group, index_offset))

    def get_or_create_variable_by_indices(self, index_group, index_offset):
        # type: (int, int) -> PLCVariable
        """Try to retrieve a variable by indices, create it if non-existent"""
        try:
            return self.get_variable_by_indices(index_group, index_offset)
        except KeyError:
            var = PLCVariable()
            var.index_group = index_group
            var.index_offset = index_offset
            self.add_variable(var)
            return var

    def get_variable_by_name(self, name):
        # type: (str) -> PLCVariable
        """Get variable by name, throw error if not found"""

        name = name.strip('\x00')

        for key, var in self._data.items():
            if var.name == name:
                return var

        raise KeyError('Variable with name `{}` not found - Create it first '
                       'explicitly or write to it'.format(name))

    def get_or_create_variable_by_name(self, name):
        # type: (str) -> PLCVariable
        """Try to retrieve a variable by indices, create it if non-existent"""
        try:
            return self.get_variable_by_name(name)
        except KeyError:
            var = PLCVariable(name=name)
            self.add_variable(var)
            return var

    def add_variable(self, var):
        # type: (PLCVariable) -> None
        tup = (var.index_group, var.index_offset)
        self._data[tup] = var


def main():
    """Main function (keep variable out of global scope)"""
    server = AdsTestServer(handler=AdvancedHandler())
    try:
        server.start()
        server.join()
    except:
        server.close()


if __name__ == "__main__":
    main()
