"""PyQt GUI for simulating monitor and IO UART channels."""

from __future__ import annotations

import sys
from dataclasses import fields

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import ControlConfig
from .controller import RefrigerationController
from .uart import MockUART


class UARTTab(QWidget):
    def __init__(self, label: str, uart: MockUART) -> None:
        super().__init__()
        self.label = label
        self.uart = uart

        root_layout = QVBoxLayout(self)

        send_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText(f"Enter {label} command")
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        self.input_line.returnPressed.connect(self.send_message)

        send_layout.addWidget(self.input_line)
        send_layout.addWidget(send_button)

        root_layout.addLayout(send_layout)

        if label == "Monitor UART":
            root_layout.addWidget(QLabel("Configuration Quick Actions"))
            root_layout.addLayout(self._build_monitor_controls())
        elif label == "IO UART":
            root_layout.addWidget(QLabel("IO Quick Actions"))
            root_layout.addLayout(self._build_io_controls())

        tx_header_layout = QHBoxLayout()
        tx_header_layout.addWidget(QLabel("TX Output"))
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_output_log)
        tx_header_layout.addWidget(clear_button)
        tx_header_layout.addStretch()
        root_layout.addLayout(tx_header_layout)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        root_layout.addWidget(self.output_log)

    def _build_monitor_controls(self) -> QGridLayout:
        layout = QGridLayout()
        self.config_inputs: dict[str, QLineEdit] = {}

        for row, config_field in enumerate(fields(ControlConfig)):
            key = config_field.name
            layout.addWidget(QLabel(key), row, 0)

            value_input = QLineEdit(str(getattr(ControlConfig(), key)))
            self.config_inputs[key] = value_input
            layout.addWidget(value_input, row, 1)

            set_button = QPushButton(f"Set {key}")
            set_button.clicked.connect(lambda _, name=key: self._send_config_value(name))
            layout.addWidget(set_button, row, 2)

        get_config_button = QPushButton("Get Config")
        get_config_button.clicked.connect(lambda: self._inject_and_log("GET CONFIG"))
        layout.addWidget(get_config_button, len(self.config_inputs), 0)

        get_status_button = QPushButton("Get Status")
        get_status_button.clicked.connect(lambda: self._inject_and_log("GET STATUS"))
        layout.addWidget(get_status_button, len(self.config_inputs), 1)
        return layout

    def _build_io_controls(self) -> QGridLayout:
        layout = QGridLayout()

        temp_input = QLineEdit("8.0")
        layout.addWidget(QLabel("air_temp_c"), 0, 0)
        layout.addWidget(temp_input, 0, 1)
        temp_button = QPushButton("Set Sensor")
        temp_button.clicked.connect(
            lambda: self._inject_and_log(f"SET_SENSOR air_temp_c={temp_input.text().strip()}")
        )
        layout.addWidget(temp_button, 0, 2)

        door_open_button = QPushButton("Door Open")
        door_open_button.clicked.connect(lambda: self._inject_and_log("SET_INPUT door_open=1"))
        layout.addWidget(door_open_button, 1, 0)

        door_closed_button = QPushButton("Door Closed")
        door_closed_button.clicked.connect(lambda: self._inject_and_log("SET_INPUT door_open=0"))
        layout.addWidget(door_closed_button, 1, 1)

        power_on_button = QPushButton("Power OK")
        power_on_button.clicked.connect(lambda: self._inject_and_log("SET_INPUT power_ok=1"))
        layout.addWidget(power_on_button, 2, 0)

        power_off_button = QPushButton("Power Fail")
        power_off_button.clicked.connect(lambda: self._inject_and_log("SET_INPUT power_ok=0"))
        layout.addWidget(power_off_button, 2, 1)

        motion_detected_button = QPushButton("Motion Detected")
        motion_detected_button.clicked.connect(
            lambda: self._inject_and_log("SET_INPUT motion_detected=1")
        )
        layout.addWidget(motion_detected_button, 3, 0)

        motion_clear_button = QPushButton("Motion Clear")
        motion_clear_button.clicked.connect(
            lambda: self._inject_and_log("SET_INPUT motion_detected=0")
        )
        layout.addWidget(motion_clear_button, 3, 1)

        panic_press_button = QPushButton("Press Panic Button")
        panic_press_button.clicked.connect(
            lambda: self._inject_and_log("SET_INPUT panic_button_pressed=1")
        )
        layout.addWidget(panic_press_button, 4, 0)

        panic_reset_button = QPushButton("Reset Panic Button")
        panic_reset_button.clicked.connect(
            lambda: self._inject_and_log("SET_INPUT panic_button_pressed=0")
        )
        layout.addWidget(panic_reset_button, 4, 1)

        get_io_button = QPushButton("Get IO")
        get_io_button.clicked.connect(lambda: self._inject_and_log("GET IO"))
        layout.addWidget(get_io_button, 5, 0)

        return layout

    def _send_config_value(self, key: str) -> None:
        value = self.config_inputs[key].text().strip()
        self._inject_and_log(f"SET {key}={value}")

    def _inject_and_log(self, message: str) -> None:
        if not message:
            return
        self.uart.inject_rx(message)
        self.output_log.append(f"> RX: {message}")

    def send_message(self) -> None:
        message = self.input_line.text().strip()
        if not message:
            return

        self._inject_and_log(message)
        self.input_line.clear()

    def append_tx(self, lines: list[str]) -> None:
        for line in lines:
            self.output_log.append(f"< TX: {line}")

    def clear_output_log(self) -> None:
        self.output_log.clear()


class UARTWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Refrigeration UART Simulator")
        self.resize(900, 650)

        self.monitor_uart = MockUART()
        self.io_uart = MockUART()
        self.controller = RefrigerationController(self.monitor_uart, self.io_uart)

        tabs = QTabWidget()
        self.monitor_tab = UARTTab("Monitor UART", self.monitor_uart)
        self.io_tab = UARTTab("IO UART", self.io_uart)

        tabs.addTab(self.monitor_tab, "Monitor UART")
        tabs.addTab(self.io_tab, "IO UART")

        self.setCentralWidget(tabs)

        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.step_controller)
        self.timer.start()

    def step_controller(self) -> None:
        self.controller.step()
        self.monitor_tab.append_tx(self.monitor_uart.drain_tx())
        self.io_tab.append_tx(self.io_uart.drain_tx())


def run_gui() -> int:
    app = QApplication(sys.argv)
    window = UARTWindow()
    window.show()
    return app.exec()


def format_status(status_payload: dict) -> str:
    """Utility formatter used by future UI enhancements and tests."""
    parts: list[str] = []
    for key, value in status_payload.items():
        parts.append(f"{key}={value}")
    return ", ".join(parts)
