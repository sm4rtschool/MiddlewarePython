from logging import getLogger

from PySide6.QtCore import QThread, Signal as pyqtSignal

from threading import Thread

# from rfid.reader import Reader
# from rfid.reader_settings import OutputControl
# from util_log import log_traceback

from rfid.reader import ReaderRC4, StopType
from rfid.reader_settings import OutputControl
from util_log import log_traceback

logger = getLogger()


class SetManualRelayThread(QThread):

    result_set_manual_relay_signal = pyqtSignal(object)

    def __init__(self, reader: ReaderRC4) -> None:
        super().__init__()
        self.reader = reader
        self.__release: bool | None = None
        self.__valid_time: int | None = None
        print("Debug: SetManualRelayThread initialized.")

    @property
    def release(self) -> None:
        raise ValueError("No getter for release")

    @release.setter
    def release(self, release: bool) -> None:
        self.__release = release
        print(f"Debug: Release set to {release}.")

    @property
    def valid_time(self) -> None:
        raise ValueError("No getter for valid_time")

    @valid_time.setter
    def valid_time(self, valid_time: int) -> None:
        self.__valid_time = valid_time
        print(f"Debug: Valid time set to {valid_time}.")

    def run(self) -> None:
        try:
            print(f"Debug: Running SetManualRelayThread with release={self.__release} and valid_time={self.__valid_time}.")
            if self.__release is None or self.__valid_time is None:
                raise ValueError("Release and valid_time must be set before running the thread.")
            response = self.reader.set_relay(self.__release, self.__valid_time)
            logger.info("Ridwan : SetManualRelayThread() > run() > response: {response}")
            self.result_set_manual_relay_signal.emit(response)
        except Exception as e:
            logger.error(f"Error in SetManualRelayThread: {e}")
            self.result_set_manual_relay_signal.emit(e)


# class GetOutputControlThread(Thread):
#     def __init__(self, reader: ReaderRC4) -> None:
#         super().__init__()
#         self.reader = reader

#     def run(self) -> None:
#         try:
#             response = self.reader.get_output_control()
#             logger.info(f"GetOutputControlThread() > run() > response: {response}")
#             # Emit signal logic here (ganti dengan cara yang sesuai di Tkinter)
#         except Exception as e:
#             log_traceback(logger, e)
#             # Emit error logic here (ganti dengan cara yang sesuai di Tkinter)

class GetOutputControlThread(QThread):
    result_get_output_control_signal = pyqtSignal(object)

    def __init__(self, reader: ReaderRC4) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_output_control()
            logger.info(f"GetOutputControlThread() > run() > response: {response}")
            self.result_get_output_control_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_get_output_control_signal.emit(e)

# class SetAutoRelayThread(Thread):
#     def __init__(self, reader: ReaderRC4) -> None:
#         super().__init__()
#         self.reader = reader
#         self.__output_control: OutputControl | None = None

#     @property
#     def output_control(self) -> None:
#         raise ValueError("No getter for output_control")

#     @output_control.setter
#     def output_control(self, output_control: OutputControl) -> None:
#         self.__output_control = output_control

#     def run(self) -> None:
#         try:
#             response = self.reader.set_output_control(self.__output_control)
#             logger.info(f"SetAutoRelayThread() > run() > response: {response}")
#             self.result_set_output_control_signal.emit(response)
#         except Exception as e:
#             log_traceback(logger, e)
#             # Emit error logic here (ganti dengan cara yang sesuai di Tkinter)

class SetAutoRelayThread(QThread):
    result_set_auto_relay_signal = pyqtSignal(object)

    def __init__(self, reader: ReaderRC4) -> None:
        super().__init__()
        self.reader = reader
        self.__output_control: OutputControl | None = None
        logger.debug("SetAutoRelayThread initialized with reader: %s", reader)

    @property
    def output_control(self) -> None:
        raise ValueError("No getter for output_control")

    @output_control.setter
    def output_control(self, output_control: OutputControl) -> None:
        logger.debug("Setting output_control: %s", output_control)
        self.__output_control = output_control

    def run(self) -> None:
        logger.debug("Running SetAutoRelayThread...")
        try:
            logger.debug("Attempting to set output control...")
            response = self.reader.set_output_control(self.__output_control)
            logger.info(f"SetAutoRelayThread() > run() > response: {response}")
            self.result_set_auto_relay_signal.emit(response)
            logger.debug("Output control set successfully.")
        except Exception as e:
            logger.error("Error occurred in SetAutoRelayThread: %s", e)
            log_traceback(logger, e)
            self.result_set_auto_relay_signal.emit(e)
            logger.debug("Emitted error signal.")