"""Some extra tests for the test server.

Like 90% of the test server and handlers are used during pyads tests. After all, that
is largely why the test server exists. However, a few features are not covered by tests
(for example because they were not needed during a test from the pyads perspective).
Since the test server has become a user feature in itself, these tests supplement the
regular pyads tests to increase the coverage of the test server itself.
"""

import time
import unittest
import pyads
from pyads.testserver import AdsTestServer, BasicHandler

# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class TestServerTestCase(unittest.TestCase):
    """Some rudimentary tests for the test server.

    The majority of test server code is tested as part of regular pyads tests. This
    case is only for a few items that were left uncovered.
    """

    def test_start_stop(self):
        handler = BasicHandler()
        test_server = AdsTestServer(handler=handler, logging=False)
        test_server.start()
        time.sleep(0.1)  # Give server a moment to spin up
        test_server.stop()
        time.sleep(0.1)  # Give server a moment to spin up

    def test_context(self):
        handler = BasicHandler()
        test_server = AdsTestServer(handler=handler, logging=False)

        with test_server:

            time.sleep(0.1)  # Give server a moment to spin up

            plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)
            with plc:
                byte = plc.read(12345, 1000, pyads.PLCTYPE_BYTE)
                self.assertEqual(byte, 0)

        time.sleep(0.1)  # Give server a moment to spin down

    def test_server_disconnect_then_del_device_notification(self):
        """Test no error thown, when ADS symbol with device_notification is cleaned up after the server went offline.

        Tests fix of issue [#303](https://github.com/stlehmann/pyads/issues/303), original pull request: [#304](https://github.com/stlehmann/pyads/pull/304)
        """
        # 1. spin up the server
        handler = BasicHandler()
        test_server = AdsTestServer(handler=handler, logging=False)
        test_server.start()
        time.sleep(0.1)  # Give server a moment to spin up

        # 2. open a plc connection to the test server:
        plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)
        plc.open()

        # 3. add a variable, register a device notification with auto_update=True
        test_int = pyads.AdsSymbol(plc, "TestSymbol", symbol_type=pyads.PLCTYPE_INT)
        test_int.plc_type = pyads.PLCTYPE_INT
        test_int.auto_update = True
        time.sleep(0.1)  # Give server a moment

        raised_error: str = ""

        # 4. stop the test server
        test_server.stop()
        time.sleep(0.1)  # Give server a moment

        try:
            # some code, where test_int is cleared by the Garbage collector after the server was stopped
            # (e.g. the machine with ADS Server disconnected)
            # this raised an ADSError up to commit [a7af674](https://github.com/stlehmann/pyads/tree/a7af674b49b1c91966f2bac1f00f86273cbd9af8)
            #  `clear_device_notifications()` failed, if not wrapped in try-catch as the server is no longer present.
            test_int.__del__()
        except pyads.ADSError as e:
            self.fail(f"Closing server connection raised: {e}")


if __name__ == "__main__":
    unittest.main()
