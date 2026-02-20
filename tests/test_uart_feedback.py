import unittest

from refrigeration.controller import RefrigerationController
from refrigeration.uart import MockUART


class ProtocolFeedbackTests(unittest.TestCase):
    def test_monitor_ignores_echoed_error_lines(self) -> None:
        monitor = MockUART()
        io = MockUART()
        controller = RefrigerationController(monitor, io)

        monitor.inject_rx("ERR unknown_command:hhhh")
        controller.step()

        tx_lines = monitor.drain_tx()
        self.assertEqual(1, len(tx_lines))
        self.assertTrue(tx_lines[0].startswith("STATUS "))

    def test_io_ignores_echoed_ack_lines(self) -> None:
        monitor = MockUART()
        io = MockUART()
        controller = RefrigerationController(monitor, io)

        io.inject_rx("ACK door_open=1")
        controller.step()

        tx_lines = io.drain_tx()
        self.assertEqual([], tx_lines)


if __name__ == "__main__":
    unittest.main()
