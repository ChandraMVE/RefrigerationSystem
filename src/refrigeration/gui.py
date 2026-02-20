"""PyQt GUI for simulating monitor and IO UART channels."""

from __future__ import annotations

import json
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
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

        root_layout.addWidget(QLabel("TX Output"))
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        root_layout.addWidget(self.output_log)

    def send_message(self) -> None:
        message = self.input_line.text().strip()
        if not message:
            return

        self.uart.inject_rx(message)
        self.output_log.append(f"> RX: {message}")
        self.input_line.clear()

    def append_tx(self, lines: list[str]) -> None:
        for line in lines:
            self.output_log.append(f"< TX: {line}")


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
    return json.dumps(status_payload, indent=2, sort_keys=True)
