"""Hardware-free testing helpers for open-idotmatrix applications."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .exceptions import AckTimeoutError


@dataclass(frozen=True)
class FakeWrite:
    data: bytes
    response: bool = False


class FakeTransport:
    """In-memory transport with the small surface used by OpenIDotMatrix."""

    def __init__(self, address: str = "fake-device") -> None:
        self.address = address
        self.connected = False
        self.writes: list[FakeWrite] = []
        self.packet_batches: list[list[bytes]] = []
        self.notification_history: list[bytes] = []
        self.notifications_started_count = 0
        self.notifications_stopped_count = 0
        self._notification_queue: asyncio.Queue[bytes] | None = None
        self._notification_callbacks = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    async def write(self, data: bytes | bytearray, *, response: bool = False) -> None:
        self.writes.append(FakeWrite(bytes(data), response=response))

    async def write_many_packets(
        self,
        packets: Iterable[bytes | bytearray],
        *,
        response: bool = False,
        inter_packet_delay: float = 0.0,
        concatenate: bool = False,
    ) -> None:
        packet_list = [bytes(packet) for packet in packets]
        self.packet_batches.append(packet_list)
        if concatenate:
            if packet_list:
                await self.write(b"".join(packet_list), response=response)
            return
        for packet in packet_list:
            await self.write(packet, response=response)
            if inter_packet_delay:
                await asyncio.sleep(inter_packet_delay)

    async def start_notifications(self, callback=None) -> None:
        self.notifications_started_count += 1
        if self._notification_queue is None:
            self._notification_queue = asyncio.Queue()
        if callback is not None and callback not in self._notification_callbacks:
            self._notification_callbacks.append(callback)

    async def stop_notifications(self) -> None:
        self.notifications_stopped_count += 1
        self._notification_queue = None
        self._notification_callbacks.clear()

    def push_notification(self, data: bytes | bytearray) -> None:
        payload = bytes(data)
        self.notification_history.append(payload)
        if self._notification_queue is not None:
            self._notification_queue.put_nowait(payload)
        for callback in tuple(self._notification_callbacks):
            callback(payload)

    async def wait_for_notification(
        self,
        expected: bytes | Sequence[bytes] | None = None,
        *,
        timeout: float = 5.0,
    ) -> bytes:
        if self._notification_queue is None:
            await self.start_notifications()
        assert self._notification_queue is not None
        if expected is None:
            expected_values = None
        elif isinstance(expected, bytes):
            expected_values = (expected,)
        else:
            expected_values = tuple(bytes(item) for item in expected)

        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AckTimeoutError("timed out waiting for fake notification")
            try:
                payload = await asyncio.wait_for(self._notification_queue.get(), timeout=remaining)
            except TimeoutError as exc:
                raise AckTimeoutError("timed out waiting for fake notification") from exc
            if expected_values is None or payload in expected_values:
                return payload


__all__ = ["FakeTransport", "FakeWrite"]
