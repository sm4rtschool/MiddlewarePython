from array import array


def hex_readable(data_bytes: bytes | array, separator: str = " ") -> str:
    return separator.join("{:02X}".format(x) for x in data_bytes)

def ip_string(ip_bytes: bytes) -> str:
    assert len(ip_bytes) == 4
    return ".".join("{:d}".format(x) for x in ip_bytes)

def ip_bytes(ip_str: str) -> bytearray:
    ip_str_split = ip_str.split('.')
    assert len(ip_str_split) == 4

    return bytearray([int(ip) for ip in ip_str_split])


def calculate_checksum(data: bytes) -> bytearray:
    value = 0xFFFF
    for d in data:
        value ^= d
        for _ in range(8):
            value = (value >> 1) ^ 0x8408 if value & 0x0001 else (value >> 1)
    crc_msb = value >> 0x08
    crc_lsb = value & 0xFF
    return bytearray([crc_msb, crc_lsb])


def calculate_rssi(rssi: bytes) -> int:
    return int.from_bytes(rssi, "big", signed=True)
