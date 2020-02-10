import datetime
import threading
import atexit
import logging
import select
from .structs import (
    AmsPacket,
    AdsNotificationStream,
    AdsStampHeader,
    AdsNotificationSample,
    AmsHeader,
    AmsTcpHeader,
)
from .. import constants
from ..filetimes import dt_to_filetime


logger = logging.getLogger(__name__)


class AdsClientConnection(threading.Thread):
    def __init__(self, handler, client, address, server):
        self.handler = handler
        self.server = server
        self.client = client
        self.client_address = address
        self.pending_notifications = []
        self.ams_net_id = None
        self.ams_port = None

        atexit.register(self.close)

        self._run = True

        super(AdsClientConnection, self).__init__()
        self.daemon = True

    def stop(self):
        if self._run:
            self._run = False
            logger.info(
                "Closing client connection {0}:{1}.".format(*self.client_address)
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

            if not data:
                self.close()
                continue

            # construct AmsPacket object containing request data
            request_packet = AmsPacket.from_bytes(data)

            # add request packet to history
            self.server.request_history.append(request_packet)

            # save ams net id and port for later use
            if self.ams_net_id is None:
                self.ams_net_id = request_packet.ams_header.source_net_id
                self.ams_port = request_packet.ams_header.source_port

            # create a response packet using the defined handler
            response_packet = self.handler.handle_request(request_packet, self)

            # send response to client
            self.client.send(response_packet.to_bytes())

            for notification, length, handle in self.pending_notifications:
                packet = self.create_notification_packet(notification, length, handle)

                logger.info(packet)
                self.client.send(packet.to_bytes())

    def create_notification_packet(self, notification, length, handle):
        sample = AdsNotificationSample(
            handle=handle, sample_size=length, data=notification.value[:length]
        )

        stamp = AdsStampHeader(
            timestamp=dt_to_filetime(datetime.datetime.utcnow()), samples=[sample]
        )

        stream = AdsNotificationStream(stamps=[stamp])

        ams_header = AmsHeader(
            target_net_id=self.ams_net_id,
            target_port=self.ams_port,
            source_net_id=self.server.ams_addr._ams_addr.netId,
            source_port=self.server.port,
            command_id=constants.ADSCOMMAND_DEVICENOTE,
            state_flags=constants.ADSSTATEFLAG_REQRESP,
            data_length=stream.length,
            error_code=0,
            invoke_id=0,
        )

        return AmsPacket(
            amstcp_header=AmsTcpHeader(length=ams_header.length + stream.length),
            ams_header=ams_header,
            ads_data=stream.to_bytes(),
        )
