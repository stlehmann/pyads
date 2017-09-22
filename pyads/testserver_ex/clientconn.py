import threading
import atexit
import logging
import select


logger = logging.getLogger(__name__)


class AdsClientConnection(threading.Thread):

    def __init__(self, handler, client, address, server):
        self.handler = handler
        self.server = server
        self.client = client
        self.client_address = address

        atexit.register(self.close)

        self._run = True

        super(AdsClientConnection, self).__init__()
        self.daemon = True

    def stop(self):
        if self._run:
            self._run = False
            logger.info(
                'Closing client connection {0}:{1}.'
                .format(*self.client_address)
            )

    def close(self):
        if self.is_alive():
            self.stop()
        self.client.close()

    def run(self):
        while self._run:
            ready, _, _ = select.select([self.client], [], [], 0.1)

            if not ready:
                continue

            data, _ = self.client.recvfrom(4096)
            logger.info(data)

            if not data:
                self.close()
                continue
