"""Core refrigeration controller skeleton independent of concrete UART hardware."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from .config import ControlConfig, WalkInDimensionsFt
from .sck import SCKCommand, SCKError, build_status_line, parse_hex_line
from .uart import UARTTransport


@dataclass
class IOState:
    air_temp_c: float = 8.0
    door_open: bool = False
    power_ok: bool = True
    motion_detected: bool = False
    panic_button_pressed: bool = False
    compressor_on: bool = False
    panic_alarm_on: bool = False


class RefrigerationController:
    def __init__(
        self,
        monitor_uart: UARTTransport,
        io_uart: UARTTransport,
        config: ControlConfig | None = None,
        dimensions: WalkInDimensionsFt | None = None,
    ) -> None:
        self.monitor_uart = monitor_uart
        self.io_uart = io_uart
        self.config = config or ControlConfig()
        self.dimensions = dimensions or WalkInDimensionsFt()
        self.io = IOState()
        self.last_compressor_off_s = time.time()
        self._last_published_status: str | None = None

    def step(self) -> None:
        self._process_monitor_uart()
        self._process_io_uart()
        self._run_control_logic()
        self._publish_status()

    def _process_monitor_uart(self) -> None:
        line = self.monitor_uart.read_line()
        if not line:
            return

        sck_frame = self._parse_sck_frame(line)
        if sck_frame is not None:
            if sck_frame.frame_type == "S":
                return
            self._handle_monitor_sck_command(sck_frame.command, sck_frame.payload, sck_frame.tid)
            return

        if self._is_protocol_response(line):
            return

        if line.startswith("SET ") and "=" in line:
            _, payload = line.split(" ", 1)
            key, raw_value = payload.split("=", 1)
            if hasattr(self.config, key):
                current = getattr(self.config, key)
                typed_value = type(current)(raw_value)
                setattr(self.config, key, typed_value)
                self.monitor_uart.write_line(f"ACK {key}={typed_value}")
            else:
                self.monitor_uart.write_line(f"ERR unknown_config:{key}")
            return

        if line == "GET CONFIG":
            self.monitor_uart.write_line(
                f"CONFIG {self._format_key_values(asdict(self.config))}"
            )
            return

        if line == "GET STATUS":
            self.monitor_uart.write_line(
                f"STATUS {self._format_key_values(self._status_payload())}"
            )
            return

        self.monitor_uart.write_line(f"ERR unknown_command:{line}")

    def _process_io_uart(self) -> None:
        line = self.io_uart.read_line()
        if not line:
            return

        sck_frame = self._parse_sck_frame(line)
        if sck_frame is not None:
            if sck_frame.frame_type == "S":
                return
            self._handle_io_sck_command(sck_frame.command, sck_frame.payload, sck_frame.tid)
            return

        if self._is_protocol_response(line):
            return

        if line.startswith("SET_SENSOR ") and "=" in line:
            _, payload = line.split(" ", 1)
            key, raw_value = payload.split("=", 1)
            if key == "air_temp_c":
                self.io.air_temp_c = float(raw_value)
                self.io_uart.write_line(f"ACK {key}={self.io.air_temp_c}")
            else:
                self.io_uart.write_line(f"ERR unknown_sensor:{key}")
            return

        if line.startswith("SET_INPUT ") and "=" in line:
            _, payload = line.split(" ", 1)
            key, raw_value = payload.split("=", 1)
            if key in {"door_open", "power_ok", "motion_detected", "panic_button_pressed"}:
                setattr(self.io, key, bool(int(raw_value)))
                self.io_uart.write_line(f"ACK {key}={int(getattr(self.io, key))}")
            else:
                self.io_uart.write_line(f"ERR unknown_input:{key}")
            return

        if line == "GET IO":
            self.io_uart.write_line(f"IO {self._format_key_values(asdict(self.io))}")
            return

        self.io_uart.write_line(f"ERR unknown_command:{line}")

    def _run_control_logic(self) -> None:
        now = time.time()

        self.io.panic_alarm_on = self.io.panic_button_pressed

        if not self.io.power_ok:
            self._set_compressor(False, now)
            return

        upper = self.config.target_temp_c + self.config.hysteresis_c
        lower = self.config.target_temp_c - self.config.hysteresis_c

        if self.io.air_temp_c >= upper:
            min_off_elapsed = (now - self.last_compressor_off_s) >= self.config.compressor_min_off_s
            if min_off_elapsed:
                self.io.compressor_on = True
        elif self.io.air_temp_c <= lower:
            self._set_compressor(False, now)

    def _set_compressor(self, state: bool, now_s: float) -> None:
        if not state and self.io.compressor_on:
            self.last_compressor_off_s = now_s
        self.io.compressor_on = state

    def _status_payload(self) -> dict:
        return {
            "dimensions_ft": asdict(self.dimensions),
            "volume_ft3": self.dimensions.volume_ft3,
            "config": asdict(self.config),
            "io": asdict(self.io),
        }

    def _publish_status(self) -> None:
        status_line = f"STATUS {self._format_key_values(self._status_payload())}"
        if status_line == self._last_published_status:
            return
        self.monitor_uart.write_line(status_line)
        self._last_published_status = status_line

    def _format_key_values(self, payload: dict) -> str:
        entries = self._flatten_payload(payload)
        return ", ".join(f"{key}={value}" for key, value in entries)

    def _flatten_payload(self, payload: dict, prefix: str = "") -> list[tuple[str, str]]:
        output: list[tuple[str, str]] = []
        for key, value in payload.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                output.extend(self._flatten_payload(value, full_key))
            else:
                output.append((full_key, self._format_value(value)))
        return output

    @staticmethod
    def _format_value(value: object) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    @staticmethod
    def _is_protocol_response(line: str) -> bool:
        return line.startswith(("ACK ", "ERR ", "STATUS ", "CONFIG ", "IO "))

    @staticmethod
    def _parse_sck_frame(line: str):
        try:
            return parse_hex_line(line)
        except SCKError:
            return None

    def _handle_monitor_sck_command(self, command: int, payload: bytes, tid: int) -> None:
        payload_text = payload.decode("utf-8", errors="ignore")

        if command == SCKCommand.MONITOR_SET_CONFIG and "=" in payload_text:
            key, raw_value = payload_text.split("=", 1)
            if hasattr(self.config, key):
                current = getattr(self.config, key)
                typed_value = type(current)(raw_value)
                setattr(self.config, key, typed_value)
                self.monitor_uart.write_line(
                    build_status_line(command, f"ACK {key}={typed_value}", tid=tid)
                )
            else:
                self.monitor_uart.write_line(
                    build_status_line(command, f"ERR unknown_config:{key}", tid=tid)
                )
            return

        if command == SCKCommand.MONITOR_GET_CONFIG:
            self.monitor_uart.write_line(
                build_status_line(
                    command,
                    f"CONFIG {self._format_key_values(asdict(self.config))}",
                    tid=tid,
                )
            )
            return

        if command == SCKCommand.MONITOR_GET_STATUS:
            self.monitor_uart.write_line(
                build_status_line(
                    command,
                    f"STATUS {self._format_key_values(self._status_payload())}",
                    tid=tid,
                )
            )
            return

        self.monitor_uart.write_line(
            build_status_line(command, f"ERR unknown_command:{payload_text or command}", tid=tid)
        )

    def _handle_io_sck_command(self, command: int, payload: bytes, tid: int) -> None:
        payload_text = payload.decode("utf-8", errors="ignore")

        if command == SCKCommand.IO_SET_SENSOR and "=" in payload_text:
            key, raw_value = payload_text.split("=", 1)
            if key == "air_temp_c":
                self.io.air_temp_c = float(raw_value)
                self.io_uart.write_line(
                    build_status_line(command, f"ACK {key}={self.io.air_temp_c}", tid=tid)
                )
            else:
                self.io_uart.write_line(
                    build_status_line(command, f"ERR unknown_sensor:{key}", tid=tid)
                )
            return

        if command == SCKCommand.IO_SET_INPUT and "=" in payload_text:
            key, raw_value = payload_text.split("=", 1)
            if key in {"door_open", "power_ok", "motion_detected", "panic_button_pressed"}:
                setattr(self.io, key, bool(int(raw_value)))
                self.io_uart.write_line(
                    build_status_line(command, f"ACK {key}={int(getattr(self.io, key))}", tid=tid)
                )
            else:
                self.io_uart.write_line(
                    build_status_line(command, f"ERR unknown_input:{key}", tid=tid)
                )
            return

        if command == SCKCommand.IO_GET_IO:
            self.io_uart.write_line(
                build_status_line(
                    command,
                    f"IO {self._format_key_values(asdict(self.io))}",
                    tid=tid,
                )
            )
            return

        self.io_uart.write_line(
            build_status_line(command, f"ERR unknown_command:{payload_text or command}", tid=tid)
        )
