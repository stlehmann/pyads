import socket
import struct
import threading
import unittest
from contextlib import closing

from pyads.constants import PORT_REMOTE_UDP
from pyads.pyads_ex import adsGetNetIdForPLC


class PLCAMSTestCase(unittest.TestCase):

    PLC_IP = "127.0.0.1"
    PLC_AMS_ID = "11.22.33.44.1.1"

    def plc_ams_request_receiver(self):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.bind(("", PORT_REMOTE_UDP))

            # Keep looping until we get an add address packet
            addr = [0]
            while addr[0] != self.PLC_IP:
                data, addr = sock.recvfrom(1024)

            # Build response
            response = struct.pack(
                ">12s", b"\x03\x66\x14\x71\x00\x00\x00\x00\x01\x00\x00\x80"
            )  # Same header as being sent to the PLC, but with 80 at the end
            response += struct.pack(
                ">6B", *map(int, self.PLC_AMS_ID.split("."))
            )  # PLC AMS id
            # Don't care about the rest, so just fill the remaining bytes with garbage
            response += struct.pack(">377s", b"\x00" * 377)

            # Send our response back to sender
            sock.sendto(response, addr)

    def test_get_ams(self):
        # Start receiving listener
        route_thread = threading.Thread(target=self.plc_ams_request_receiver)
        route_thread.setDaemon(True)
        route_thread.start()

        # Confirm that the AMS net id is properly fetched from PLC
        self.assertEqual(adsGetNetIdForPLC(self.PLC_IP), self.PLC_AMS_ID)


if __name__ == "__main__":
    unittest.main()
