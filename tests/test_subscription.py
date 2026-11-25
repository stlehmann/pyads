"""Tests for decoded notification subscriptions (Connection.subscribe)."""
import ctypes
import gc
import struct
import time
import unittest
from datetime import timezone
from unittest import mock

import pyads
from pyads import constants
from pyads.subscription import resolve_notification_type
from pyads.testserver import AdsTestServer, AdvancedHandler, PLCVariable

TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class _Point(ctypes.Structure):
    _layout_ = "ms"
    _pack_ = 1
    _fields_ = [("x", ctypes.c_int16), ("y", ctypes.c_int16)]


class ResolverTestCase(unittest.TestCase):
    """Type resolution from symbol info (no server needed).

    Rows mirror symbol entries observed on a real TwinCAT PLC.
    """

    def assertResolves(self, symbol_type, data_type, size, expected_type, expected_size):
        plc_type, n = resolve_notification_type("X", symbol_type, data_type, size)
        self.assertIs(plc_type, expected_type)
        self.assertEqual(n, expected_size)

    def assertUnresolvable(self, symbol_type, data_type, size):
        with self.assertRaises(TypeError) as ctx:
            resolve_notification_type("GVL.x", symbol_type, data_type, size)
        self.assertIn("GVL.x", str(ctx.exception))
        self.assertIn("plc_datatype=", str(ctx.exception))

    def test_base_type(self):
        self.assertResolves("INT", constants.ADST_INT16, 2, constants.PLCTYPE_INT, 2)

    def test_bool(self):
        self.assertResolves("BOOL", constants.ADST_BIT, 1, constants.PLCTYPE_BOOL, 1)

    def test_enum_int16(self):
        self.assertResolves(
            "Tc3_BACnetRev14.E_BACnet_Priority", constants.ADST_INT16, 2,
            constants.PLCTYPE_INT, 2,
        )

    def test_enum_uint8(self):
        plc_type, n = resolve_notification_type(
            "X", "Tc3_BA2_Common.E_BA_PIDMode", constants.ADST_UINT8, 1
        )
        self.assertEqual(ctypes.sizeof(plc_type), 1)
        self.assertEqual(n, 1)

    def test_subrange(self):
        self.assertResolves("INT (2..100)", constants.ADST_INT16, 2, constants.PLCTYPE_INT, 2)

    def test_time_of_day(self):
        self.assertResolves("TIME_OF_DAY", constants.ADST_UINT32, 4, constants.PLCTYPE_UDINT, 4)

    def test_string_alias(self):
        self.assertResolves(
            "Tc3_XBA.T_BA_MedString", constants.ADST_STRING, 65, constants.PLCTYPE_STRING, 65
        )

    def test_sized_string(self):
        self.assertResolves("STRING(80)", constants.ADST_STRING, 81, constants.PLCTYPE_STRING, 81)

    def test_sized_wstring(self):
        self.assertResolves(
            "WSTRING(10)", constants.ADST_WSTRING, 22, constants.PLCTYPE_WSTRING, 22
        )

    def test_array_of_base_type(self):
        plc_type, n = resolve_notification_type(
            "X", "ARRAY [0..9] OF INT", constants.ADST_INT16, 20
        )
        self.assertTrue(issubclass(plc_type, ctypes.Array))
        self.assertIs(plc_type._type_, constants.PLCTYPE_INT)
        self.assertEqual(plc_type._length_, 10)
        self.assertEqual(n, 20)

    def test_alias_to_array_size_mismatch(self):
        self.assertUnresolvable("T_Arr", constants.ADST_INT16, 20)

    def test_array_size_mismatch(self):
        self.assertUnresolvable("ARRAY [0..2] OF INT", constants.ADST_INT16, 8)

    def test_array_of_strings(self):
        self.assertUnresolvable("ARRAY [0..11] OF STRING(80)", constants.ADST_STRING, 972)

    def test_multi_dimensional_array(self):
        self.assertUnresolvable("ARRAY [0..1,0..2] OF INT", constants.ADST_INT16, 12)

    def test_nested_array(self):
        self.assertUnresolvable("ARRAY [1..3] OF ARRAY [0..1] OF INT", constants.ADST_INT16, 12)

    def test_array_of_wstrings(self):
        self.assertUnresolvable("ARRAY [0..3] OF WSTRING(10)", constants.ADST_WSTRING, 88)

    def test_structure(self):
        self.assertUnresolvable("ST_HA_Bath", constants.ADST_BIGTYPE, 64)

    def test_string_without_size(self):
        self.assertUnresolvable("STRING(80)", constants.ADST_STRING, 0)



