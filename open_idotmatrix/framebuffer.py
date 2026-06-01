"""Bytearray-backed 32x32 RGB framebuffer."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from PIL import Image

from .constants import HEIGHT, PIXEL_COUNT, WIDTH
from .exceptions import ProtocolError
from .types import Color, Pixel, Point, RGBTuple

_BLACK = (0, 0, 0)
_FRAME_BYTES = PIXEL_COUNT * 3


class MatrixFrame:
    """A compact 32x32 RGB frame for rendering, diffing, and uploads."""

    width = WIDTH
    height = HEIGHT

    def __init__(
        self,
        fill: Color | Sequence[int] = _BLACK,
        *,
        data: bytes | bytearray | None = None,
    ) -> None:
        if data is not None:
            if len(data) != _FRAME_BYTES:
                raise ProtocolError(f"frame data must be exactly {_FRAME_BYTES} bytes")
            self.data = bytearray(data)
        else:
            self.data = bytearray(_FRAME_BYTES)
            self.clear(fill)

    @staticmethod
    def _offset(x: int, y: int) -> int:
        point = Point(x, y)
        return (point.y * WIDTH + point.x) * 3

    def copy(self) -> MatrixFrame:
        return MatrixFrame(data=self.data)

    def clear(self, color: Color | Sequence[int] = _BLACK) -> None:
        color = Color.parse(color)
        self.data[:] = color.as_bytes() * PIXEL_COUNT

    def fill(self, color: Color | Sequence[int]) -> None:
        self.clear(color)

    def set_pixel(self, x: int, y: int, color: Color | Sequence[int]) -> None:
        color = Color.parse(color)
        offset = self._offset(x, y)
        self.data[offset : offset + 3] = color.as_bytes()

    def get_pixel(self, x: int, y: int) -> RGBTuple:
        offset = self._offset(x, y)
        return self.data[offset], self.data[offset + 1], self.data[offset + 2]

    def diff(self, previous: MatrixFrame) -> list[Pixel]:
        if not isinstance(previous, MatrixFrame):
            raise ProtocolError("previous frame must be a MatrixFrame")
        changed: list[Pixel] = []
        for offset in range(0, _FRAME_BYTES, 3):
            if self.data[offset : offset + 3] == previous.data[offset : offset + 3]:
                continue
            pixel_index = offset // 3
            x = pixel_index % WIDTH
            y = pixel_index // WIDTH
            changed.append(Pixel.parse(x, y, self.data[offset : offset + 3]))
        return changed

    def iter_pixels(self) -> Iterator[Pixel]:
        for offset in range(0, _FRAME_BYTES, 3):
            pixel_index = offset // 3
            x = pixel_index % WIDTH
            y = pixel_index // WIDTH
            yield Pixel.parse(x, y, self.data[offset : offset + 3])

    def solid_color(self) -> RGBTuple | None:
        first = bytes(self.data[0:3])
        for offset in range(3, _FRAME_BYTES, 3):
            if self.data[offset : offset + 3] != first:
                return None
        return first[0], first[1], first[2]

    def to_image(self) -> Image.Image:
        return Image.frombytes("RGB", (WIDTH, HEIGHT), bytes(self.data))

    @classmethod
    def from_image(cls, image: Image.Image) -> MatrixFrame:
        image = image.convert("RGB")
        if image.size != (WIDTH, HEIGHT):
            image = image.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)
        return cls(data=image.tobytes())

    def __getitem__(self, point: tuple[int, int]) -> RGBTuple:
        x, y = point
        return self.get_pixel(x, y)

    def __setitem__(self, point: tuple[int, int], color: Color | Sequence[int]) -> None:
        x, y = point
        self.set_pixel(x, y, color)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MatrixFrame) and self.data == other.data

    def __repr__(self) -> str:
        return f"MatrixFrame(width={WIDTH}, height={HEIGHT}, bytes={len(self.data)})"


__all__ = ["MatrixFrame"]
