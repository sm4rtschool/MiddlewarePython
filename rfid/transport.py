import glob
import sys
from enum import Enum
from abc import ABC, abstractmethod
from socket import socket, AF_INET, SOCK_STREAM
from typing import TypeVar

import serial

from rfid.utils import hex_readable

# logger = getLogger()
T = TypeVar('T', bound='Parent')


class BaudRate(Enum):
    BPS_9600 = 0x00
    BPS_19200 = 0x01
    BPS_38400 = 0x02
    BPS_57600 = 0x03
    BPS_115200 = 0x04

    _ignore_ = ["INT"]
    INT = []

    def __str__(self) -> str:
        return f'{self.to_int} bps'

    @property
    def to_int(self) -> int:
        return self.INT[self.value]

    @classmethod
    def from_int(cls, value: int) -> T:
        for baud_rate in BaudRate:
            if baud_rate.to_int == value:
                return baud_rate


BaudRate.INT = [9600, 19200, 38400, 57600, 115200]


class ConnectionType(Enum):
    SERIAL = 0
    USB = 1
    TCP_IP = 2

    def __str__(self) -> str:
        return ConnectionType.DISPLAY_STRINGS[self.value]

    @classmethod
    def from_str(cls, value: str) -> T:
        for connection_type in ConnectionType:
            if str(connection_type) == value:
                return connection_type


ConnectionType.DISPLAY_STRINGS = [
    "Serial",
    "USB",
    "TCP/IP"
]

class TransportRC4(ABC):
    @abstractmethod
    def connect(self, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def reconnect(self, **kwargs) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, **kwargs) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def write_bytes(self, buffer: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_buffer(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class TcpTransportRC4(TransportRC4):
    def __init__(self, ip_address: str, port: int, timeout: int = 6) -> None:
        self.ip_address: str = ip_address
        self.port: int = port
        self.timeout: int = timeout
        self.socket: socket | None = None

    def __str__(self) -> str:
        return f'TcpTransportRC4(ip_address: {self.ip_address}, port: {self.port}, timeout: {self.timeout})'

    def connect(self) -> None:
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.ip_address, self.port))

    def reconnect(self, ip_address: str | None = None, port: int | None = None,
                  timeout: int | None = None) -> None:
        self.socket.close()
        self.ip_address = ip_address if ip_address else self.ip_address
        self.timeout = timeout if timeout else self.timeout
        self.connect()

    def read_bytes(self, length: int) -> bytes:
        return self.socket.recv(length)

    def write_bytes(self, buffer: bytes) -> None:
        self.socket.sendall(buffer)

    def clear_buffer(self) -> None:
        # self.socket.recv(1024)
        pass

    def close(self) -> None:
        self.socket.close()


class SerialTransport(TransportRC4):
    def __init__(self, serial_port: str, baud_rate: BaudRate, timeout: int = 0.5) -> None:
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial = serial.Serial(self.serial_port, self.baud_rate.to_int,
                                    timeout=timeout, write_timeout=timeout * 2)

    def __str__(self) -> str:
        return f'SerialTransport(port: {self.serial_port}, baud_rate: {self.baud_rate})'

    @classmethod
    def scan(cls, timeout: int = 1) -> list[str]:
        result: list[str] = []
        if sys.platform.startswith("win"):  # Windows
            ports = ["COM%s" % (i + 1) for i in range(15)]
        elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):  # Linux
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif sys.platform.startswith("darwin"):  # Mac OS
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")
        for port in ports:
            try:
                s = serial.Serial(port, timeout=timeout)
                s.close()
                result.append(port)
            except serial.SerialException as _:
                pass
        return result

    def connect(self, **kwargs):
        pass

    def reconnect(self, serial_port: str | None = None, baud_rate: BaudRate | None = None,
                  timeout: int | None = None) -> None:
        self.close()
        self.serial_port = serial_port if serial_port else self.serial.port
        self.baud_rate = baud_rate if baud_rate else BaudRate.from_int(self.serial.baudrate)
        self.timeout = timeout if timeout else self.serial.timeout
        self.serial = serial.Serial(self.serial_port, self.baud_rate.to_int,
                                    timeout=self.timeout, write_timeout=self.timeout * 2)

    def read_bytes(self, length: int) -> bytes:
        response = self.serial.read(length)
        return response

    def write_bytes(self, buffer: bytes) -> None:
        self.serial.write(buffer)

    def clear_buffer(self) -> None:
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def close(self) -> None:
        self.serial.close()
