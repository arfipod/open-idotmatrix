"""Text rendering helpers for iDotMatrix 32x32 text packets."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont

from .constants import TEXT_GLYPH_BYTES, TEXT_GLYPH_HEIGHT, TEXT_GLYPH_WIDTH, TEXT_SEPARATOR_32
from .exceptions import ProtocolError
from .types import Color

DEFAULT_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


def resolve_font(font_path: str | None = None, font_size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font if available, otherwise fall back to Pillow's default font."""

    if font_path:
        return ImageFont.truetype(font_path, font_size)
    for candidate in DEFAULT_FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, font_size)
    return ImageFont.load_default()


def render_char_image(
    char: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    width: int = TEXT_GLYPH_WIDTH,
    height: int = TEXT_GLYPH_HEIGHT,
) -> Image.Image:
    """Render one character to a centered 1-bit glyph image."""

    if len(char) != 1:
        raise ProtocolError("render_char_image expects exactly one character")
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), char, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2 - bbox[0]
    y = (height - text_height) // 2 - bbox[1]
    draw.text((x, y), char, fill=1, font=font)
    return image


def image_to_glyph_bytes(image: Image.Image) -> bytes:
    """Pack a 16x32 1-bit image to row-major little-endian bitmap bytes."""

    if image.size != (TEXT_GLYPH_WIDTH, TEXT_GLYPH_HEIGHT):
        raise ProtocolError(f"glyph image must be {TEXT_GLYPH_WIDTH}x{TEXT_GLYPH_HEIGHT}")
    image = image.convert("1")
    out = bytearray()
    for y in range(TEXT_GLYPH_HEIGHT):
        byte = 0
        bit_count = 0
        for x in range(TEXT_GLYPH_WIDTH):
            bit = 1 if image.getpixel((x, y)) else 0
            byte |= bit << bit_count
            bit_count += 1
            if bit_count == 8:
                out.append(byte)
                byte = 0
                bit_count = 0
        if bit_count:
            out.append(byte)
    if len(out) != TEXT_GLYPH_BYTES:
        raise ProtocolError(f"unexpected glyph byte length: {len(out)}")
    return bytes(out)


def glyph_bytes_to_grid(glyph_bytes: bytes | bytearray) -> list[list[int]]:
    """Decode one 64-byte 16x32 glyph bitmap into a 0/1 grid."""

    glyph_bytes = bytes(glyph_bytes)
    if len(glyph_bytes) != TEXT_GLYPH_BYTES:
        raise ProtocolError(f"glyph must be {TEXT_GLYPH_BYTES} bytes")
    grid: list[list[int]] = []
    idx = 0
    for _y in range(TEXT_GLYPH_HEIGHT):
        row: list[int] = []
        for _byte_index in range(TEXT_GLYPH_WIDTH // 8):
            value = glyph_bytes[idx]
            idx += 1
            for bit in range(8):
                row.append((value >> bit) & 1)
        grid.append(row)
    return grid


def render_text_bitmap_bytes(
    text: str,
    *,
    font_path: str | None = None,
    font_size: int = 24,
) -> bytes:
    """Render text to iDotMatrix 32x32 character bitmap blocks.

    The result is suitable for :func:`open_idotmatrix.protocol.build_text_packet`.
    """

    if not text:
        raise ProtocolError("text cannot be empty")
    font = resolve_font(font_path=font_path, font_size=font_size)
    out = bytearray()
    for char in text:
        glyph = image_to_glyph_bytes(render_char_image(char, font=font))
        out.extend(TEXT_SEPARATOR_32)
        out.extend(glyph)
    return bytes(out)


def split_text_bitmap_bytes(text_bitmaps: bytes | bytearray) -> list[bytes]:
    """Split concatenated text bitmap blocks into raw glyph byte strings."""

    data = bytes(text_bitmaps)
    block_len = len(TEXT_SEPARATOR_32) + TEXT_GLYPH_BYTES
    if len(data) % block_len != 0:
        raise ProtocolError("text bitmap stream has invalid length")
    glyphs: list[bytes] = []
    for i in range(0, len(data), block_len):
        block = data[i : i + block_len]
        if not block.startswith(TEXT_SEPARATOR_32):
            raise ProtocolError("missing text separator 05ffffff")
        glyphs.append(block[len(TEXT_SEPARATOR_32) :])
    return glyphs


def render_text_preview_image(
    text_or_bitmaps: str | bytes | bytearray,
    *,
    color: Color | Sequence[int] = (255, 255, 255),
    background: Color | Sequence[int] = (0, 0, 0),
    font_path: str | None = None,
    font_size: int = 24,
) -> Image.Image:
    """Render text or text bitmap blocks to a wide RGB preview image."""

    color = Color.parse(color)
    background = Color.parse(background)
    if isinstance(text_or_bitmaps, str):
        bitmaps = render_text_bitmap_bytes(text_or_bitmaps, font_path=font_path, font_size=font_size)
    else:
        bitmaps = bytes(text_or_bitmaps)
    glyphs = split_text_bitmap_bytes(bitmaps)
    image = Image.new("RGB", (TEXT_GLYPH_WIDTH * len(glyphs), TEXT_GLYPH_HEIGHT), background.as_tuple())
    for glyph_index, glyph in enumerate(glyphs):
        grid = glyph_bytes_to_grid(glyph)
        x_offset = glyph_index * TEXT_GLYPH_WIDTH
        for y, row in enumerate(grid):
            for x, bit in enumerate(row):
                if bit:
                    image.putpixel((x_offset + x, y), color.as_tuple())
    return image


def grids_to_ascii(grids: Iterable[list[list[int]]]) -> str:
    """Return a debugging ASCII representation of glyph grids."""

    chunks = []
    for grid in grids:
        chunks.append("\n".join("".join("#" if bit else "." for bit in row) for row in grid))
    return "\n\n".join(chunks)
