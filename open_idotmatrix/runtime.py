"""Synchronous runtime for game loops that cannot own an asyncio loop."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from .device import OpenIDotMatrix
from .framebuffer import MatrixFrame
from .profile import DeviceProfile
from .renderer import MatrixRenderer
from .session import SessionLogger
from .transport import BleTransport
from .types import Color, RGBTuple


class MatrixRuntime:
    """Run OpenIDotMatrix + MatrixRenderer on a background asyncio thread.

    ``submit_frame`` is non-blocking and uses a queue of size one. If the game
    loop produces frames faster than BLE can send them, the older queued frame
    is dropped and the newest frame wins.
    """

    def __init__(
        self,
        address: str | None = None,
        *,
        device: OpenIDotMatrix | None = None,
        transport: BleTransport | None = None,
        profile: DeviceProfile | None = None,
        session_logger: SessionLogger | str | Path | None = None,
        renderer_kwargs: dict[str, Any] | None = None,
        clear_first: Color | RGBTuple | None = None,
    ) -> None:
        self.address = address
        self.device = device
        self.transport = transport
        self.profile = profile
        self.session_logger = session_logger
        self.renderer_kwargs = renderer_kwargs or {}
        self.clear_first = clear_first

        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[MatrixFrame | None] | None = None
        self._started = threading.Event()
        self._connected = threading.Event()
        self._closed = threading.Event()
        self._startup_error: BaseException | None = None

    def start(self, *, timeout: float | None = 10.0) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._started.clear()
        self._connected.clear()
        self._closed.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._thread_main, name="open-idotmatrix-runtime", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout):
            raise TimeoutError("timed out starting MatrixRuntime")
        if not self._connected.wait(timeout):
            if self._startup_error is not None:
                raise RuntimeError("MatrixRuntime failed to connect") from self._startup_error
            raise TimeoutError("timed out connecting MatrixRuntime")

    def submit_frame(self, frame: MatrixFrame) -> bool:
        """Queue the latest frame without blocking the caller."""

        if self._loop is None or self._queue is None or self._closed.is_set():
            return False
        snapshot = frame.copy()
        self._loop.call_soon_threadsafe(self._replace_queued_frame, snapshot)
        return True

    def wait_until_idle(self, *, timeout: float | None = None) -> None:
        if self._loop is None or self._queue is None:
            return
        future = asyncio.run_coroutine_threadsafe(self._queue.join(), self._loop)
        future.result(timeout=timeout)

    def close(self, *, timeout: float | None = 10.0) -> None:
        if self._loop is not None and self._queue is not None and not self._closed.is_set():
            self._loop.call_soon_threadsafe(self._request_stop)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        if self._thread is not None and self._thread.is_alive():
            raise TimeoutError("timed out closing MatrixRuntime")

    def __enter__(self) -> MatrixRuntime:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=1)
        self._started.set()
        try:
            loop.run_until_complete(self._run())
        except BaseException as exc:
            if self._startup_error is None:
                self._startup_error = exc
            self._connected.set()
        finally:
            loop.close()
            self._loop = None
            self._queue = None
            self._closed.set()

    async def _run(self) -> None:
        device = self.device or OpenIDotMatrix(
            address=self.address,
            transport=self.transport,
            profile=self.profile,
            session_logger=self.session_logger,
        )
        self.device = device
        renderer = MatrixRenderer(device, **self.renderer_kwargs)
        try:
            await device.connect()
            if self.clear_first is not None:
                await device.fill(self.clear_first)
                renderer.previous_frame = MatrixFrame(fill=self.clear_first)
        except BaseException as exc:
            self._startup_error = exc
            self._connected.set()
            raise
        self._connected.set()
        try:
            assert self._queue is not None
            while True:
                frame = await self._queue.get()
                try:
                    if frame is None:
                        return
                    await renderer.show(frame)
                finally:
                    self._queue.task_done()
        finally:
            await device.disconnect()

    def _replace_queued_frame(self, frame: MatrixFrame) -> None:
        if self._queue is None:
            return
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        self._queue.put_nowait(frame)

    def _request_stop(self) -> None:
        if self._queue is None:
            return
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        self._queue.put_nowait(None)


__all__ = ["MatrixRuntime"]
