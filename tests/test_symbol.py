"""Test AdsSymbol class.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2020-11-16

"""
import ctypes
from ctypes import addressof, memmove, resize, sizeof, pointer
import datetime
import time
import unittest
import pyads
import struct
from pyads.testserver import AdsTestServer, AmsPacket, AdvancedHandler
from pyads.structs import NotificationAttrib
from pyads import constants, structs, AdsSymbol
from collections import OrderedDict

# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class AdsSymbolTestCase(unittest.TestCase):
    """Testcase for ADS symbol class"""

    @classmethod
    def setUpClass(cls):
        # type: () -> None
        """Setup the ADS testserver."""
        cls.test_server = AdsTestServer(logging=True)
        cls.test_server.start()

        # wait a bit otherwise error might occur
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        # type: () -> None
        """Tear down the testserver."""
        cls.test_server.stop()

        # wait a bit for server to shutdown
        time.sleep(1)

    def setUp(self):
        # type: () -> None
        """Establish connection to the testserver."""
        self.test_server.request_history = []
        # self.test_server.handler.reset()
        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT,
            TEST_SERVER_IP_ADDRESS
        )

    def assert_command_id(self, request, target_id):
        # type: (AmsPacket, int) -> None
        """Assert command_id and target_id."""
        # Check the request code received by the server
        command_id = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id)[0]
        self.assertEqual(command_id, target_id)

    def test_init_name(self):
        handle_name = "TestHandle"

        with self.plc:

            self.plc.write(
                value="1", index_group=123, index_offset=0,
                plc_datatype=constants.PLCTYPE_STRING
            )

            value = self.plc.read_by_name(handle_name, constants.PLCTYPE_BYTE)
            print('Value:', value)

            symbol = AdsSymbol(self.plc, handle_name)
            print('Value:', symbol)


if __name__ == "__main__":
    unittest.main()
    if __name__ == "__main__":
        unittest.main()
