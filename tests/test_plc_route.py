import time
import unittest
import threading
import socket
import struct
from contextlib import closing
from pyads import add_route_to_plc
from pyads.constants import PORT_REMOTE_UDP
from pyads.utils import platform_is_linux


class PLCRouteTestCase(unittest.TestCase):

    SENDER_AMS = "1.2.3.4.1.1"
    PLC_IP = "127.0.0.1"
    USERNAME = "user"
    PASSWORD = "password"
    ROUTE_NAME = "Route"
    ADDING_AMS_ID = "5.6.7.8.1.1"
    HOSTNAME = "Host"
    PLC_AMS_ID = "11.22.33.44.1.1"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def plc_route_receiver(self):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.bind(("", PORT_REMOTE_UDP))

            # Keep looping until we get an add address packet
            addr = [0]
            while addr[0] != self.PLC_IP:
                data, addr = sock.recvfrom(1024)

            # Decipher data and 'add route'
            data = data[12:]  # Remove our data header

            sending_ams_bytes = data[:6]  # Sending AMS address
            sending_ams = ".".join(map(str, struct.unpack(">6B", sending_ams_bytes)))
            data = data[6:]

            comm_port = struct.unpack("<H", data[:2])[
                0
            ]  # Internal communication port (PORT_SYSTEMSERVICE)
            data = data[2:]

            command_code = struct.unpack("<H", data[:2])[
                0
            ]  # Comand code to write to PLC
            data = data[2:]

            data = data[4:]  # Remove protocol bytes

            len_route_name = struct.unpack("<H", data[:2])[0]  # Length of route name
            data = data[2:]

            route_name = data[:len_route_name].decode(
                "utf-8"
            )  # Null terminated username
            data = data[len_route_name:]

            data = data[2:]  # Remove protocol bytes

            len_ams_id = struct.unpack("<H", data[:2])[0]  # Length of adding AMS ID
            data = data[2:]

            adding_ams_id_bytes = data[:len_ams_id]  # AMS ID being added to PLC
            adding_ams_id = ".".join(
                map(str, struct.unpack(">6B", adding_ams_id_bytes))
            )
            data = data[len_ams_id:]

            data = data[2:]  # Remove protocol bytes

            len_username = struct.unpack("<H", data[:2])[0]  # Length of PLC username
            data = data[2:]

            username = data[:len_username].decode("utf-8")  # Null terminated username
            data = data[len_username:]

            data = data[2:]  # Remove protocol bytes

            len_password = struct.unpack("<H", data[:2])[0]  # Length of PLC password
            data = data[2:]

            password = data[:len_password].decode("utf-8")  # Null terminated username
            data = data[len_password:]

            data = data[2:]  # Remove protocol bytes

            len_sending_host = struct.unpack("<H", data[:2])[0]  # Length of host name
            data = data[2:]

            hostname = data[:len_sending_host].decode(
                "utf-8"
            )  # Null terminated hostname
            data = data[len_sending_host:]

            self.assertEqual(len(data), 0)  # We should have popped everything from data
            self.assertEqual(sending_ams, self.SENDER_AMS)
            self.assertEqual(comm_port, 10000)
            self.assertEqual(command_code, 5)
            self.assertEqual(
                len_sending_host, len(self.HOSTNAME) + 1
            )  # +1 for the null terminator
            self.assertEqual(hostname, self.HOSTNAME + "\0")
            self.assertEqual(adding_ams_id, self.ADDING_AMS_ID)
            self.assertEqual(
                len_username, len(self.USERNAME) + 1
            )  # +1 for the null terminator
            self.assertEqual(username, self.USERNAME + "\0")

            # Don't check the password since that's part the correct/incorrect response test
            # We can also assume that if the data after the password is correct, then the password was sent/read correctly
            # self.assertEqual(len_password, len(self.PASSWORD) + 1)				# +1 for the null terminator
            # self.assertEqual(password, self.PASSWORD + '\0')

            self.assertEqual(
                len_route_name, len(self.ROUTE_NAME) + 1
            )  # +1 for the null terminator
            self.assertEqual(route_name, self.ROUTE_NAME + "\0")

            if password == self.PASSWORD + "\0":
                password_correct = True
            else:
                password_correct = False

            # Build response
            response = struct.pack(
                ">12s", b"\x03\x66\x14\x71\x00\x00\x00\x00\x06\x00\x00\x80"
            )  # Same header as being sent to the PLC, but with 80 at the end
            response += struct.pack(
                ">6B", *map(int, self.PLC_AMS_ID.split("."))
            )  # PLC AMS id
            response += struct.pack(
                "<H", 10000
            )  # Internal communication port (PORT_SYSTEMSERVICE)
            response += struct.pack(">2s", b"\x01\x00")  # Command code read
            response += struct.pack(
                ">4s", b"\x00\x00\x01\x04"
            )  # Block of unknown protocol
            if password_correct:
                response += struct.pack(">3s", b"\x04\x00\x00")  # Password Correct
            else:
                response += struct.pack(">3s", b"\x00\x04\x07")  # Password Incorrect
            response += struct.pack(">2s", b"\x00\x00")  # Block of unknown protocol

            # Send our response back to sender
            sock.sendto(response, addr)

    def test_correct_route(self):
        if platform_is_linux():
            # Start receiving listener
            route_thread = threading.Thread(target=self.plc_route_receiver)
            route_thread.setDaemon(True)
            route_thread.start()

            time.sleep(1)

            # Try to set up a route with ourselves using all the optionals
            try:
                result = add_route_to_plc(
                    self.SENDER_AMS,
                    self.HOSTNAME,
                    self.PLC_IP,
                    self.USERNAME,
                    self.PASSWORD,
                    route_name=self.ROUTE_NAME,
                    added_net_id=self.ADDING_AMS_ID,
                )
            except:
                result = None

            self.assertTrue(result)

    def test_incorrect_route(self):
        if platform_is_linux():
            # Start receiving listener
            route_thread = threading.Thread(target=self.plc_route_receiver)
            route_thread.setDaemon(True)
            route_thread.start()

            # Try to set up a route with ourselves using all the optionals AND an incorrect password
            try:
                result = add_route_to_plc(
                    self.SENDER_AMS,
                    self.HOSTNAME,
                    self.PLC_IP,
                    self.USERNAME,
                    "Incorrect Password",
                    route_name=self.ROUTE_NAME,
                    added_net_id=self.ADDING_AMS_ID,
                )
            except:
                result = None

            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
