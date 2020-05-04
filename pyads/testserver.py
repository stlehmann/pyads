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
from typing import Any, List, Type, Optional, DefaultDict, Tuple
from types import TracebackType
import atexit
import logging
import select
import socket
import struct
import threading

from collections import namedtuple, defaultdict

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
AmsResponseData = namedtuple("AmsResponseData", ("state_flags", "error_code", "data"))


class AdsTestServer(threading.Thread):
    """Simple ADS testing server.

    :ivar function handler: Request handler (see `default_handler` for example)
    :ivar str ip_address: Host address for server. Defaults to ''
    :ivar int port: Host port to listen on, defaults to 48898

    """

    def __init__(
        self, handler=None, ip_address="", port=ADS_PORT, logging=True, *args, **kwargs
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
                    handler=self.handler, client=client, address=address, server=self
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
                "Closing client connection {0}:{1}.".format(*self.client_address)
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
                response_bytes = self.construct_response(response, request_packet)

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

        ams_tcp_header = "\x00\x00".encode("utf-8") + struct.pack("<I", len(ams_header))

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
            response_length = struct.unpack("<I", request.ams_header.data[8:12])[0]
            # Create response of repeated 0x0F with a null terminator for strings
            response_value = (("\x0F" * (response_length - 1)) + "\x00").encode("utf-8")
            response_content = struct.pack("<I", len(response_value)) + response_value

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
            # Parse requested data length
            response_length = struct.unpack("<I", request.ams_header.data[8:12])[0]
            if response_length > 0:
                # Create response of repeated 0x0F with a null terminator for strings
                response_value = (("\x0F" * (response_length - 1)) + "\x00").encode(
                    "utf-8"
                )
            else:
                response_value = b""

            response_content = struct.pack("<I", len(response_value)) + response_value

        else:
            logger.info("Unknown Command: {0}".format(hex(command_id)))
            # Set error code to 'unknown command ID'
            error_code = "\x08\x00\x00\x00".encode("utf-8")
            return AmsResponseData(state, error_code, "".encode("utf-8"))

        # Set no error in response
        error_code = ("\x00" * 4).encode("utf-8")
        response_data = error_code + response_content

        return AmsResponseData(state, request.ams_header.error_code, response_data)


class PLCVariable:
    """Storage item for named data."""

    def __init__(self, name, value):
        # type: (str, Any) -> None
        self.name = name
        self.value = value


class AdvancedHandler(AbstractHandler):
    """The advanced handler allows to store and restore data.

    The advanced handler allows to store and restore data via read, write and
    read_write functions. There are two separate storage areas access by
    address and access by name. The purpose of this handler to test read/write
    access and test basic interaction.

    """

    def __init__(self):
        # type: () -> None
        self.reset()

    def reset(self):
        # type: () -> None
        self._data = defaultdict(
            lambda: bytes(16)
        )  # type: DefaultDict[Tuple[int, int], bytes]  # noqa: E501
        self._named_data = []  # type: Any

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
                ).format(index_group, index_offset, plc_datatype)
            )

            # value by handle is demanded return from named data store
            if index_group == constants.ADSIGRP_SYM_VALBYHND:

                response_value = self._named_data[index_offset].value

            else:
                # Create response of repeated 0x0F with a null
                # terminator for strings
                response_value = self._data[(index_group, index_offset)][:plc_datatype]

            return struct.pack("<I", len(response_value)) + response_value

        def handle_write():
            # type: () -> bytes
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
            # type: () -> bytes
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
                    self._named_data.append(PLCVariable(name=var_name, value=bytes(16)))
                    handle = len(self._named_data) - 1

                read_data = struct.pack("<I", handle)

            else:

                # read stored data
                read_data = self._data[(index_group, index_offset)][:read_length]

                # store write data
                self._data[(index_group, index_offset)] = write_data

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
        try:

            response_content = function_map[command_id]()

        except KeyError:
            logger.info("Unknown Command: {0}".format(hex(command_id)))
            # Set error code to 'unknown command ID'
            error_code = "\x08\x00\x00\x00".encode("utf-8")
            return AmsResponseData(state, error_code, "".encode("utf-8"))

        # Set no error in response
        error_code = ("\x00" * 4).encode("utf-8")
        response_data = error_code + response_content

        return AmsResponseData(state, request.ams_header.error_code, response_data)


if __name__ == "__main__":
    server = AdsTestServer(handler=AdvancedHandler())
    try:
        server.start()
        server.join()
    except:
        server.close()
