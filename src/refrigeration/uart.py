"""UART abstractions for simulation and optional real serial transport."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Protocol

try:
    import serial
    from serial import SerialException
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - optional dependency
    serial = None
    SerialException = Exception
    list_ports = None


class UARTTransport(Protocol):
    def read_line(self) -> str | None:
        ...

    def write_line(self, message: str) -> None:
        ...


@dataclass
class MockUART:
    """Mock UART with optional forwarding to a live serial port.

    The existing simulator behavior is preserved through in-memory RX/TX queues.
    When a serial port is open, TX lines are mirrored to the port and RX lines are
    polled from the port as well.
    """

    rx_queue: Deque[str] = field(default_factory=deque)
    tx_queue: Deque[str] = field(default_factory=deque)
    _tx_echo_queue: Deque[str] = field(default_factory=deque, init=False, repr=False)
    _serial_port: object | None = field(default=None, init=False, repr=False)

    @property
    def serial_connected(self) -> bool:
        return self._serial_port is not None

    def inject_rx(self, message: str) -> None:
        self.rx_queue.append(message.strip())

    def read_line(self) -> str | None:
        if self._serial_port is not None:
            try:
                payload: bytes = self._serial_port.readline()
            except SerialException:
                self.close_serial()
            else:
                decoded = payload.decode("utf-8", errors="ignore").strip()
                if decoded:
                    if self._tx_echo_queue and decoded == self._tx_echo_queue[0]:
                        self._tx_echo_queue.popleft()
                    else:
                        return decoded

        while self._tx_echo_queue and self._tx_echo_queue[0] == "":
            self._tx_echo_queue.popleft()

        if not self.rx_queue:
            return None
        return self.rx_queue.popleft()

    def write_line(self, message: str) -> None:
        payload = message.strip()
        self.tx_queue.append(payload)

        if self._serial_port is not None:
            try:
                self._serial_port.write(f"{payload}\n".encode("utf-8"))
                self._tx_echo_queue.append(payload)
            except SerialException:
                self.close_serial()

    def drain_tx(self) -> list[str]:
        output = list(self.tx_queue)
        self.tx_queue.clear()
        return output

    def open_serial(self, port: str, baudrate: int, bits: int) -> tuple[bool, str]:
        if serial is None:
            return False, "pyserial is not installed"

        byte_size_lookup = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS,
        }

        if bits not in byte_size_lookup:
            return False, f"Unsupported bits setting: {bits}"

        self.close_serial()
        try:
            self._serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=byte_size_lookup[bits],
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0,
                write_timeout=0,
            )
        except (SerialException, ValueError) as exc:
            self._serial_port = None
            return False, str(exc)

        return True, f"Connected to {port} @ {baudrate} {bits}N1"

    def close_serial(self) -> tuple[bool, str]:
        if self._serial_port is None:
            return True, "Port already closed"

        try:
            self._serial_port.close()
        except SerialException as exc:
            self._serial_port = None
            return False, str(exc)

        self._serial_port = None
        self._tx_echo_queue.clear()
        return True, "Port closed"

    @staticmethod
    def list_serial_ports() -> list[str]:
        if list_ports is None:
            return []
        return [item.device for item in list_ports.comports()]
