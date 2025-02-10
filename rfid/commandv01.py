from enum import Enum
from rfid.utils import calculate_checksum


HEADER = 0xCF
BROADCAST_ADDRESS = 0xFF


class CommandOption(Enum):
    SET = 0x01
    GET = 0x02


class CommandRequest(Enum):
    SET_POWER = 0x0053
    GET_DEVICE_INFO = 0x0070
    INVENTORY_ISO_CONTINUE = 0x0001
    INVENTORY_STOP = 0x0002
    INVENTORY_ACTIVE = 0x0001


class Command(object):
    def __init__(self,
                 command: CommandRequest,
                 address=BROADCAST_ADDRESS,
                 data: bytes | bytearray = bytearray()) -> None:
        self.address = address
        self.command = command
        self.data = data

    def serialize(self, with_checksum: bool = True) -> bytes:
        base_data = bytearray(
            [HEADER, self.address]) + \
                    self.command.value.to_bytes(2, "big") + \
                    bytearray([len(self.data)]) + \
                    bytearray(self.data)
        if with_checksum:
            checksum = calculate_checksum(base_data)
            base_data.extend(checksum)
        return base_data