class _ServerTestCase(unittest.TestCase):
    """Shared AdvancedHandler test server setup."""

    @classmethod
    def setUpClass(cls):
        cls.handler = AdvancedHandler()
        cls.test_server = AdsTestServer(handler=cls.handler, logging=False)
        cls.test_server.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.test_server.stop()
        time.sleep(1)

    def setUp(self):
        self.test_server.request_history = []
        self.handler.reset()
        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT, TEST_SERVER_IP_ADDRESS
        )
        self.received = []

    def tearDown(self):
        self.plc.close()

    def add_var(self, name, value, ads_type, symbol_type):
        var = PLCVariable(name, value, ads_type=ads_type, symbol_type=symbol_type)
        self.handler.add_variable(var)
        return var

    def command_ids(self):
        return [
            struct.unpack("<H", r.ams_header.command_id)[0]
            for r in self.test_server.request_history
        ]

    def add_note_requests(self):
        return [
            r for r in self.test_server.request_history
            if struct.unpack("<H", r.ams_header.command_id)[0]
            == constants.ADSCOMMAND_ADDDEVICENOTE
        ]


class SubscribeTestCase(_ServerTestCase):
    """Connection.subscribe against the test server."""

    def test_base_type_by_name(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe("GVL.counter", self.received.append)
            self.plc.write_by_name("GVL.counter", 42, pyads.PLCTYPE_INT)
        self.assertEqual(len(self.received), 1)
        note = self.received[0]
        self.assertIsInstance(note, pyads.Notification)
        self.assertEqual(note.name, "GVL.counter")
        self.assertEqual(note.value, 42)
        self.assertEqual(note.handle, sub.notification_handle)
        self.assertEqual(note.timestamp.tzinfo, timezone.utc)
        self.assertIs(sub.plc_datatype, pyads.PLCTYPE_INT)

    def test_enum_resolves_to_int(self):
        self.add_var("GVL.mode", struct.pack("<h", 0), constants.ADST_INT16, "E_Mode")
        with self.plc:
            self.plc.subscribe("GVL.mode", self.received.append)
            self.plc.write_by_name("GVL.mode", 3, pyads.PLCTYPE_INT)
        self.assertEqual([n.value for n in self.received], [3])

    def test_sized_string(self):
        self.add_var("GVL.text", bytes(11), constants.ADST_STRING, "STRING(10)")
        with self.plc:
            sub = self.plc.subscribe("GVL.text", self.received.append)
            self.plc.write_by_name("GVL.text", "hello", pyads.PLCTYPE_STRING)
        self.assertEqual(sub.size, 11)
        self.assertEqual([n.value for n in self.received], ["hello"])

    def test_wstring_decoded_to_str(self):
        self.add_var("GVL.wtext", bytes(22), constants.ADST_WSTRING, "WSTRING(10)")
        with self.plc:
            self.plc.subscribe("GVL.wtext", self.received.append)
            self.plc.write_by_name("GVL.wtext", "Grüße", pyads.PLCTYPE_WSTRING)
        self.assertEqual([n.value for n in self.received], ["Grüße"])

    def test_array_of_base_type(self):
        self.add_var(
            "GVL.arr", bytes(6), constants.ADST_INT16, "ARRAY [0..2] OF INT"
        )
        with self.plc:
            self.plc.subscribe("GVL.arr", self.received.append)
            self.plc.write_by_name("GVL.arr", [1, 2, 3], pyads.PLCTYPE_INT * 3)
        self.assertEqual([n.value for n in self.received], [[1, 2, 3]])

    def test_structure_raises_before_registering(self):
        self.add_var("GVL.point", bytes(4), constants.ADST_BIGTYPE, "ST_Point")
        with self.plc:
            with self.assertRaises(TypeError):
                self.plc.subscribe("GVL.point", self.received.append)
        self.assertNotIn(constants.ADSCOMMAND_ADDDEVICENOTE, self.command_ids())
        self.assertEqual(self.plc._subscriptions, {})

    def test_structure_with_explicit_type(self):
        self.add_var("GVL.point", bytes(4), constants.ADST_BIGTYPE, "ST_Point")
        with self.plc:
            self.plc.subscribe("GVL.point", self.received.append, plc_datatype=_Point)
            self.plc.write_by_name(
                "GVL.point", bytes(_Point(3, -4)), ctypes.c_ubyte * 4
            )
        self.assertEqual(len(self.received), 1)
        self.assertEqual((self.received[0].value.x, self.received[0].value.y), (3, -4))

    def test_default_attr(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            self.plc.subscribe("GVL.counter", self.received.append)
        (request,) = self.add_note_requests()
        _ig, _io, length, mode, max_delay, cycle_time = struct.unpack(
            "<IIIIII", request.ams_header.data[:24]
        )
        self.assertEqual(length, 2)
        self.assertEqual(mode, constants.ADSTRANS_SERVERONCHA)
        self.assertEqual(max_delay, 0)
        self.assertEqual(cycle_time, 1_000_000)  # 100 ms in 100 ns ticks

    def test_explicit_attr_used_as_is(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        attr = pyads.NotificationAttrib(2, cycle_time=5)
        with self.plc:
            self.plc.subscribe("GVL.counter", self.received.append, attr=attr)
        (request,) = self.add_note_requests()
        cycle_time = struct.unpack("<I", request.ams_header.data[20:24])[0]
        self.assertEqual(cycle_time, 50_000)

    def test_callback_error_is_logged_once_and_isolated(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        calls = []

        def broken(note):
            calls.append(note.value)
            raise RuntimeError("boom")

        with self.plc:
            with self.assertLogs("pyads", level="DEBUG") as logs:
                self.plc.subscribe("GVL.counter", broken)
                self.plc.write_by_name("GVL.counter", 1, pyads.PLCTYPE_INT)
                self.plc.write_by_name("GVL.counter", 2, pyads.PLCTYPE_INT)
        self.assertEqual(calls, [1, 2])
        errors = [r for r in logs.records if r.levelname == "ERROR"]
        self.assertEqual(len(errors), 1)
        self.assertIn("GVL.counter", errors[0].getMessage())

    def test_unsubscribe(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe("GVL.counter", self.received.append)
            sub.unsubscribe()
            sub.unsubscribe()  # idempotent
            self.plc.write_by_name("GVL.counter", 7, pyads.PLCTYPE_INT)
        self.assertFalse(sub.active)
        self.assertEqual(self.received, [])
        self.assertEqual(
            self.command_ids().count(constants.ADSCOMMAND_DELDEVICENOTE), 1
        )

    def test_context_manager(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            with self.plc.subscribe("GVL.counter", self.received.append) as sub:
                self.assertTrue(sub.active)
            self.assertFalse(sub.active)
            self.assertEqual(self.plc._subscriptions, {})

    def test_subscribe_on_closed_connection(self):
        with self.assertRaises(ValueError):
            self.plc.subscribe("GVL.counter", self.received.append)

    def test_dropped_subscription_object_keeps_delivering(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            self.plc.subscribe("GVL.counter", self.received.append)
            gc.collect()
            self.plc.write_by_name("GVL.counter", 5, pyads.PLCTYPE_INT)
        self.assertEqual([n.value for n in self.received], [5])

    def test_explicit_type_with_attr_uses_attr_length(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe(
                "GVL.counter", self.received.append,
                plc_datatype=pyads.PLCTYPE_INT, attr=pyads.NotificationAttrib(2),
            )
        self.assertEqual(sub.size, 2)

    def test_explicit_string_type_asks_plc_for_size(self):
        self.add_var("GVL.text", bytes(11), constants.ADST_STRING, "STRING(10)")
        with self.plc:
            sub = self.plc.subscribe(
                "GVL.text", self.received.append, plc_datatype=pyads.PLCTYPE_STRING
            )
            self.plc.write_by_name("GVL.text", "abc", pyads.PLCTYPE_STRING)
        self.assertEqual(sub.size, 11)
        self.assertEqual([n.value for n in self.received], ["abc"])

    def test_array_payload_size_mismatch_is_reported(self):
        # the PLC sends 2 bytes, but 3 INTs (6 bytes) are expected
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            with self.assertLogs("pyads", level="ERROR") as logs:
                self.plc.subscribe(
                    "GVL.counter", self.received.append,
                    plc_datatype=pyads.PLCTYPE_INT * 3,
                )
                self.plc.write_by_name("GVL.counter", 1, pyads.PLCTYPE_INT)
        self.assertEqual(self.received, [])
        self.assertIn("does not match", "\n".join(logs.output))

    def test_notification_in_flight_after_deactivation_is_dropped(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe("GVL.counter", self.received.append)
            # simulate a notification arriving while unsubscribe() runs
            sub._active = False
            self.plc.write_by_name("GVL.counter", 9, pyads.PLCTYPE_INT)
            self.plc._remove_subscription(sub)
        self.assertEqual(self.received, [])

    def test_failed_registration_leaves_no_subscription(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            with mock.patch.object(
                self.plc, "add_device_notification", side_effect=pyads.ADSError(1808)
            ):
                with self.assertRaises(pyads.ADSError):
                    self.plc.subscribe("GVL.counter", self.received.append)
            self.assertEqual(self.plc._subscriptions, {})

    def test_registration_on_concurrently_closed_connection(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            with mock.patch.object(
                self.plc, "add_device_notification", return_value=None
            ):
                with self.assertRaises(ValueError):
                    self.plc.subscribe("GVL.counter", self.received.append)
            self.assertEqual(self.plc._subscriptions, {})

    def test_repr(self):
        self.add_var("GVL.counter", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe("GVL.counter", self.received.append)
            self.assertEqual(
                repr(sub),
                f"<Subscription 'GVL.counter' handle={sub.notification_handle} active>",
            )
            sub.unsubscribe()
            self.assertTrue(repr(sub).endswith("inactive>"))



class CloseTestCase(_ServerTestCase):
    """Connection.close tears down subscriptions."""

    def test_close_removes_all_subscriptions(self):
        self.add_var("GVL.a", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        self.add_var("GVL.b", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        self.plc.open()
        sub_a = self.plc.subscribe("GVL.a", self.received.append)
        sub_b = self.plc.subscribe("GVL.b", self.received.append)
        self.plc.close()
        self.assertFalse(sub_a.active)
        self.assertFalse(sub_b.active)
        self.assertEqual(self.plc._subscriptions, {})
        self.assertEqual(
            self.command_ids().count(constants.ADSCOMMAND_DELDEVICENOTE), 2
        )
        sub_a.unsubscribe()  # no-op after close
        self.assertEqual(
            self.command_ids().count(constants.ADSCOMMAND_DELDEVICENOTE), 2
        )

    def test_close_logs_failed_unsubscribe_and_continues(self):
        self.add_var("GVL.a", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        self.add_var("GVL.b", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        self.plc.open()
        sub_a = self.plc.subscribe("GVL.a", self.received.append)
        sub_b = self.plc.subscribe("GVL.b", self.received.append)
        real_unsubscribe = pyads.Subscription.unsubscribe

        def unsubscribe_then_fail(sub):
            # really remove the notification: closing the port with a live
            # one crashes AdsLib
            real_unsubscribe(sub)
            if sub is sub_a:
                raise pyads.ADSError(1808)

        with mock.patch.object(pyads.Subscription, "unsubscribe", unsubscribe_then_fail):
            with self.assertLogs("pyads", level="WARNING") as logs:
                self.plc.close()
        self.assertIn("GVL.a", "\n".join(logs.output))
        self.assertFalse(sub_b.active)  # the failure did not stop the loop

    def test_with_block_exit_removes_subscriptions(self):
        self.add_var("GVL.a", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        with self.plc:
            sub = self.plc.subscribe("GVL.a", self.received.append)
        self.assertFalse(sub.active)

    def test_close_leaves_raw_notifications_alone(self):
        var = self.add_var("GVL.a", struct.pack("<h", 0), constants.ADST_INT16, "INT")
        self.plc.open()
        handles = self.plc.add_device_notification(
            (var.index_group, var.index_offset), pyads.NotificationAttrib(2),
            lambda *_: None,
        )
        self.plc.subscribe("GVL.a", self.received.append)
        # remove the raw one ourselves: closing a port with a live raw
        # notification crashes AdsLib (pre-existing, unrelated to subscribe)
        before = self.command_ids().count(constants.ADSCOMMAND_DELDEVICENOTE)
        self.plc.del_device_notification(*handles)
        self.plc.close()
        dels = self.command_ids().count(constants.ADSCOMMAND_DELDEVICENOTE) - before
        self.assertEqual(dels, 2)  # our explicit raw delete + the subscription


if __name__ == "__main__":
    unittest.main()
