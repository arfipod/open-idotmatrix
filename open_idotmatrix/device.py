"""High-level async device client for open-idotmatrix."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from .constants import ACK_CHUNK_OK, ACK_UPLOAD_DONE, WIDTH
from .framebuffer import MatrixFrame
from .gif import gif_chunks_from_file, image_chunks_from_file, image_chunks_from_image
from .profile import DeviceProfile
from .protocol import (
    build_chronograph,
    build_clock_mode,
    build_countdown,
    build_delete_device_data,
    build_eco_mode,
    build_effect,
    build_flip_screen,
    build_freeze_screen,
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
from .session import SessionLogger
from .text import render_text_bitmap_bytes
from .transport import BleTransport, DiscoveredDevice
from .types import (
    Color,
    GifAckPolicy,
    GifTotalLengthMode,
    Pixel,
    TextBackgroundMode,
    TextColorMode,
    TextMode,
    YearByteMode,
)


class OpenIDotMatrix:
    """Async high-level API for an iDotMatrix-compatible 32x32 display."""

    def __init__(
        self,
        address: str | None = None,
        *,
        transport: BleTransport | None = None,
        profile: DeviceProfile | None = None,
        session_logger: SessionLogger | str | Path | None = None,
    ) -> None:
        profile = profile or DeviceProfile(address=address)
        if address is not None and profile.address != address:
            profile = profile.with_address(address)
        self.profile = profile
        if transport is None:
            self.transport = BleTransport(
                address=profile.address,
                inter_write_delay=profile.inter_write_delay,
                gatt_chunk_size=profile.gatt_chunk_size,
                session_logger=session_logger,
            )
        else:
            self.transport = transport
            if session_logger is not None and hasattr(self.transport, "session_logger"):
                self.transport.session_logger = BleTransport._coerce_session_logger(session_logger)

    @classmethod
    async def scan(cls, *, timeout: float = 5.0, name_prefix: str = "IDM-") -> list[DiscoveredDevice]:
        return await BleTransport.scan(timeout=timeout, name_prefix=name_prefix)

    async def connect(self) -> None:
        await self.transport.connect()

    async def disconnect(self) -> None:
        await self.transport.disconnect()

    async def __aenter__(self) -> OpenIDotMatrix:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    def _response(self, response: bool | None) -> bool:
        return self.profile.write_response if response is None else response

    async def send(self, packet: bytes | bytearray, *, response: bool | None = None) -> dict:
        packet = bytes(packet)
        await self.transport.write(packet, response=self._response(response))
        return parse_packet(packet)

    async def on(self) -> dict:
        return await self.send(build_screen_on())

    async def off(self) -> dict:
        return await self.send(build_screen_off())

    async def set_brightness(self, percent: int) -> dict:
        return await self.send(build_set_brightness(percent))

    async def flip(self, enabled: bool = True) -> dict:
        return await self.send(build_flip_screen(enabled))

    async def freeze(self) -> dict:
        return await self.send(build_freeze_screen())

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
        year_mode: YearByteMode | str | None = None,
    ) -> dict:
        year_mode = self.profile.year_byte_mode if year_mode is None else YearByteMode(year_mode)
        return await self.send(build_set_time(dt, year_mode=year_mode))

    async def fill(self, color: Color | Sequence[int]) -> dict:
        return await self.send(build_fullscreen_color(color))

    async def pixel(self, x: int, y: int, color: Color | Sequence[int]) -> dict:
        return await self.send(build_pixel(x, y, color))

    async def pixels(self, pixels: Iterable[Pixel], *, delay: float = 0.0) -> list[dict]:
        return await self.pixels_fast(pixels, inter_packet_delay=delay, parse=True)

    async def pixels_fast(
        self,
        pixels: Iterable[Pixel],
        *,
        response: bool | None = None,
        inter_packet_delay: float = 0.0,
        parse: bool = False,
    ) -> list[dict]:
        """Send many single-pixel packets through the transport fast path."""

        packets = [build_pixel(pixel.x, pixel.y, pixel.color) for pixel in pixels]
        if hasattr(self.transport, "write_many_packets"):
            await self.transport.write_many_packets(
                packets,
                response=self._response(response),
                inter_packet_delay=inter_packet_delay,
                concatenate=self.profile.pixel_batch_mode == "concatenate",
            )
        else:
            for packet in packets:
                await self.transport.write(packet, response=self._response(response))
                if inter_packet_delay:
                    await asyncio.sleep(inter_packet_delay)
        if not parse:
            return []
        return [parse_packet(packet) for packet in packets]

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

    async def _send_upload_chunks(
        self,
        chunks,
        *,
        wait_for_ack: bool,
        ack_policy: GifAckPolicy | str,
        response: bool,
        ack_timeout: float,
        sleep_between_chunks: float,
    ) -> list[dict]:
        ack_policy = GifAckPolicy.NONE if not wait_for_ack else GifAckPolicy(ack_policy)
        if ack_policy is not GifAckPolicy.NONE:
            await self.transport.start_notifications()
        results = []
        for index, chunk in enumerate(chunks):
            await self.transport.write(chunk.data, response=response)
            results.append(parse_packet(chunk.data))
            if ack_policy is not GifAckPolicy.NONE:
                await self._wait_for_gif_ack(index, len(chunks), policy=ack_policy, timeout=ack_timeout)
            elif sleep_between_chunks:
                await asyncio.sleep(sleep_between_chunks)
        return results

    async def _wait_for_gif_ack(
        self,
        index: int,
        total_chunks: int,
        *,
        policy: GifAckPolicy,
        timeout: float,
    ) -> list[bytes]:
        if policy is GifAckPolicy.EXACT:
            return [
                await self.transport.wait_for_notification(
                    expected_gif_ack_for_chunk(index, total_chunks),
                    timeout=timeout,
                )
            ]
        if policy is GifAckPolicy.OK_OR_DONE:
            return [await self.transport.wait_for_notification((ACK_CHUNK_OK, ACK_UPLOAD_DONE), timeout=timeout)]
        if policy is GifAckPolicy.WAIT_DONE_AFTER_FINAL:
            if index < total_chunks - 1:
                return [await self.transport.wait_for_notification(ACK_CHUNK_OK, timeout=timeout)]
            first = await self.transport.wait_for_notification((ACK_CHUNK_OK, ACK_UPLOAD_DONE), timeout=timeout)
            received = [first]
            if first == ACK_CHUNK_OK:
                received.append(await self.transport.wait_for_notification(ACK_UPLOAD_DONE, timeout=timeout))
            return received
        if policy is GifAckPolicy.NONE:
            return []
        raise ValueError(f"unknown GIF ACK policy: {policy}")  # pragma: no cover

    async def gif(
        self,
        path: str | Path,
        *,
        process: bool = True,
        total_length_mode: GifTotalLengthMode | str | None = None,
        wait_for_ack: bool | None = None,
        ack_policy: GifAckPolicy | str | None = None,
        response: bool = True,
        ack_timeout: float = 10.0,
        sleep_between_chunks: float = 1.0,
    ) -> list[dict]:
        total_length_mode = self.profile.gif_total_length_mode if total_length_mode is None else total_length_mode
        wait_for_ack = self.profile.gif_wait_for_ack if wait_for_ack is None else wait_for_ack
        ack_policy = self.profile.gif_ack_policy if ack_policy is None else ack_policy
        chunks = gif_chunks_from_file(path, process=process, pixel_size=WIDTH, total_length_mode=total_length_mode)
        return await self._send_upload_chunks(
            chunks,
            wait_for_ack=wait_for_ack,
            ack_policy=ack_policy,
            response=response,
            ack_timeout=ack_timeout,
            sleep_between_chunks=sleep_between_chunks,
        )

    async def image(
        self,
        path: str | Path,
        *,
        total_length_mode: GifTotalLengthMode | str | None = None,
        wait_for_ack: bool | None = None,
        ack_policy: GifAckPolicy | str | None = None,
        response: bool = True,
        ack_timeout: float = 10.0,
        sleep_between_chunks: float = 1.0,
    ) -> list[dict]:
        total_length_mode = self.profile.gif_total_length_mode if total_length_mode is None else total_length_mode
        wait_for_ack = self.profile.gif_wait_for_ack if wait_for_ack is None else wait_for_ack
        ack_policy = self.profile.gif_ack_policy if ack_policy is None else ack_policy
        chunks = image_chunks_from_file(path, pixel_size=WIDTH, total_length_mode=total_length_mode)
        return await self._send_upload_chunks(
            chunks,
            wait_for_ack=wait_for_ack,
            ack_policy=ack_policy,
            response=response,
            ack_timeout=ack_timeout,
            sleep_between_chunks=sleep_between_chunks,
        )

    async def frame(
        self,
        frame: MatrixFrame,
        *,
        total_length_mode: GifTotalLengthMode | str | None = None,
        wait_for_ack: bool | None = None,
        ack_policy: GifAckPolicy | str | None = None,
        response: bool = True,
        ack_timeout: float = 10.0,
        sleep_between_chunks: float = 1.0,
    ) -> list[dict]:
        """Upload a MatrixFrame as a single-frame GIF."""

        total_length_mode = self.profile.gif_total_length_mode if total_length_mode is None else total_length_mode
        wait_for_ack = self.profile.gif_wait_for_ack if wait_for_ack is None else wait_for_ack
        ack_policy = self.profile.gif_ack_policy if ack_policy is None else ack_policy
        chunks = image_chunks_from_image(frame.to_image(), pixel_size=WIDTH, total_length_mode=total_length_mode)
        return await self._send_upload_chunks(
            chunks,
            wait_for_ack=wait_for_ack,
            ack_policy=ack_policy,
            response=response,
            ack_timeout=ack_timeout,
            sleep_between_chunks=sleep_between_chunks,
        )

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
