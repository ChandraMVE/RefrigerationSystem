import unittest

from refrigeration.uart import MockUART


class PhysicalMediaTests(unittest.TestCase):
    def test_no_intercommunication_without_physical_media(self) -> None:
        monitor = MockUART()
        io = MockUART()

        monitor.write_line("PING")

        self.assertIsNone(io.read_line())

    def test_bidirectional_intercommunication_with_physical_media(self) -> None:
        monitor = MockUART()
        io = MockUART()
        monitor.connect_physical_peer(io)

        monitor.write_line("MONITOR->IO")
        io.write_line("IO->MONITOR")

        self.assertEqual("MONITOR->IO", io.read_line())
        self.assertEqual("IO->MONITOR", monitor.read_line())


if __name__ == "__main__":
    unittest.main()
