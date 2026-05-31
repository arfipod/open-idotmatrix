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


def matrix_image_from_file(path: str | Path, *, pixel_size: int = WIDTH) -> Image.Image:
    """Load any Pillow-supported image and deform it to pixel_size x pixel_size.

    The resize intentionally does not preserve aspect ratio: the source image is
    stretched or squashed to a square, then nearest-neighbor sampled to preserve
    LED-like hard pixels.
    """

    if pixel_size <= 0:
        raise ProtocolError("pixel_size must be positive")

    with Image.open(path) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGBA")
        if frame.size != (pixel_size, pixel_size):
            frame = frame.resize((pixel_size, pixel_size), Image.Resampling.NEAREST)
        background = Image.new("RGBA", frame.size, (0, 0, 0, 255))
        background.alpha_composite(frame)
        return background.convert("RGB")


def process_image_bytes(path: str | Path, *, pixel_size: int = WIDTH) -> bytes:
    """Convert any Pillow-supported image into a single-frame 32x32 GIF."""

    image = matrix_image_from_file(path, pixel_size=pixel_size)
    buffer = io.BytesIO()
    image.convert("P", palette=Image.Palette.ADAPTIVE).save(buffer, format="GIF")
    return buffer.getvalue()


def save_matrix_image_preview(
    path: str | Path,
    out_path: str | Path,
    *,
    pixel_size: int = WIDTH,
    scale: int = 16,
    grid: bool = True,
) -> Path:
    """Save a scaled preview of the square 32x32 nearest-neighbor conversion."""

    if scale <= 0:
        raise ProtocolError("scale must be positive")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image = matrix_image_from_file(path, pixel_size=pixel_size)
    preview = image.resize((pixel_size * scale, pixel_size * scale), Image.Resampling.NEAREST)
    if grid and scale >= 6:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(preview)
        width, height = preview.size
        for x in range(0, width + 1, scale):
            draw.line((x, 0, x, height), fill=(40, 40, 40))
        for y in range(0, height + 1, scale):
            draw.line((0, y, width, y), fill=(40, 40, 40))
    preview.save(out_path)
    return out_path


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


def image_chunks_from_file(
    path: str | Path,
    *,
    pixel_size: int = WIDTH,
    total_length_mode: GifTotalLengthMode = GifTotalLengthMode.INCLUDE_HEADERS,
) -> list[GifChunk]:
    """Convert any image to a 32x32 single-frame GIF and return upload chunks."""

    gif_bytes = process_image_bytes(path, pixel_size=pixel_size)
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
