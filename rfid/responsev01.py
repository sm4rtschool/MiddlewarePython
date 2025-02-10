from dataclasses import dataclass
from enum import Enum

from rfid.command import HEADER, CommandRequest
from rfid.utils import calculate_checksum, hex_readable


class Status(Enum):
    SUCCESS = 0x00
    WRONG_PARAM = 0x01
    CMD_EXECUTION_FAILED = 0x02
    RESERVE = 0x03
    NO_COUNT_LABEL = 0x12
    TIMEOUT = 0x14
    TAG_RESPONSE_ERROR = 0x15
    AUTHENTICATION_FAILED = 0x16
    WRONG_PASSWORD = 0x17
    NO_MORE_DATA = 0xFF


class TagStatus(Enum):
    NO_ERROR = 0xFF
    TIMEOUT = 0x14
    OTHER_ERROR = 0x81
    STORAGE_AREA_ERROR = 0x82
    STORAGE_LOCK = 0x83
    INSUFFICIENT_POWER = 0x84
    NO_POWER = 0x85


class InventoryStatus(Enum):
    SUCCESS = 0x00
    WRONG_PARAM = 0x01
    CMD_EXECUTION_FAILED = 0x02
    NO_COUNT_LABEL = 0x12
    EXCEED_MAX_TRANSMIT_SERIAL = 0x17


@dataclass
class Tag:
    rssi: bytes
    antenna: int
    channel: int
    data: bytes
    count: int = 1

    def __str__(self) -> str:
        return f'Tag(rssi: {hex_readable(self.rssi)}, ' \
               f'antenna: {self.antenna}, channel: {self.channel}, ' \
               f'data: {hex_readable(self.data)})'


class Response:
    def __init__(self, response: bytes) -> None:
        if response is None:
            raise ValueError("Response is None")

        header_section: bytes = response[0:5]
        assert header_section[0] == HEADER
        self.header: int = response[0]
        self.address: int = response[1]
        self.command: CommandRequest = CommandRequest(int.from_bytes(response[2:4], "big"))
        self.length: int = response[4]
        self.status: Status = Status(response[5])

        __body_n_checksum_section: bytes = response[6: 4 + self.length + 2 + 1]
        self.payload: bytes = __body_n_checksum_section[0:-2]
        self.checksum: bytes = __body_n_checksum_section[-2:]

        # Verify checksum
        data = bytearray(header_section)
        data.extend(bytearray([self.status.value]))
        if self.payload:
            data.extend(self.payload)
        crc_msb, crc_lsb = calculate_checksum(data)
        assert self.checksum[0] == crc_msb and self.checksum[1] == crc_lsb
