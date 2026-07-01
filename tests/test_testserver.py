"""Some extra tests for the test server.

Like 90% of the test server and handlers are used during pyads tests. After all, that
is largely why the test server exists. However, a few features are not covered by tests
(for example because they were not needed during a test from the pyads perspective).
Since the test server has become a user feature in itself, these tests supplement the
regular pyads tests to increase the coverage of the test server itself.
"""

import socket
import struct
import time
import unittest
import pyads
from pyads.testserver import AdsTestServer, AdvancedHandler, BasicHandler, PLCVariable

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
            del test_int  # Trigger destructor
        except pyads.ADSError as e:
            self.fail(f"Closing server connection raised: {e}")


    def test_handler_exception_returns_device_error_and_survives(self):
        """A command handler that raises must return an ADS device error, not
        crash the connection thread.

        Regression guard for the try/except added around the command dispatch in
        ``AdvancedHandler.handle_request``. Requesting a handle for an unknown
        symbol makes ``get_variable_by_name`` raise ``KeyError`` inside the
        handler; the server must answer with a device error and keep serving.
        """
        handler = AdvancedHandler()
        handler.add_variable(
            PLCVariable("Known", 0, pyads.constants.ADST_INT16, "INT")
        )
        test_server = AdsTestServer(handler=handler, logging=False)

        with test_server:
            time.sleep(0.1)  # Give server a moment to spin up
            plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)
            with plc:
                # Unknown symbol -> handler raises -> converted to ADS error.
                with self.assertRaises(pyads.ADSError):
                    plc.get_handle("DoesNotExist")

                # The connection thread survived: a valid request still works.
                self.assertIsNotNone(plc.get_handle("Known"))

        time.sleep(0.1)  # Give server a moment to spin down

    def test_sumup_write_reports_per_item_errors_and_keeps_good_writes(self):
        """A SUMUP_WRITE batch with one bad sub-request returns one error code
        per sub-request, and the sub-writes that already succeeded still land.

        Regression guard for the per-item handling in the SUMUP_WRITE branch of
        ``handle_read_write``. Previously any sub-write that raised bubbled to
        the dispatch catch-all and collapsed the whole batch to a single device
        error, discarding both the per-item result array that pyads' own
        ``adsSumWriteBytes`` parses and the writes that had already landed. This
        drives the handler directly: the client resolves handles first, so a
        per-item *write* failure is not reachable through ``pyads.Connection``.
        """
        from pyads.testserver.handler import AmsHeader, AmsTcpHeader, AmsPacket

        var = PLCVariable(
            "Known",
            bytes(2),
            ads_type=pyads.constants.ADST_INT16,
            symbol_type="INT",
            index_group=0x4020,
            index_offset=0x0001,
        )
        handler = AdvancedHandler()
        handler.add_variable(var)

        # Two sub-requests: the known variable, then an unknown index that makes
        # get_variable_by_indices raise.
        good = struct.pack("<III", var.index_group, var.index_offset, 2)
        bad = struct.pack("<III", 0xDEADBEEF, 0xDEADBEEF, 2)
        payload = struct.pack("<hh", 0x1234, 0x5678)
        write_data = good + bad + payload
        ams_data = (
            struct.pack("<I", pyads.constants.ADSIGRP_SUMUP_WRITE)
            + struct.pack("<I", 2)  # num_requests, coded in the index_offset
            + struct.pack("<I", 2 * 4)  # read_length: one error code per request
            + struct.pack("<I", len(write_data))
            + write_data
        )
        header = AmsHeader(
            target_net_id=b"\x01" * 6,
            target_port=struct.pack("<H", TEST_SERVER_AMS_PORT),
            source_net_id=b"\x02" * 6,
            source_port=struct.pack("<H", 40000),
            command_id=struct.pack("<H", pyads.constants.ADSCOMMAND_READWRITE),
            state_flags=struct.pack("<H", 0x0004),
            length=struct.pack("<I", len(ams_data)),
            error_code=struct.pack("<I", 0),
            invoke_id=struct.pack("<I", 1),
            data=ams_data,
        )
        packet = AmsPacket(tcp_header=AmsTcpHeader(length=0), ams_header=header)

        response = handler.handle_request(packet)

        # Response is result(4) + read_length(4) + one error code per request.
        codes = struct.unpack("<II", response.data[8:16])
        self.assertEqual(codes, (0, 0x0700))
        # The successful sub-write landed despite the sibling failure.
        self.assertEqual(struct.unpack("<h", var.value[:2])[0], 0x1234)

    def test_abrupt_client_disconnect_is_handled(self):
        """An abruptly reset client connection must not crash the server.

        Regression guard for the try/except around ``recvfrom`` in
        ``AdsClientConnection``. A raw socket connects and forces a TCP RST via
        ``SO_LINGER``, so the server's ``recvfrom`` raises
        ``ConnectionResetError``; the server must treat it as a disconnect and
        still accept the next client.
        """
        handler = AdvancedHandler()
        handler.add_variable(
            PLCVariable("Known", 0, pyads.constants.ADST_INT16, "INT")
        )
        test_server = AdsTestServer(handler=handler, logging=False)

        with test_server:
            time.sleep(0.1)  # Give server a moment to spin up

            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.connect((TEST_SERVER_IP_ADDRESS, 0xBF02))  # ADS TCP port 48898
            time.sleep(0.1)  # let the connection thread enter its recv loop
            # SO_LINGER with timeout 0 makes close() send a RST instead of FIN.
            raw.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
            raw.close()
            time.sleep(0.1)  # let the server observe the reset

            # Server still accepts and serves a fresh connection.
            plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)
            with plc:
                self.assertIsNotNone(plc.get_handle("Known"))

        time.sleep(0.1)  # Give server a moment to spin down


if __name__ == "__main__":
    unittest.main()
