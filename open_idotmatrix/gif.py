"""GIF/image preparation helpers for iDotMatrix 32x32 upload packets."""

from __future__ import annotations

import io
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageSequence

from .constants import HEIGHT, WIDTH
from .exceptions import ProtocolError
from .protocol import GifChunk, build_gif_chunks
from .types import GifTotalLengthMode


def load_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def assert_image_size(path: str | Path, *, size: tuple[int, int] = (WIDTH, HEIGHT)) -> None:
    with Image.open(path) as image:
        if image.size != size:
            raise ProtocolError(f"image must be {size[0]}x{size[1]}, got {image.size[0]}x{image.size[1]}")


def process_gif_bytes(path: str | Path, *, pixel_size: int = WIDTH) -> bytes:
    """Resize a GIF or still image into a pixel_size x pixel_size GIF byte stream."""

    path = Path(path)
    if pixel_size <= 0:
        raise ProtocolError("pixel_size must be positive")

    with Image.open(path) as image:
        frames: list[Image.Image] = []
        durations: list[int] = []
        for frame in ImageSequence.Iterator(image):
            frame_rgba = frame.convert("RGBA")
            if frame_rgba.size != (pixel_size, pixel_size):
                frame_rgba = frame_rgba.resize((pixel_size, pixel_size), Image.Resampling.NEAREST)
            frames.append(frame_rgba.convert("P", palette=Image.Palette.ADAPTIVE))
            durations.append(int(frame.info.get("duration", image.info.get("duration", 100))))

        if not frames:
            raise ProtocolError(f"no frames found in {path}")

        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
            optimize=False,
        )
        return buffer.getvalue()


def gif_chunks_from_file(
    path: str | Path,
    *,
    process: bool = True,
    pixel_size: int = WIDTH,
    total_length_mode: GifTotalLengthMode = GifTotalLengthMode.INCLUDE_HEADERS,
) -> list[GifChunk]:
    """Load/process a GIF file and return upload chunks."""

    gif_bytes = process_gif_bytes(path, pixel_size=pixel_size) if process else load_bytes(path)
    if not process:
        with Image.open(io.BytesIO(gif_bytes)) as image:
            if image.size != (pixel_size, pixel_size):
                raise ProtocolError(
                    f"unprocessed GIF/image must already be {pixel_size}x{pixel_size}; got {image.size}"
                )
    return build_gif_chunks(gif_bytes, total_length_mode=total_length_mode)


def first_frame_image(path_or_bytes: str | Path | bytes | bytearray, *, pixel_size: int = WIDTH) -> Image.Image:
    """Return the first frame as an RGB image resized for simulation."""

    source = io.BytesIO(bytes(path_or_bytes)) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    with Image.open(source) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGB")
        if frame.size != (pixel_size, pixel_size):
            frame = frame.resize((pixel_size, pixel_size), Image.Resampling.NEAREST)
        return frame.copy()


def frame_images(path: str | Path, *, pixel_size: int = WIDTH, max_frames: int | None = None) -> Iterable[Image.Image]:
    """Yield RGB frames resized for simulation/export."""

    with Image.open(path) as image:
        for idx, frame in enumerate(ImageSequence.Iterator(image)):
            if max_frames is not None and idx >= max_frames:
                return
            rgb = frame.convert("RGB")
            if rgb.size != (pixel_size, pixel_size):
                rgb = rgb.resize((pixel_size, pixel_size), Image.Resampling.NEAREST)
            yield rgb.copy()
