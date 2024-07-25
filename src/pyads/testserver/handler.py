"""Abstract handler module for testserver.

:author: David Browne <davidabrowne@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2016-09-13

"""
import logging
from collections import namedtuple


# Log to stdout by default
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(levelname)s:%(message)s")
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.WARN)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)
logger.setLevel(logging.WARN)
logger.propagate = False  # "Overwrite" default handler

null_logger = logging.getLogger(__name__ + "_null")
null_logger.addHandler(logging.NullHandler())

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


class AbstractHandler:
    """Abstract Handler class to provide a base class for handling requests."""

    def handle_request(self, request: AmsPacket) -> AmsResponseData:
        """Handle incoming requests.

        :param AmsPacket request: The request data received from the client
        :rtype: AmsResponseData
        :return: Data needed to construct the AMS response packet

        """
        raise not NotImplementedError()  # type: ignore
