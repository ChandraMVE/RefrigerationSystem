import unittest

from refrigeration.controller import RefrigerationController
from refrigeration.sck import SCKCommand, build_command_line, parse_hex_line
from refrigeration.uart import MockUART


class SCKInterfaceTests(unittest.TestCase):
    def test_monitor_set_config_via_sck(self) -> None:
        monitor = MockUART()
        io = MockUART()
        controller = RefrigerationController(monitor, io)

        monitor.inject_rx(build_command_line(SCKCommand.MONITOR_SET_CONFIG, "target_temp_c=3.5", tid=7))
        controller.step()

        tx_lines = monitor.drain_tx()
        ack_frame = parse_hex_line(tx_lines[0])
        assert ack_frame is not None
        self.assertEqual("S", ack_frame.frame_type)
        self.assertEqual(7, ack_frame.tid)
        self.assertEqual(SCKCommand.MONITOR_SET_CONFIG, ack_frame.command)
        self.assertIn("ACK target_temp_c=3.5", ack_frame.payload.decode("utf-8"))
        self.assertAlmostEqual(3.5, controller.config.target_temp_c)

    def test_io_quick_action_style_command_via_sck(self) -> None:
        monitor = MockUART()
        io = MockUART()
        controller = RefrigerationController(monitor, io)

        io.inject_rx(build_command_line(SCKCommand.IO_SET_INPUT, "door_open=1", tid=9))
        controller.step()

        tx_lines = io.drain_tx()
        ack_frame = parse_hex_line(tx_lines[0])
        assert ack_frame is not None
        self.assertEqual("S", ack_frame.frame_type)
        self.assertEqual(9, ack_frame.tid)
        self.assertIn("ACK door_open=1", ack_frame.payload.decode("utf-8"))
        self.assertTrue(controller.io.door_open)


if __name__ == "__main__":
    unittest.main()
