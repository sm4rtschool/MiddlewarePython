from dataclasses import dataclass

from rfid.utils import hex_readable


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

