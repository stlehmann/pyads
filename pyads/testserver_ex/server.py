"""
Extended Testserver for pyads.

:author: Stefan Lehmann <stefan.st.lehmann@gmail.com
:license: MIT license, see license.txt for details

:created on 2017-09-29 10:34:28
:last modified by:   Stefan Lehmann
:last modified time: 2017-11-10 11:52:25

"""
import click
import logging
import threading
import socket
import select
import atexit
from .client import AdsClientConnection
from .handler import AdvancedHandler
from ..structs import AmsAddr


AMS_NET_ID = "127.0.0.1.1.1"
ADS_PORT = 48898


# init logger
logger = logging.getLogger("pyads.testserver_ex")
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
stdout_handler.setLevel(logging.DEBUG)
logger.addHandler(stdout_handler)
logger.setLevel(logging.INFO)


class Testserver(threading.Thread):
    def __init__(
        self,
        handler=None,
        ip_address="",
        ams_net_id=AMS_NET_ID,
        port=ADS_PORT,
        logging=True,
    ):

        self.handler = handler or AdvancedHandler()
        self.ip_address = ip_address
        self.ams_addr = AmsAddr(ams_net_id, port)
        self.port = port
        self._run = False
        self.clients = []
        self.request_history = []

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip_address, self.port))

        atexit.register(self.close)

        super(Testserver, self).__init__()
        self.daemon = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def stop(self):
        for client in self.clients:
            client.close()

        self.clients = []
        self.socket.close()

    def close(self):
        self.stop()

    def run(self):
        self._run = True
        self.socket.listen(5)

        logger.info(
            "Server listening on {0}:{1}".format(
                self.ip_address or "localhost", self.port
            )
        )

        while self._run:
            ready, _, _ = select.select([self.socket], [], [], 0.1)

            if ready:
                client, address = self.socket.accept()
                logger.info("New connection from {0}:{1}".format(*address))

                client_connection = AdsClientConnection(
                    self.handler, client, address, self
                )
                client_connection.start()
                self.clients.append(client_connection)


@click.command()
@click.argument("port", type=int)
@click.option(
    "--netid", help="Change the netid that the server uses.", default=AMS_NET_ID
)
def main(port, netid):
    testserver = Testserver(ams_net_id=netid, port=port)
    testserver.run()


if __name__ == "__main__":
    main()
