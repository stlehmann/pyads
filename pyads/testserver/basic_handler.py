"""Basic handler module for testserver.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2017-09-15

"""
from typing import List, Union
import struct

from .handler import AbstractHandler, AmsPacket, AmsResponseData, logger
from pyads import constants


class BasicHandler(AbstractHandler):
    """Basic request handler.

    Basic request handler to print the request data and return some default values.

    """

    def handle_request(self, request: AmsPacket) -> AmsResponseData:
        """Handle incoming requests and send a response."""
        # Extract command id from the request
        command_id_bytes = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id_bytes)[0]

        # Set AMS state correctly for response
        state = struct.unpack("<H", request.ams_header.state_flags)[0]
        state = state | 0x0001  # Set response flag
        state = struct.pack("<H", state)

        # Handle request
        if command_id == constants.ADSCOMMAND_READDEVICEINFO:
            logger.info("Command received: READ_DEVICE_INFO")

            # Create dummy response: version 1.2.3, device name 'TestServer'
            major_version = "\x01".encode("utf-8")
            minor_version = "\x02".encode("utf-8")
            version_build = "\x03\x00".encode("utf-8")
            device_name = "TestServer\x00".encode("utf-8")

            response_content = (
                    major_version + minor_version + version_build + device_name
            )

        elif command_id == constants.ADSCOMMAND_READ:
            logger.info("Command received: READ")
            # Parse requested data length
            response_length = \
                struct.unpack("<I", request.ams_header.data[8:12])[0]
            # Create response of repeated 0x0F with a null terminator for strings
            response_value = (
                    ("\x0F" * (response_length - 1)) + "\x00").encode(
                "utf-8")
            response_content = struct.pack("<I", len(
                response_value)) + response_value

        elif command_id == constants.ADSCOMMAND_WRITE:
            logger.info("Command received: WRITE")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_READSTATE:
            logger.info("Command received: READ_STATE")
            ads_state = struct.pack("<H", constants.ADSSTATE_RUN)
            # I don't know what an appropriate value for device state is.
            # I suspect it may be unused..
            device_state = struct.pack("<H", 0)

            response_content = ads_state + device_state

        elif command_id == constants.ADSCOMMAND_WRITECTRL:
            logger.info("Command received: WRITE_CONTROL")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_ADDDEVICENOTE:
            logger.info("Command received: ADD_DEVICE_NOTIFICATION")
            handle = ("\x0F" * 4).encode("utf-8")
            response_content = handle

        elif command_id == constants.ADSCOMMAND_DELDEVICENOTE:
            logger.info("Command received: DELETE_DEVICE_NOTIFICATION")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_DEVICENOTE:
            logger.info("Command received: DEVICE_NOTIFICATION")
            # No response data required
            response_content = "".encode("utf-8")

        elif command_id == constants.ADSCOMMAND_READWRITE:
            logger.info("Command received: READ_WRITE")
            # parse the request
            index_group = struct.unpack("<I", request.ams_header.data[:4])[0]
            response_length = \
                struct.unpack("<I", request.ams_header.data[8:12])[0]
            write_length = struct.unpack("<I", request.ams_header.data[12:16])[
                0]
            write_data = request.ams_header.data[16: (16 + write_length)]

            if index_group == constants.ADSIGRP_SYM_INFOBYNAMEEX:
                # Pack the structure in the same format as SAdsSymbolEntry.
                # Only 'EntrySize' (first field) and Type will be filled.
                # Use fixed UINT8 type
                if "str_" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 5, constants.ADST_STRING, 0, 0,
                        0, 0
                    )
                # Non-existent type
                elif "no_type" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 5, 1, 0, 0, 0, 0
                    )
                # Array
                elif "ar_" in write_data.decode():
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 2, constants.ADST_UINT8, 0, 0,
                        0, 0
                    )
                else:
                    logger.info("Packing ADST_UINT8...")
                    response_value = struct.pack(
                        "<IIIIIIHHH", 30, 0, 0, 1, constants.ADST_UINT8, 0, 0,
                        0, 0
                    )

            elif index_group == constants.ADSIGRP_SUMUP_READ:
                n_reads = len(write_data) // 12
                fmt = "<" + n_reads * "I"
                vals: List[Union[int, bytes]] = [0 for _ in range(n_reads)]

                for i in range(n_reads):
                    buf = write_data[i * 12 + 8:i * 12 + 12]
                    is_str = struct.unpack("<I", buf)[0] == 5

                    if is_str:
                        fmt += "5s"
                        vals.append(b"test\x00")
                    else:
                        fmt += "B"
                        vals.append(i + 1)
                response_value = struct.pack(fmt, *vals)

            elif index_group == constants.ADSIGRP_SUMUP_WRITE:
                n_writes = len(write_data) // 12
                fmt = "<" + n_writes * "I"
                vals = n_writes * [0]
                response_value = struct.pack(fmt, *vals)

            elif response_length > 0:
                # Create response of repeated 0x0F with a null terminator for strings
                response_value = (
                        ("\x0F" * (response_length - 1)) + "\x00").encode(
                    "utf-8"
                )
            else:
                response_value = b""

            response_content = struct.pack("<I", len(
                response_value)) + response_value

        else:
            logger.info("Unknown Command: {0}".format(hex(command_id)))
            # Set error code to 'unknown command ID'
            error_code = "\x08\x00\x00\x00".encode("utf-8")
            return AmsResponseData(state, error_code, "".encode("utf-8"))

        # Set no error in response
        error_code = ("\x00" * 4).encode("utf-8")
        response_data = error_code + response_content

        return AmsResponseData(state, request.ams_header.error_code,
                               response_data)
