from enum import Enum
from typing import Iterator

from rfid.command import CommandRequest, Command
# from rfid.response import Response, InventoryStatus, Tag
from rfid.response import *
from rfid.transport import TransportRC4
from rfid.utils import hex_readable

from rfid.reader_settings import AnswerModeInventoryParameter, WorkMode, MemoryBank, LockMemoryBank, LockAction, \
    StopAfter

class StopType(Enum):
    """\
    TIME: int = According to the time (in seconds)

    NUMBER: int = According to the number or cycles
    """
    TIME = 0x00
    NUMBER = 0x01


class ReaderRC4:
    def __init__(self, transport: TransportRC4) -> None:
        super().__init__()
        self.transport = transport
        self.transport.connect()

    def close(self) -> None:
        self.transport.close()

    def __receive_response(self) -> bytes | None:
        # Get header section
        response_header_section: bytes = self.transport.read_bytes(length=5)
        if not response_header_section:
            return

        assert len(response_header_section) == 5

        # Get body section
        body_length: int = response_header_section[-1]
        response_body_section: bytes = self.transport.read_bytes(length=body_length + 2)  # 2(checksum)

        return response_header_section + response_body_section


    def set_power(self, power: int) -> Response:
        cmd_request: CommandRequest = CommandRequest.SET_POWER
        command: Command = Command(cmd_request, data=bytearray([power, 0x00]))

        # Send request
        self.transport.write_bytes(command.serialize())

        # Receive response
        raw_response: bytes | None = self.__receive_response()
        if raw_response is None:
            raise RuntimeError("No response from reader.")
        response: Response = Response(raw_response)

        # Validation response
        assert response.command == cmd_request

        return response
    
    def set_relay(self, release: bool, valid_time: int = 1) -> Response:
        """
        :param release: If `True` release/open the relay
        :param valid_time: The effective time when closing
        """
        assert type(release) is bool
        assert 0x00 <= valid_time <= 0xFF, f"Invalid valid_time: {valid_time}. Must be between 0x00 and 0xFF."

        print(f"Debug: Setting relay - release: {release}, valid_time: {valid_time}")

        release_value = 0x01
        if not release:  # Close
            release_value = 0x02
            print("Debug: Relay will be closed.")

        cmd_request = CommandRequest.RELEASE_CLOSE_RELAY
        command = Command(cmd_request, data=bytearray([release_value, valid_time]))
        print(f"Debug: Command to send: {command.serialize()}")

        self.transport.write_bytes(command.serialize())
        
        # Debug: Log the command sent
        print(f"Debug: Command sent to transport: {command.serialize()}")

        raw_response = self.__receive_response()
        if raw_response is None:
            print("Debug: No response received from the reader.")
            raise RuntimeError("No response from reader.")
        
        response = Response(raw_response)
        print(f"Debug: Received response: {response}")

        # Debug: Log the response details
        print(f"Debug: Response details - Command: {response.command}, Status: {response.status}")

        return response

    def start_inventory_answer_mode(self, stop_type: StopType, value: int) -> Iterator[Tag]:
        cmd_request: CommandRequest = CommandRequest.INVENTORY_ISO_CONTINUE
        data = bytearray([stop_type.value])
        data.extend(value.to_bytes(4, "big"))
        command = Command(cmd_request, data=data)

        # Send request
        self.transport.write_bytes(command.serialize())

        while True:
            raw_response: bytes | None = self.__receive_response()
            if raw_response is None:
                return
            response: Response = Response(raw_response)

            if response.command == CommandRequest.INVENTORY_STOP or not response.payload:
                print("Inventory finished!")
                break

            tag: Tag = Tag(
                rssi=response.payload[0:2],
                antenna=response.payload[2],
                channel=response.payload[3],
                data=response.payload[5:])
            yield tag

    def stop_inventory_answer_mode(self) -> Response:
        cmd_request: CommandRequest = CommandRequest.INVENTORY_STOP
        command: Command = Command(cmd_request)

        # Send request
        self.transport.write_bytes(command.serialize())

        # Receive response
        response: Response = Response(self.__receive_response())

        # Validation response
        assert response.command == cmd_request

        return response
    
    def set_output_control(self, output_control: OutputControl) -> Response:
        logger.info(f"Reader() > set_output_control()")

        cmd_request = CommandRequest.SET_GET_OUTPUT_PARAMETERS
        data = bytearray([CommandOption.SET.value])
        data.extend(output_control.to_command_data())
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_output_control(self) -> ResponseOutputControl:
        logger.info(f"Reader() > get_output_control()")

        cmd_request = CommandRequest.SET_GET_OUTPUT_PARAMETERS
        data = bytearray([CommandOption.GET.value])
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return ResponseOutputControl(self.__receive_response(cmd_request))