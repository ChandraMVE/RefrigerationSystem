"""UART abstractions and in-memory mock transport for simulation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Protocol


class UARTTransport(Protocol):
    def read_line(self) -> str | None:
        ...

    def write_line(self, message: str) -> None:
        ...


@dataclass
class MockUART:
    rx_queue: Deque[str] = field(default_factory=deque)
    tx_queue: Deque[str] = field(default_factory=deque)

    def inject_rx(self, message: str) -> None:
        self.rx_queue.append(message.strip())

    def read_line(self) -> str | None:
        if not self.rx_queue:
            return None
        return self.rx_queue.popleft()

    def write_line(self, message: str) -> None:
        self.tx_queue.append(message.strip())

    def drain_tx(self) -> list[str]:
        output = list(self.tx_queue)
        self.tx_queue.clear()
        return output
