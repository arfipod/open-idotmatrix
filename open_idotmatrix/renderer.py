"""Frame renderer that chooses efficient device update strategies."""

from __future__ import annotations

from typing import Any

from .exceptions import ProtocolError
from .framebuffer import MatrixFrame
from .types import GifTotalLengthMode


class MatrixRenderer:
    """Render MatrixFrame instances through OpenIDotMatrix.

    The automatic strategy keeps a previous frame, sends no-op updates when
    nothing changed, uses pixel diffs for sparse changes, solid fill for full
    solid frames, and falls back to a single-frame GIF upload for dense frames.
    """

    def __init__(
        self,
        device: Any,
        *,
        max_pixel_updates: int = 128,
        strategy: str = "auto",
        image_total_length_mode: GifTotalLengthMode | str | None = None,
        image_wait_for_ack: bool | None = None,
        image_response: bool = True,
        image_ack_timeout: float = 10.0,
        image_sleep_between_chunks: float = 1.0,
    ) -> None:
        if max_pixel_updates < 0:
            raise ProtocolError("max_pixel_updates must be non-negative")
        if strategy not in {"auto", "pixels", "fill", "image", "gif"}:
            raise ProtocolError("strategy must be one of: auto, pixels, fill, image, gif")
        self.device = device
        self.max_pixel_updates = max_pixel_updates
        self.strategy = strategy
        self.previous_frame: MatrixFrame | None = None
        self.image_total_length_mode = image_total_length_mode
        self.image_wait_for_ack = image_wait_for_ack
        self.image_response = image_response
        self.image_ack_timeout = image_ack_timeout
        self.image_sleep_between_chunks = image_sleep_between_chunks

    async def show(self, frame: MatrixFrame) -> dict[str, Any]:
        if not isinstance(frame, MatrixFrame):
            raise ProtocolError("frame must be a MatrixFrame")

        changed = list(frame.iter_pixels()) if self.previous_frame is None else frame.diff(self.previous_frame)
        solid_color = frame.solid_color()
        strategy = self._choose_strategy(frame, changed, solid_color)

        if strategy == "noop":
            result: Any = None
        elif strategy == "fill":
            assert solid_color is not None
            result = await self.device.fill(solid_color)
        elif strategy == "pixels":
            result = await self.device.pixels_fast(changed, parse=False)
        elif strategy == "image":
            result = await self.device.frame(
                frame,
                total_length_mode=self.image_total_length_mode,
                wait_for_ack=self.image_wait_for_ack,
                response=self.image_response,
                ack_timeout=self.image_ack_timeout,
                sleep_between_chunks=self.image_sleep_between_chunks,
            )
        else:  # pragma: no cover - _choose_strategy guards this
            raise ProtocolError(f"unknown render strategy: {strategy}")

        self.previous_frame = frame.copy()
        return {"strategy": strategy, "changed_pixels": len(changed), "result": result}

    def _choose_strategy(
        self,
        frame: MatrixFrame,
        changed: list,
        solid_color: tuple[int, int, int] | None,
    ) -> str:
        if self.strategy == "fill":
            if solid_color is None:
                raise ProtocolError("fill strategy requires a solid-color frame")
            return "fill"
        if self.strategy in {"image", "gif"}:
            return "image"
        if self.strategy == "pixels":
            return "noop" if not changed else "pixels"

        if self.previous_frame is None:
            return "fill" if solid_color is not None else "image"
        if not changed:
            return "noop"
        if solid_color is not None and len(changed) > self.max_pixel_updates:
            return "fill"
        if len(changed) <= self.max_pixel_updates:
            return "pixels"
        return "image"


__all__ = ["MatrixRenderer"]
