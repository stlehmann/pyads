"""Test reconnecting a Connection after the device went away.

:license: MIT, see license file or https://opensource.org/licenses/MIT

"""
import ctypes
import time
import unittest

import pyads
from pyads import constants
from pyads.pyads_ex import callback_store
from pyads.testserver import AdsTestServer, AdvancedHandler, PLCVariable

TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1

# Short timeout so requests against the stopped server fail quickly
TIMEOUT_MS = 300


class ReconnectTestCase(unittest.TestCase):
    """Stop and restart the test server underneath an open connection."""

    def setUp(self) -> None:
        self.handler = AdvancedHandler()
        self.var = PLCVariable(
            "Main.counter", 0, constants.ADST_INT16, symbol_type="INT"
        )
        self.handler.add_variable(self.var)
        self.server = self._start_server()
        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID,
            TEST_SERVER_AMS_PORT,
            TEST_SERVER_IP_ADDRESS,
            timeout=TIMEOUT_MS,
        )
        self.plc.open()

    def tearDown(self) -> None:
        self.plc.close()
        self.server.stop()
        time.sleep(0.2)

    def _start_server(self) -> AdsTestServer:
        server = AdsTestServer(handler=self.handler, logging=False)
        server.start()
        time.sleep(0.2)
        return server

    def _drop_link(self) -> None:
        """Stop the server and wait until the connection notices."""
        # A request first makes sure the server has accepted the TCP
        # connection, otherwise a late accept() outlives stop()
        self.assertTrue(self.plc.check_connection())
        self.server.stop()
        time.sleep(0.2)
        self.assertFalse(self.plc.check_connection())

    def _restart_server(self) -> None:
        self.server = self._start_server()

    def _add_counter_notification(self, received):
        return self.plc.add_device_notification(
            (self.var.index_group, self.var.index_offset),
            pyads.NotificationAttrib(ctypes.sizeof(pyads.PLCTYPE_INT)),
            # The header is only valid during the callback
            lambda notification, data: received.append(
                notification.contents.hNotification
            ),
        )

    def test_check_connection(self) -> None:
        self.assertTrue(self.plc.check_connection())
        self._drop_link()
        self.plc.close()
        self.assertFalse(self.plc.check_connection())

    def test_port_stays_dead_without_reconnect(self) -> None:
        """Document the AdsLib behaviour that makes reconnect() necessary."""
        self._drop_link()
        self._restart_server()
        self.assertFalse(self.plc.check_connection())

    def test_reconnect_restores_notifications(self) -> None:
        received = []
        old_handles = self._add_counter_notification(received)

        self._drop_link()
        self._restart_server()
        remapped = self.plc.reconnect()

        self.assertTrue(self.plc.check_connection())
        self.assertEqual(list(remapped), [old_handles])
        self.assertEqual(self.plc.pending_notifications, [])
        new_handles = remapped[old_handles]
        self.assertNotIn((self.plc._adr, old_handles[0]), callback_store)

        self.plc.write_by_name("Main.counter", 42, pyads.PLCTYPE_INT)
        self.assertEqual(len(received), 1)
        self.assertEqual(received, [new_handles[0]])

        # The test server keeps the notifications of dead clients, a PLC
        # drops them when the TCP connection closes
        self.plc.del_device_notification(*new_handles)
        self.assertNotIn(new_handles[0], self.var.notifications)

    def test_reconnect_while_device_is_down(self) -> None:
        old_handles = self._add_counter_notification([])
        self._drop_link()

        with self.assertRaises(pyads.ADSError):
            self.plc.reconnect()
        self.assertEqual(self.plc.pending_notifications, [old_handles])

        self._restart_server()
        remapped = self.plc.reconnect()
        self.assertEqual(list(remapped), [old_handles])
        self.assertEqual(self.plc.pending_notifications, [])

    def test_failed_restore_stays_pending(self) -> None:
        old_handles = self._add_counter_notification([])
        self._drop_link()

        # The variable is gone after the restart, so subscribing fails
        self.handler.reset()
        self._restart_server()
        self.assertEqual(self.plc.reconnect(), {})
        self.assertEqual(self.plc.pending_notifications, [old_handles])

        self.handler.add_variable(self.var)
        remapped = self.plc.restore_notifications()
        self.assertEqual(list(remapped), [old_handles])
        self.assertEqual(self.plc.pending_notifications, [])

    def test_delete_pending_notification(self) -> None:
        old_handles = self._add_counter_notification([])
        self._drop_link()
        with self.assertRaises(pyads.ADSError):
            self.plc.reconnect()

        self.plc.del_device_notification(*old_handles)
        self.assertEqual(self.plc.pending_notifications, [])

        self._restart_server()
        self.assertEqual(self.plc.reconnect(), {})

    def test_close_forgets_notifications(self) -> None:
        self._add_counter_notification([])
        self.plc.close()
        self.plc.open()
        self.assertEqual(self.plc.reconnect(), {})

    def test_symbol_follows_new_handles(self) -> None:
        symbol = self.plc.get_symbol("Main.counter", auto_update=True)
        old_handles = symbol._auto_update_handle

        self._drop_link()
        self._restart_server()
        remapped = self.plc.reconnect()

        new_handles = remapped[old_handles]
        self.assertEqual(symbol._auto_update_handle, new_handles)
        self.plc.write_by_name("Main.counter", 7, pyads.PLCTYPE_INT)
        self.assertEqual(symbol.value, 7)

        symbol.auto_update = False
        self.assertNotIn(new_handles[0], self.var.notifications)

    def test_subscription_survives_reconnect(self) -> None:
        received = []
        sub = self.plc.subscribe("Main.counter", received.append)
        old_handle = sub.notification_handle

        self._drop_link()
        self._restart_server()
        remapped = self.plc.reconnect()

        (new_handles,) = remapped.values()
        self.assertEqual(sub.notification_handle, new_handles[0])
        self.assertNotEqual(sub.notification_handle, old_handle)
        self.assertEqual(self.plc._subscriptions, {new_handles[0]: sub})

        received.clear()
        self.plc.write_by_name("Main.counter", 5, pyads.PLCTYPE_INT)
        self.assertEqual([n.value for n in received], [5])

        sub.unsubscribe()
        self.assertEqual(self.plc._subscriptions, {})
        self.assertNotIn(new_handles[0], self.var.notifications)

    def test_unsubscribe_while_pending(self) -> None:
        """An unsubscribed subscription must not come back on restore."""
        sub = self.plc.subscribe("Main.counter", lambda n: None)
        self._drop_link()
        with self.assertRaises(pyads.ADSError):
            self.plc.reconnect()

        sub.unsubscribe()
        self.assertEqual(self.plc.pending_notifications, [])
        self._restart_server()
        self.assertEqual(self.plc.reconnect(), {})


if __name__ == "__main__":
    unittest.main()
