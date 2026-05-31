"""Pure packet builders and parsers for the iDotMatrix 32x32 BLE protocol.

This module intentionally contains no Bluetooth code. Every function returns
``bytes`` and can be tested without hardware.
"""

from __future__ import annotations

import math
import struct
import zlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .constants import (
    ACK_CHUNK_OK,
    ACK_UPLOAD_DONE,
    GIF_CHUNK_HEADER_SIZE,
    GIF_PAYLOAD_CHUNK_SIZE,
    TEXT_GLYPH_BYTES,
    TEXT_SEPARATOR_32,
    WIDTH,
)
from .exceptions import ProtocolError
from .types import (
    Color,
    GifTotalLengthMode,
    Pixel,
    TextBackgroundMode,
    TextColorMode,
    TextMode,
    YearByteMode,
)


def _u16le(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ProtocolError(f"u16 value out of range: {value}")
    return value.to_bytes(2, byteorder="little", signed=False)


def _u32le(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ProtocolError(f"u32 value out of range: {value}")
    return value.to_bytes(4, byteorder="little", signed=False)


def _byte(value: int, *, name: str = "value") -> int:
    if not isinstance(value, int) or not 0 <= value <= 255:
        raise ProtocolError(f"{name} must be an integer in 0..255")
    return value


def build_screen_on() -> bytes:
    return bytes.fromhex("05 00 07 01 01")


def build_screen_off() -> bytes:
    return bytes.fromhex("05 00 07 01 00")


def build_freeze_screen() -> bytes:
    """Build the freeze/unfreeze packet. This command is known to be inconsistent."""

    return bytes.fromhex("04 00 03 00")


def build_set_brightness(percent: int) -> bytes:
    """Build brightness packet. Public implementations use range 5..100."""

    if not isinstance(percent, int) or not 5 <= percent <= 100:
        raise ProtocolError("brightness percent must be an integer in 5..100")
    return bytes((0x05, 0x00, 0x04, 0x80, percent))


def build_flip_screen(enabled: bool = True) -> bytes:
    return bytes((0x05, 0x00, 0x06, 0x80, 0x01 if enabled else 0x00))


def build_reset_packets() -> list[bytes]:
    """Packets observed to recover/reset the device state.

    The second packet is also shaped like a brightness packet set to 80. Keep
    this operation named as a soft reset/recovery, not as factory reset.
    """

    return [bytes.fromhex("04 00 03 80"), bytes.fromhex("05 00 04 80 50")]


def build_set_time(dt: datetime | None = None, *, year_mode: YearByteMode = YearByteMode.LOW_BYTE) -> bytes:
    """Build the date/time sync packet.

    Packet format: ``0b 00 01 80 yy mm dd dow hh mm ss``. Day-of-week is
    encoded as 1..7 where Monday is 1.
    """

    dt = dt or datetime.now()
    if isinstance(year_mode, str):
        year_mode = YearByteMode(year_mode)
    if year_mode is YearByteMode.LOW_BYTE:
        year_byte = dt.year & 0xFF
    elif year_mode is YearByteMode.TWO_DIGIT:
        year_byte = dt.year % 100
    else:  # pragma: no cover - enum exhaustiveness
        raise ProtocolError(f"unknown year mode: {year_mode}")
    return bytes(
        (
            0x0B,
            0x00,
            0x01,
            0x80,
            year_byte,
            dt.month,
            dt.day,
            dt.weekday() + 1,
            dt.hour,
            dt.minute,
            dt.second,
        )
    )


def build_pixel(x: int, y: int, color: Color | Sequence[int]) -> bytes:
    """Build a graffiti-mode packet that sets one pixel on a 32x32 display."""

    pixel = Pixel.parse(x, y, color)
    return bytes((0x0A, 0x00, 0x05, 0x01, 0x00, pixel.color.r, pixel.color.g, pixel.color.b, pixel.x, pixel.y))


def build_fullscreen_color(color: Color | Sequence[int]) -> bytes:
    color = Color.parse(color)
    return bytes((0x07, 0x00, 0x02, 0x02, color.r, color.g, color.b))


def build_clock_mode(
    style: int,
    *,
    visible_date: bool = True,
    hour24: bool = True,
    color: Color | Sequence[int] = (255, 255, 255),
) -> bytes:
    if not 0 <= style <= 7:
        raise ProtocolError("clock style must be in 0..7")
    color = Color.parse(color)
    flags = style | (0x80 if visible_date else 0x00) | (0x40 if hour24 else 0x00)
    return bytes((0x08, 0x00, 0x06, 0x01, flags, color.r, color.g, color.b))


def build_chronograph(mode: int) -> bytes:
    if not 0 <= mode <= 3:
        raise ProtocolError("chronograph mode must be in 0..3")
    return bytes((0x05, 0x00, 0x09, 0x80, mode))


def build_countdown(mode: int, minutes: int, seconds: int) -> bytes:
    if not 0 <= mode <= 3:
        raise ProtocolError("countdown mode must be in 0..3")
    _byte(minutes, name="minutes")
    if not 0 <= seconds <= 59:
        raise ProtocolError("seconds must be in 0..59")
    return bytes((0x07, 0x00, 0x08, 0x80, mode, minutes, seconds))


def build_scoreboard(score_left: int, score_right: int) -> bytes:
    if not 0 <= score_left <= 999:
        raise ProtocolError("score_left must be in 0..999")
    if not 0 <= score_right <= 999:
        raise ProtocolError("score_right must be in 0..999")
    left = struct.pack("!H", score_left)
    right = struct.pack("!H", score_right)
    return bytes((0x08, 0x00, 0x0A, 0x80, left[1], left[0], right[1], right[0]))


def build_eco_mode(flag: int, start_hour: int, start_minute: int, end_hour: int, end_minute: int, brightness: int) -> bytes:
    for name, value in (
        ("flag", flag),
        ("start_hour", start_hour),
        ("start_minute", start_minute),
        ("end_hour", end_hour),
        ("end_minute", end_minute),
        ("brightness", brightness),
    ):
        _byte(value, name=name)
    return bytes((0x0A, 0x00, 0x02, 0x80, flag, start_hour, start_minute, end_hour, end_minute, brightness))


def build_effect(style: int, colors: Iterable[Color | Sequence[int]], speed: int = 90) -> bytes:
    if not 0 <= style <= 6:
        raise ProtocolError("effect style must be in 0..6")
    _byte(speed, name="speed")
    parsed = [Color.parse(c) for c in colors]
    if not 2 <= len(parsed) <= 7:
        raise ProtocolError("effect requires between 2 and 7 colors")
    payload = bytearray((0x06 + len(parsed), 0x00, 0x03, 0x02, style, speed, len(parsed)))
    for color in parsed:
        payload.extend(color.as_bytes())
    return bytes(payload)


def build_delete_device_data() -> bytes:
    """Build the destructive delete-data packet.

    This is intentionally exposed but should not be used during fuzzing unless
    the test plan explicitly calls for it.
    """

    return bytes((0x11, 0x00, 0x02, 0x01, 0x0C, 0x00, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11))


@dataclass(frozen=True)
class TextPacketInfo:
    total_length: int
    metadata_length: int
    bitmap_length: int
    crc32: int
    num_chars: int


def build_text_packet(
    text_bitmaps: bytes | bytearray,
    *,
    text_mode: TextMode | int = TextMode.SCROLL_LEFT_TO_RIGHT,
    speed: int = 95,
    text_color_mode: TextColorMode | int = TextColorMode.FIXED,
    text_color: Color | Sequence[int] = (255, 0, 0),
    text_bg_mode: TextBackgroundMode | int = TextBackgroundMode.OFF,
    text_bg_color: Color | Sequence[int] = (0, 0, 0),
) -> bytes:
    """Build a text packet from pre-rendered 16x32 glyph bitmaps.

    ``text_bitmaps`` must be a concatenation of blocks shaped as::

        05 ff ff ff + 64 bitmap bytes

    one block per character.
    """

    text_bitmaps = bytes(text_bitmaps)
    if not text_bitmaps:
        raise ProtocolError("text_bitmaps cannot be empty")
    if len(text_bitmaps) % (len(TEXT_SEPARATOR_32) + TEXT_GLYPH_BYTES) != 0:
        raise ProtocolError("text_bitmaps length does not match 32x32 glyph block size")

    num_chars = text_bitmaps.count(TEXT_SEPARATOR_32)
    expected_len = num_chars * (len(TEXT_SEPARATOR_32) + TEXT_GLYPH_BYTES)
    if num_chars == 0 or expected_len != len(text_bitmaps):
        raise ProtocolError("text_bitmaps must contain one 05ffffff separator per glyph")

    text_mode = TextMode(int(text_mode))
    text_color_mode = TextColorMode(int(text_color_mode))
    text_bg_mode = TextBackgroundMode(int(text_bg_mode))
    speed = _byte(speed, name="speed")
    text_color = Color.parse(text_color)
    text_bg_color = Color.parse(text_bg_color)

    metadata = bytearray(
        (
            0x00,
            0x00,
            0x00,
            0x01,
            int(text_mode),
            speed,
            int(text_color_mode),
            text_color.r,
            text_color.g,
            text_color.b,
            int(text_bg_mode),
            text_bg_color.r,
            text_bg_color.g,
            text_bg_color.b,
        )
    )
    metadata[0:2] = _u16le(num_chars)

    payload = bytes(metadata) + text_bitmaps
    crc = zlib.crc32(payload) & 0xFFFFFFFF

    header = bytearray((0x00, 0x00, 0x03, 0x00, 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0x00, 0x00, 0x0C))
    total_len = len(header) + len(payload)
    header[0:2] = _u16le(total_len)
    header[5:9] = _u32le(len(payload))
    header[9:13] = _u32le(crc)
    return bytes(header) + payload


def inspect_text_packet(packet: bytes) -> TextPacketInfo:
    packet = bytes(packet)
    if len(packet) < 30 or packet[2] != 0x03 or packet[15] != 0x0C:
        raise ProtocolError("not a recognized text packet")
    total_len = int.from_bytes(packet[0:2], "little")
    metadata_and_bitmap_len = int.from_bytes(packet[5:9], "little")
    expected_crc = int.from_bytes(packet[9:13], "little")
    payload = packet[16:]
    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if total_len != len(packet):
        raise ProtocolError(f"text packet length mismatch: header says {total_len}, actual {len(packet)}")
    if metadata_and_bitmap_len != len(payload):
        raise ProtocolError("text packet metadata/bitmap length mismatch")
    if expected_crc != actual_crc:
        raise ProtocolError(f"text packet CRC mismatch: expected {expected_crc:#x}, actual {actual_crc:#x}")
    num_chars = int.from_bytes(payload[0:2], "little")
    bitmap_len = len(payload) - 14
    return TextPacketInfo(total_len, 14, bitmap_len, actual_crc, num_chars)


@dataclass(frozen=True)
class GifChunk:
    index: int
    data: bytes
    header: bytes
    payload: bytes

    @property
    def is_first(self) -> bool:
        return self.index == 0


def build_gif_chunks(
    gif_bytes: bytes | bytearray,
    *,
    total_length_mode: GifTotalLengthMode = GifTotalLengthMode.INCLUDE_HEADERS,
    chunk_size: int = GIF_PAYLOAD_CHUNK_SIZE,
) -> list[GifChunk]:
    """Build application-level GIF upload chunks.

    Each returned chunk has a 16-byte protocol header followed by up to 4096
    bytes of GIF payload. Lower BLE transports may still split each chunk into
    smaller GATT writes according to the negotiated MTU.
    """

    gif_bytes = bytes(gif_bytes)
    if not gif_bytes:
        raise ProtocolError("gif_bytes cannot be empty")
    if chunk_size <= 0:
        raise ProtocolError("chunk_size must be positive")

    raw_chunks = [gif_bytes[i : i + chunk_size] for i in range(0, len(gif_bytes), chunk_size)]
    mode = GifTotalLengthMode(total_length_mode)
    if mode is GifTotalLengthMode.INCLUDE_HEADERS:
        total_len = len(gif_bytes) + GIF_CHUNK_HEADER_SIZE * len(raw_chunks)
    elif mode is GifTotalLengthMode.RAW_PAYLOAD_ONLY:
        total_len = len(gif_bytes)
    else:  # pragma: no cover - enum exhaustiveness
        raise ProtocolError(f"unknown total_length_mode: {mode}")

    crc = zlib.crc32(gif_bytes) & 0xFFFFFFFF
    chunks: list[GifChunk] = []
    for index, raw in enumerate(raw_chunks):
        header = bytearray((0x00, 0x00, 0x01, 0x00, 0x02 if index > 0 else 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0x05, 0x00, 0x0D))
        header[0:2] = _u16le(len(raw) + GIF_CHUNK_HEADER_SIZE)
        header[5:9] = _u32le(total_len)
        header[9:13] = _u32le(crc)
        data = bytes(header) + raw
        chunks.append(GifChunk(index=index, data=data, header=bytes(header), payload=raw))
    return chunks


def build_png_payloads_experimental(png_bytes: bytes | bytearray, *, chunk_size: int = GIF_PAYLOAD_CHUNK_SIZE) -> list[bytes]:
    """Build experimental PNG/DIY payloads.

    This mirrors public notes from another implementation and is intentionally
    marked experimental. Prefer single-frame GIFs until this mode is validated
    on your hardware.
    """

    png_bytes = bytes(png_bytes)
    if not png_bytes:
        raise ProtocolError("png_bytes cannot be empty")
    chunks = [png_bytes[i : i + chunk_size] for i in range(0, len(png_bytes), chunk_size)]
    total = len(png_bytes) + len(chunks)
    if total > 0x7FFF:
        raise ProtocolError("experimental PNG payload too large for signed 16-bit header")
    total_bytes = struct.pack("h", total)
    raw_len = struct.pack("i", len(png_bytes))
    return [total_bytes + bytes((0x00, 0x00, 0x02 if i > 0 else 0x00)) + raw_len + chunk for i, chunk in enumerate(chunks)]


def expected_gif_ack_for_chunk(index: int, total_chunks: int) -> bytes:
    if total_chunks <= 0:
        raise ProtocolError("total_chunks must be positive")
    if not 0 <= index < total_chunks:
        raise ProtocolError("index out of range")
    return ACK_UPLOAD_DONE if index == total_chunks - 1 else ACK_CHUNK_OK


def parse_packet(packet: bytes | bytearray) -> dict[str, Any]:
    """Return a best-effort structured description of one packet.

    This is meant for reverse-engineering and tests. Unknown packets are not an
    error; they are returned with ``kind='unknown'`` and the raw hex string.
    """

    packet = bytes(packet)
    result: dict[str, Any] = {
        "length": len(packet),
        "hex": packet.hex(" "),
        "kind": "unknown",
    }
    if not packet:
        result["kind"] = "empty"
        return result

    if packet == build_screen_on():
        result.update(kind="screen_on")
        return result
    if packet == build_screen_off():
        result.update(kind="screen_off")
        return result
    if packet == build_freeze_screen():
        result.update(kind="freeze_screen")
        return result

    if len(packet) == 5 and packet[0:4] == bytes((0x05, 0x00, 0x04, 0x80)):
        result.update(kind="brightness", brightness=packet[4])
        return result
    if packet in build_reset_packets():
        result.update(kind="reset_or_recover")
        return result
    if len(packet) == 5 and packet[0:4] == bytes((0x05, 0x00, 0x06, 0x80)):
        result.update(kind="flip_screen", enabled=bool(packet[4]))
        return result
    if len(packet) == 11 and packet[0:4] == bytes((0x0B, 0x00, 0x01, 0x80)):
        result.update(
            kind="set_time",
            year_byte=packet[4],
            month=packet[5],
            day=packet[6],
            dow=packet[7],
            hour=packet[8],
            minute=packet[9],
            second=packet[10],
        )
        return result
    if len(packet) == 10 and packet[0:5] == bytes((0x0A, 0x00, 0x05, 0x01, 0x00)):
        result.update(kind="pixel", color=(packet[5], packet[6], packet[7]), x=packet[8], y=packet[9])
        return result
    if len(packet) == 7 and packet[0:4] == bytes((0x07, 0x00, 0x02, 0x02)):
        result.update(kind="fullscreen_color", color=(packet[4], packet[5], packet[6]))
        return result
    if len(packet) == 8 and packet[0:4] == bytes((0x08, 0x00, 0x06, 0x01)):
        flags = packet[4]
        result.update(
            kind="clock",
            style=flags & 0x3F,
            visible_date=bool(flags & 0x80),
            hour24=bool(flags & 0x40),
            color=(packet[5], packet[6], packet[7]),
        )
        return result
    if len(packet) == 5 and packet[0:4] == bytes((0x05, 0x00, 0x09, 0x80)):
        result.update(kind="chronograph", mode=packet[4])
        return result
    if len(packet) == 7 and packet[0:4] == bytes((0x07, 0x00, 0x08, 0x80)):
        result.update(kind="countdown", mode=packet[4], minutes=packet[5], seconds=packet[6])
        return result
    if len(packet) == 8 and packet[0:4] == bytes((0x08, 0x00, 0x0A, 0x80)):
        result.update(
            kind="scoreboard",
            score_left=packet[4] | (packet[5] << 8),
            score_right=packet[6] | (packet[7] << 8),
        )
        return result
    if len(packet) == 10 and packet[0:4] == bytes((0x0A, 0x00, 0x02, 0x80)):
        result.update(
            kind="eco",
            flag=packet[4],
            start_hour=packet[5],
            start_minute=packet[6],
            end_hour=packet[7],
            end_minute=packet[8],
            brightness=packet[9],
        )
        return result
    if len(packet) >= 13 and packet[2:4] == bytes((0x03, 0x02)) and packet[6] * 3 == len(packet) - 7:
        colors = [tuple(packet[i : i + 3]) for i in range(7, len(packet), 3)]
        result.update(kind="effect", style=packet[4], speed=packet[5], color_count=packet[6], colors=colors)
        return result
    if packet == build_delete_device_data():
        result.update(kind="delete_device_data")
        return result

    if len(packet) >= 16 and packet[2:4] == bytes((0x01, 0x00)) and packet[13:16] == bytes((0x05, 0x00, 0x0D)):
        result.update(
            kind="gif_chunk",
            chunk_length=int.from_bytes(packet[0:2], "little"),
            continuation_marker=packet[4],
            total_length=int.from_bytes(packet[5:9], "little"),
            crc32=int.from_bytes(packet[9:13], "little"),
            payload_length=max(0, len(packet) - GIF_CHUNK_HEADER_SIZE),
        )
        return result

    if len(packet) >= 16 and packet[2] == 0x03 and packet[15] == 0x0C:
        payload = packet[16:]
        expected_crc = int.from_bytes(packet[9:13], "little")
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        result.update(
            kind="text",
            total_length=int.from_bytes(packet[0:2], "little"),
            metadata_and_bitmap_length=int.from_bytes(packet[5:9], "little"),
            crc32_expected=expected_crc,
            crc32_actual=actual_crc,
            crc32_ok=expected_crc == actual_crc,
            num_chars=int.from_bytes(payload[0:2], "little") if len(payload) >= 2 else None,
        )
        return result

    return result


def generate_spiral_pixels(
    *,
    color: Color | Sequence[int] = (255, 0, 0),
    grid_size: int = WIDTH,
    num_points: int = 500,
) -> list[Pixel]:
    """Utility similar to the original experiment: generate a simple spiral."""

    color = Color.parse(color)
    center = grid_size // 2
    seen: set[tuple[int, int]] = set()
    pixels: list[Pixel] = []
    for t in range(num_points):
        angle = 0.1 * t
        radius = 0.5 * angle
        x = int(center + radius * math.cos(angle))
        y = int(center + radius * math.sin(angle))
        if 0 <= x < grid_size and 0 <= y < grid_size and (x, y) not in seen:
            seen.add((x, y))
            pixels.append(Pixel(x, y, color))
    return pixels
