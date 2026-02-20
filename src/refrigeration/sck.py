"""SCK UART command framing helpers."""

from __future__ import annotations

from dataclasses import dataclass

STX = 0x02
ETX = 0x03
FRAME_PREFIX = "SCK"
DEFAULT_VERSION = 0x0420


class SCKError(ValueError):
    """Raised when an SCK frame is malformed."""


@dataclass(frozen=True)
class SCKFrame:
    version: int
    tid: int
    frame_type: str
    command: int
    payload: bytes


class SCKCommand:
    MONITOR_SET_CONFIG = 0x0001
    MONITOR_GET_CONFIG = 0x0002
    MONITOR_GET_STATUS = 0x0003
    IO_SET_SENSOR = 0x0101
    IO_SET_INPUT = 0x0102
    IO_GET_IO = 0x0103


def crc16_ibm(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def encode_frame(frame: SCKFrame) -> bytes:
    if frame.frame_type not in {"C", "S"}:
        raise SCKError(f"Unsupported frame type: {frame.frame_type}")

    if not 0 <= frame.version <= 0xFFFF:
        raise SCKError("Version must fit in 2 bytes")
    if not 0 <= frame.tid <= 0xFF:
        raise SCKError("TID must fit in 1 byte")
    if not 0 <= frame.command <= 0xFFFF:
        raise SCKError("Command must fit in 2 bytes")

    length = 3 + len(frame.payload)
    if not 1 <= length <= 1023:
        raise SCKError("Length must be in range 1..1023")

    packet = bytearray()
    packet.append(STX)
    packet.extend(frame.version.to_bytes(2, "little"))
    packet.extend(length.to_bytes(2, "little"))
    packet.append(frame.tid)
    packet.append(ord(frame.frame_type))
    packet.extend(frame.command.to_bytes(2, "little"))
    packet.extend(frame.payload)

    crc_input = packet[3:5] + packet[6:]
    packet.extend(crc16_ibm(crc_input).to_bytes(2, "little"))
    packet.append(ETX)
    return bytes(packet)


def decode_frame(packet: bytes) -> SCKFrame:
    if len(packet) < 11:
        raise SCKError("Frame too short")
    if packet[0] != STX:
        raise SCKError("Missing STX")
    if packet[-1] != ETX:
        raise SCKError("Missing ETX")

    version = int.from_bytes(packet[1:3], "little")
    length = int.from_bytes(packet[3:5], "little")
    tid = packet[5]
    frame_type = chr(packet[6])
    command = int.from_bytes(packet[7:9], "little")

    payload_length = length - 3
    if payload_length < 0:
        raise SCKError("Invalid LENGTH")

    payload_end = 9 + payload_length
    crc_end = payload_end + 2
    if crc_end + 1 != len(packet):
        raise SCKError("Frame length mismatch")

    payload = packet[9:payload_end]
    crc_actual = int.from_bytes(packet[payload_end:crc_end], "little")

    crc_input = packet[3:5] + packet[6:payload_end]
    crc_expected = crc16_ibm(crc_input)
    if crc_actual != crc_expected:
        raise SCKError("CRC mismatch")

    if frame_type not in {"C", "S"}:
        raise SCKError("Invalid frame type")

    return SCKFrame(
        version=version,
        tid=tid,
        frame_type=frame_type,
        command=command,
        payload=payload,
    )


def format_hex_line(packet: bytes) -> str:
    payload = " ".join(f"{byte:02X}" for byte in packet)
    return f"{FRAME_PREFIX} {payload}"


def parse_hex_line(line: str) -> SCKFrame | None:
    normalized = line.strip()
    if not normalized.startswith(f"{FRAME_PREFIX} "):
        return None

    raw = normalized[len(FRAME_PREFIX) + 1 :].strip()
    if not raw:
        raise SCKError("Missing SCK payload")

    tokens = raw.split()
    try:
        packet = bytes(int(token, 16) for token in tokens)
    except ValueError as exc:  # pragma: no cover - defensive parsing
        raise SCKError("Invalid hex payload") from exc
    return decode_frame(packet)


def build_command_line(
    command: int,
    payload_text: str = "",
    *,
    tid: int = 1,
    version: int = DEFAULT_VERSION,
) -> str:
    frame = SCKFrame(
        version=version,
        tid=tid,
        frame_type="C",
        command=command,
        payload=payload_text.encode("utf-8"),
    )
    return format_hex_line(encode_frame(frame))


def build_status_line(
    command: int,
    payload_text: str = "",
    *,
    tid: int = 1,
    version: int = DEFAULT_VERSION,
) -> str:
    frame = SCKFrame(
        version=version,
        tid=tid,
        frame_type="S",
        command=command,
        payload=payload_text.encode("utf-8"),
    )
    return format_hex_line(encode_frame(frame))
