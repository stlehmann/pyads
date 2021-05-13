""" ADS TCP/IP testserver implementation.

ADS TCP/IP testserver implementation to allow for functional testing of
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
from .testserver import AdsTestServer
from .basic_handler import BasicHandler
from .advanced_handler import AdvancedHandler, PLCVariable
from .handler import AmsTcpHeader, AmsHeader, AmsPacket, AmsResponseData
