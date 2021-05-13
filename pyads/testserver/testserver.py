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

"""
from __future__ import absolute_import
from typing import Any, List, Type, Optional
from types import TracebackType
import atexit
import select
import socket
import struct
import threading

from .handler import AbstractHandler, logger, null_logger, AmsPacket, AmsResponseData, AmsHeader, AmsTcpHeader
from .basic_handler import BasicHandler
from .advanced_handler import AdvancedHandler

ADS_PORT = 0xBF02


class AdsTestServer(threading.Thread):
    """Simple ADS testing server.

    :ivar function handler: Request handler (see `default_handler` for example)
    :ivar str ip_address: Host address for server. Defaults to '127.0.0.1'
    :ivar int port: Host port to listen on, defaults to 48898

    """

    def __init__(
            self,
            handler: "AbstractHandler" = None,
            ip_address: str = "127.0.0.1",
            port: int = ADS_PORT,
            logging: bool = True,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        self.handler = handler or BasicHandler()
        self.ip_address = ip_address
        self.port = port
        self._run = True

        global logger
        logger = logger if logging else null_logger

        # Keep track of all received AMS packets
        self.request_history: List[AmsPacket] = []

        # Initialize TCP/IP socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set option to allow instant socket reuse after shutdown
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server.bind((self.ip_address, self.port))

        # Make sure we clean up on exit
        atexit.register(self.close)

        # Daemonize the server thread

        # Container for client connection threads
        self.clients: List[AdsClientConnection] = []

        super(AdsTestServer, self).__init__(*args, **kwargs)
        self.daemon = True

    def __enter__(self) -> "AdsTestServer":
        """Enter context."""
        self.start()
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        """Exit context."""
        self.close()

    def stop(self) -> None:
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

    def close(self) -> None:
        """Close the server thread."""
        self.stop()

    def run(self) -> None:
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

    def __init__(self, handler: "AbstractHandler", client: socket.socket, address: str, server: AdsTestServer,
                 *args: Any,
                 **kwargs: Any) -> None:
        self.handler = handler
        self.server = server
        self.client = client
        self.client_address = address

        # Make sure we clean up on exit
        atexit.register(self.close)

        # Server loop execution flag
        self._run = True

        super(AdsClientConnection, self).__init__(*args, **kwargs)

    def stop(self) -> None:
        """Stop the client thread."""
        if self._run:
            logger.info(
                "Closing client connection {0}:{1}.".format(
                    *self.client_address)
            )
            self._run = False

        self.join()

    def close(self) -> None:
        """Close the client connection."""
        if self.is_alive():
            self.stop()
        self.client.close()

    def run(self) -> None:
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

    @staticmethod
    def construct_response(response_data: AmsResponseData, request: AmsPacket) -> bytes:
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

    @staticmethod
    def construct_request(request_bytes: bytes) -> AmsPacket:
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
