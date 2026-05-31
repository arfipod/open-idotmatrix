"""High-level async device client for open-idotmatrix."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from .constants import ACK_CHUNK_OK, ACK_UPLOAD_DONE, WIDTH
from .gif import gif_chunks_from_file
from .protocol import (
    build_chronograph,
    build_clock_mode,
    build_countdown,
    build_delete_device_data,
    build_eco_mode,
    build_effect,
    build_flip_screen,
    build_fullscreen_color,
    build_pixel,
    build_reset_packets,
    build_scoreboard,
    build_screen_off,
    build_screen_on,
    build_set_brightness,
    build_set_time,
    build_text_packet,
    expected_gif_ack_for_chunk,
    generate_spiral_pixels,
    parse_packet,
)
from .text import render_text_bitmap_bytes
from .transport import BleTransport, DiscoveredDevice
from .types import (
    Color,
    GifTotalLengthMode,
    Pixel,
    TextBackgroundMode,
    TextColorMode,
    TextMode,
    YearByteMode,
)


class OpenIDotMatrix:
    """Async high-level API for an iDotMatrix-compatible 32x32 display."""

    def __init__(self, address: str | None = None, *, transport: BleTransport | None = None) -> None:
        self.transport = transport or BleTransport(address=address)

    @classmethod
    async def scan(cls, *, timeout: float = 5.0) -> list[DiscoveredDevice]:
        return await BleTransport.scan(timeout=timeout)

    async def connect(self) -> None:
        await self.transport.connect()

    async def disconnect(self) -> None:
        await self.transport.disconnect()

    async def __aenter__(self) -> OpenIDotMatrix:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    async def send(self, packet: bytes | bytearray, *, response: bool = False) -> dict:
        packet = bytes(packet)
        await self.transport.write(packet, response=response)
        return parse_packet(packet)

    async def on(self) -> dict:
        return await self.send(build_screen_on())

    async def off(self) -> dict:
        return await self.send(build_screen_off())

    async def set_brightness(self, percent: int) -> dict:
        return await self.send(build_set_brightness(percent))

    async def flip(self, enabled: bool = True) -> dict:
        return await self.send(build_flip_screen(enabled))

    async def reset(self) -> list[dict]:
        results = []
        for packet in build_reset_packets():
            results.append(await self.send(packet))
            await asyncio.sleep(0.05)
        return results

    async def sync_time(
        self,
        dt: datetime | None = None,
        *,
        year_mode: YearByteMode = YearByteMode.LOW_BYTE,
    ) -> dict:
        return await self.send(build_set_time(dt, year_mode=year_mode))

    async def fill(self, color: Color | Sequence[int]) -> dict:
        return await self.send(build_fullscreen_color(color))

    async def pixel(self, x: int, y: int, color: Color | Sequence[int]) -> dict:
        return await self.send(build_pixel(x, y, color))

    async def pixels(self, pixels: Iterable[Pixel], *, delay: float = 0.0) -> list[dict]:
        results = []
        for pixel in pixels:
            results.append(await self.pixel(pixel.x, pixel.y, pixel.color))
            if delay:
                await asyncio.sleep(delay)
        return results

    async def spiral(self, color: Color | Sequence[int] = (255, 0, 0), *, delay: float = 0.0) -> list[dict]:
        return await self.pixels(generate_spiral_pixels(color=color), delay=delay)

    async def text(
        self,
        text: str,
        *,
        mode: TextMode | int = TextMode.SCROLL_LEFT_TO_RIGHT,
        speed: int = 95,
        color_mode: TextColorMode | int = TextColorMode.FIXED,
        color: Color | Sequence[int] = (255, 255, 255),
        background_mode: TextBackgroundMode | int = TextBackgroundMode.OFF,
        background: Color | Sequence[int] = (0, 0, 0),
        font_path: str | None = None,
        font_size: int = 24,
    ) -> dict:
        bitmaps = render_text_bitmap_bytes(text, font_path=font_path, font_size=font_size)
        packet = build_text_packet(
            bitmaps,
            text_mode=mode,
            speed=speed,
            text_color_mode=color_mode,
            text_color=color,
            text_bg_mode=background_mode,
            text_bg_color=background,
        )
        return await self.send(packet)

    async def gif(
        self,
        path: str | Path,
        *,
        process: bool = True,
        total_length_mode: GifTotalLengthMode = GifTotalLengthMode.INCLUDE_HEADERS,
        wait_for_ack: bool = True,
        response: bool = True,
        ack_timeout: float = 10.0,
        sleep_between_chunks: float = 1.0,
    ) -> list[dict]:
        chunks = gif_chunks_from_file(path, process=process, pixel_size=WIDTH, total_length_mode=total_length_mode)
        if wait_for_ack:
            await self.transport.start_notifications()
        results = []
        for index, chunk in enumerate(chunks):
            await self.transport.write(chunk.data, response=response)
            results.append(parse_packet(chunk.data))
            if wait_for_ack:
                expected = expected_gif_ack_for_chunk(index, len(chunks))
                await self.transport.wait_for_notification(expected, timeout=ack_timeout)
            elif sleep_between_chunks:
                await asyncio.sleep(sleep_between_chunks)
        return results

    async def clock(
        self,
        style: int,
        *,
        visible_date: bool = True,
        hour24: bool = True,
        color: Color | Sequence[int] = (255, 255, 255),
    ) -> dict:
        return await self.send(build_clock_mode(style, visible_date=visible_date, hour24=hour24, color=color))

    async def chronograph(self, mode: int) -> dict:
        return await self.send(build_chronograph(mode))

    async def countdown(self, mode: int, minutes: int, seconds: int) -> dict:
        return await self.send(build_countdown(mode, minutes, seconds))

    async def scoreboard(self, score_left: int, score_right: int) -> dict:
        return await self.send(build_scoreboard(score_left, score_right))

    async def eco(
        self,
        flag: int,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        brightness: int,
    ) -> dict:
        return await self.send(build_eco_mode(flag, start_hour, start_minute, end_hour, end_minute, brightness))

    async def effect(self, style: int, colors: Iterable[Color | Sequence[int]], *, speed: int = 90) -> dict:
        return await self.send(build_effect(style, colors, speed=speed))

    async def delete_device_data(self) -> dict:
        """Destructive command. Prefer not to use during normal reverse-engineering."""

        return await self.send(build_delete_device_data())


__all__ = ["OpenIDotMatrix", "ACK_CHUNK_OK", "ACK_UPLOAD_DONE"]
