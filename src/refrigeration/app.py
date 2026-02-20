"""Application bootstrap for local simulation."""

from __future__ import annotations

import time

from .controller import RefrigerationController
from .uart import MockUART


class SimulationApp:
    def __init__(self) -> None:
        self.monitor_uart = MockUART()
        self.io_uart = MockUART()
        self.controller = RefrigerationController(self.monitor_uart, self.io_uart)

    def demo(self, steps: int = 3, delay_s: float = 0.1) -> None:
        self.monitor_uart.inject_rx("GET CONFIG")
        self.io_uart.inject_rx("SET_SENSOR air_temp_c=7.5")

        for _ in range(steps):
            self.controller.step()
            time.sleep(delay_s)

        print("--- MONITOR UART TX ---")
        for line in self.monitor_uart.drain_tx():
            print(line)

        print("--- IO UART TX ---")
        for line in self.io_uart.drain_tx():
            print(line)
