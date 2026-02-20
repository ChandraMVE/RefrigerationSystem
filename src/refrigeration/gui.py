"""PyQt GUI for simulating monitor and IO UART channels."""

from __future__ import annotations

import sys
from dataclasses import fields

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
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
    BAUD_RATES = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
    DATA_BITS = ["5", "6", "7", "8"]

    def __init__(self, label: str, uart: MockUART) -> None:
        super().__init__()
        self.label = label
        self.uart = uart

        root_layout = QVBoxLayout(self)

        inner_tabs = QTabWidget()
        inner_tabs.addTab(self._build_console_tab(), "Console")
        inner_tabs.addTab(self._build_config_tab(), "UART Configuration")
        root_layout.addWidget(inner_tabs)

    def _build_console_tab(self) -> QWidget:
        panel = QWidget()
        root_layout = QVBoxLayout(panel)

        send_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText(f"Enter {self.label} command")
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        self.input_line.returnPressed.connect(self.send_message)

        send_layout.addWidget(self.input_line)
        send_layout.addWidget(send_button)

        root_layout.addLayout(send_layout)

        if self.label == "Monitor UART":
            root_layout.addWidget(QLabel("Configuration Quick Actions"))
            root_layout.addLayout(self._build_monitor_controls())
        elif self.label == "IO UART":
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
        return panel

    def _build_config_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(self.BAUD_RATES)
        self.baud_combo.setCurrentText("115200")

        self.bits_combo = QComboBox()
        self.bits_combo.addItems(self.DATA_BITS)
        self.bits_combo.setCurrentText("8")

        refresh_button = QPushButton("Refresh Ports")
        refresh_button.clicked.connect(self.refresh_ports)

        self.open_button = QPushButton("OPEN")
        self.open_button.clicked.connect(self.open_port)

        self.close_button = QPushButton("CLOSE")
        self.close_button.clicked.connect(self.close_port)

        self.connection_status = QLabel("Port closed")

        layout.addWidget(QLabel("Port"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1)
        layout.addWidget(refresh_button, 0, 2)

        layout.addWidget(QLabel("Baudrate"), 1, 0)
        layout.addWidget(self.baud_combo, 1, 1)

        layout.addWidget(QLabel("Bits"), 2, 0)
        layout.addWidget(self.bits_combo, 2, 1)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.open_button)
        action_layout.addWidget(self.close_button)
        layout.addLayout(action_layout, 3, 1)

        layout.addWidget(QLabel("Status"), 4, 0)
        layout.addWidget(self.connection_status, 4, 1, 1, 2)

        self.refresh_ports()
        return panel

    def refresh_ports(self) -> None:
        current_port = self.port_combo.currentText().strip()
        ports = self.uart.list_serial_ports()

        self.port_combo.clear()
        self.port_combo.addItems(ports)

        if current_port:
            self.port_combo.setCurrentText(current_port)

        if not ports and not current_port:
            self.connection_status.setText("No UART ports found (or pyserial missing)")

    def open_port(self) -> None:
        port = self.port_combo.currentText().strip()
        if not port:
            self.connection_status.setText("Select a port before opening")
            return

        baudrate = int(self.baud_combo.currentText())
        bits = int(self.bits_combo.currentText())
        success, message = self.uart.open_serial(port, baudrate, bits)
        self.connection_status.setText(message)
        if success:
            self.output_log.append(f"* {message}")

    def close_port(self) -> None:
        _, message = self.uart.close_serial()
        self.connection_status.setText(message)
        self.output_log.append(f"* {message}")

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


class TemperatureGraphWidget(QWidget):
    def __init__(self, max_points: int = 120) -> None:
        super().__init__()
        self.max_points = max_points
        self._temperatures: list[float] = []
        self.setMinimumHeight(260)

    def add_temperature(self, value: float) -> None:
        self._temperatures.append(value)
        if len(self._temperatures) > self.max_points:
            self._temperatures.pop(0)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        chart_rect = QRectF(50, 20, max(self.width() - 70, 10), max(self.height() - 60, 10))
        painter.fillRect(chart_rect, QColor("#f7f9fc"))

        grid_pen = QPen(QColor("#e1e6ef"))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        horizontal_lines = 5
        for index in range(horizontal_lines + 1):
            y = chart_rect.top() + (index / horizontal_lines) * chart_rect.height()
            painter.drawLine(
                int(chart_rect.left()),
                int(y),
                int(chart_rect.right()),
                int(y),
            )

        axis_pen = QPen(QColor("#596275"))
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)
        painter.drawRect(chart_rect)

        if len(self._temperatures) < 2:
            painter.setPen(QColor("#596275"))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Waiting for temperature data")
            return

        minimum = min(self._temperatures)
        maximum = max(self._temperatures)
        if minimum == maximum:
            minimum -= 1.0
            maximum += 1.0

        series_pen = QPen(QColor("#2d98da"))
        series_pen.setWidth(2)
        painter.setPen(series_pen)

        points: list[QPointF] = []
        x_step = chart_rect.width() / (len(self._temperatures) - 1)
        for index, value in enumerate(self._temperatures):
            x = chart_rect.left() + (index * x_step)
            normalized = (value - minimum) / (maximum - minimum)
            y = chart_rect.bottom() - (normalized * chart_rect.height())
            points.append(QPointF(x, y))

        for start, end in zip(points[:-1], points[1:]):
            painter.drawLine(start, end)

        painter.setPen(QColor("#2d3436"))
        painter.drawText(8, int(chart_rect.top() + 5), f"{maximum:.1f}°C")
        painter.drawText(8, int(chart_rect.bottom()), f"{minimum:.1f}°C")


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
        self.temperature_tab = self._build_temperature_tab()

        tabs.addTab(self.monitor_tab, "Monitor UART")
        tabs.addTab(self.io_tab, "IO UART")
        tabs.addTab(self.temperature_tab, "Room Temperature")

        self.setCentralWidget(tabs)

        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.step_controller)
        self.timer.start()

    def _build_temperature_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.temperature_reading_label = QLabel("Current Room Temperature: -- °C")
        layout.addWidget(self.temperature_reading_label)

        self.temperature_graph = TemperatureGraphWidget()
        layout.addWidget(self.temperature_graph)

        helper_text = QLabel(
            "This trend graph reflects IO sensor updates (air_temp_c). "
            "PID controls will be added in a future phase."
        )
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        return panel

    def step_controller(self) -> None:
        self.controller.step()
        self.monitor_tab.append_tx(self.monitor_uart.drain_tx())
        self.io_tab.append_tx(self.io_uart.drain_tx())
        current_temperature = self.controller.io.air_temp_c
        self.temperature_reading_label.setText(
            f"Current Room Temperature: {current_temperature:.2f} °C"
        )
        self.temperature_graph.add_temperature(current_temperature)


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
