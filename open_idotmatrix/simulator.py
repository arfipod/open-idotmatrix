"""Pillow-based 32x32 iDotMatrix simulator.

The simulator is intentionally simple: it understands the packet builders in
this project and renders an approximate preview of what the physical matrix
should show.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw

from .constants import HEIGHT, WIDTH
from .exceptions import ProtocolError
from .gif import first_frame_image, frame_images
from .protocol import inspect_text_packet, parse_packet
from .text import render_text_bitmap_bytes, render_text_preview_image, split_text_bitmap_bytes
from .types import Color

_BLACK = (0, 0, 0)


@dataclass
class MatrixSimulator:
    """In-memory 32x32 RGB matrix with Pillow rendering."""

    width: int = WIDTH
    height: int = HEIGHT
    pixels: list[list[tuple[int, int, int]]] = field(default_factory=list)
    screen_on: bool = True
    brightness: int = 100

    def __post_init__(self) -> None:
        if not self.pixels:
            self.clear()

    def clear(self, color: Color | Sequence[int] = _BLACK) -> None:
        color = Color.parse(color).as_tuple()
        self.pixels = [[color for _x in range(self.width)] for _y in range(self.height)]

    def fill(self, color: Color | Sequence[int]) -> None:
        self.clear(color)

    def set_pixel(self, x: int, y: int, color: Color | Sequence[int]) -> None:
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ProtocolError(f"pixel coordinate out of range: ({x}, {y})")
        self.pixels[y][x] = Color.parse(color).as_tuple()

    def from_image(self, image: Image.Image) -> None:
        image = image.convert("RGB")
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.Resampling.NEAREST)
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = image.getpixel((x, y))

    def to_image(self, *, scale: int = 1, grid: bool = False) -> Image.Image:
        image = Image.new("RGB", (self.width, self.height), _BLACK)
        if self.screen_on:
            for y, row in enumerate(self.pixels):
                for x, color in enumerate(row):
                    if self.brightness < 100:
                        factor = max(0, min(100, self.brightness)) / 100.0
                        color = tuple(int(c * factor) for c in color)
                    image.putpixel((x, y), color)
        if scale > 1:
            image = image.resize((self.width * scale, self.height * scale), Image.Resampling.NEAREST)
        if grid and scale >= 6:
            draw = ImageDraw.Draw(image)
            w, h = image.size
            for x in range(0, w + 1, scale):
                draw.line((x, 0, x, h), fill=(40, 40, 40))
            for y in range(0, h + 1, scale):
                draw.line((0, y, w, y), fill=(40, 40, 40))
        return image

    def save(self, path: str | Path, *, scale: int = 16, grid: bool = True) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.to_image(scale=scale, grid=grid).save(path)
        return path

    def show(self, *, scale: int = 16, grid: bool = True) -> None:
        self.to_image(scale=scale, grid=grid).show()

    def apply_packet(self, packet: bytes | bytearray, *, text_scroll_offset: int = 0) -> dict:
        """Apply one known protocol packet to the simulated matrix."""

        packet = bytes(packet)
        info = parse_packet(packet)
        kind = info.get("kind")
        if kind == "screen_on":
            self.screen_on = True
        elif kind == "screen_off":
            self.screen_on = False
        elif kind == "brightness":
            self.brightness = int(info["brightness"])
        elif kind == "fullscreen_color":
            self.fill(info["color"])
        elif kind == "pixel":
            self.set_pixel(int(info["x"]), int(info["y"]), info["color"])
        elif kind == "text":
            self.apply_text_packet(packet, scroll_offset=text_scroll_offset)
        return info

    def apply_packets(self, packets: Iterable[bytes | bytearray]) -> list[dict]:
        return [self.apply_packet(packet) for packet in packets]

    def apply_text_packet(self, packet: bytes | bytearray, *, scroll_offset: int = 0) -> None:
        """Render a text packet to a 32x32 frame.

        This is an approximation. For scrolling modes it renders the current
        scroll offset over a virtual wide strip.
        """

        packet = bytes(packet)
        inspect_text_packet(packet)
        payload = packet[16:]
        metadata = payload[:14]
        bitmaps = payload[14:]
        num_chars = int.from_bytes(metadata[0:2], "little")
        if num_chars != len(split_text_bitmap_bytes(bitmaps)):
            raise ProtocolError("text packet num_chars does not match bitmap stream")
        text_mode = metadata[4]
        color = (metadata[7], metadata[8], metadata[9])
        bg_mode = metadata[10]
        background = (metadata[11], metadata[12], metadata[13]) if bg_mode == 1 else _BLACK
        strip = render_text_preview_image(bitmaps, color=color, background=background)
        frame = Image.new("RGB", (self.width, self.height), background)
        if strip.width <= self.width:
            frame.paste(strip, (0, 0))
        elif text_mode in (1, 2, 3, 4, 5, 6, 7, 8):
            if text_mode == 2:
                offset = (-scroll_offset) % strip.width
            else:
                offset = scroll_offset % strip.width
            for x in range(self.width):
                src_x = (x + offset) % strip.width
                for y in range(self.height):
                    frame.putpixel((x, y), strip.getpixel((src_x, y)))
        else:
            frame.paste(strip.crop((0, 0, self.width, self.height)), (0, 0))
        self.from_image(frame)

    def load_gif_preview(self, path: str | Path) -> None:
        self.from_image(first_frame_image(path, pixel_size=self.width))


def simulate_text_frame(
    text: str,
    *,
    offset: int = 0,
    color: Color | Sequence[int] = (255, 255, 255),
    background: Color | Sequence[int] = _BLACK,
    font_path: str | None = None,
    font_size: int = 24,
) -> MatrixSimulator:
    """Build a simulator frame directly from a text string."""

    sim = MatrixSimulator()
    bitmaps = render_text_bitmap_bytes(text, font_path=font_path, font_size=font_size)
    strip = render_text_preview_image(bitmaps, color=color, background=background)
    frame = Image.new("RGB", (WIDTH, HEIGHT), Color.parse(background).as_tuple())
    for x in range(WIDTH):
        src_x = (x + offset) % strip.width
        for y in range(HEIGHT):
            frame.putpixel((x, y), strip.getpixel((src_x, y)))
    sim.from_image(frame)
    return sim


def save_text_animation(
    text: str,
    path: str | Path,
    *,
    frames: int = 64,
    scale: int = 16,
    duration: int = 80,
    color: Color | Sequence[int] = (255, 255, 255),
    background: Color | Sequence[int] = _BLACK,
    font_path: str | None = None,
    font_size: int = 24,
) -> Path:
    """Save an animated GIF preview of a scrolling text frame."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    images = []
    for offset in range(frames):
        sim = simulate_text_frame(
            text,
            offset=offset,
            color=color,
            background=background,
            font_path=font_path,
            font_size=font_size,
        )
        images.append(sim.to_image(scale=scale, grid=False))
    images[0].save(path, save_all=True, append_images=images[1:], duration=duration, loop=0)
    return path


def save_gif_preview_frames(path: str | Path, out_dir: str | Path, *, scale: int = 16, max_frames: int = 16) -> list[Path]:
    """Export several preview frames from a GIF/image for inspection."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for idx, frame in enumerate(frame_images(path, max_frames=max_frames)):
        sim = MatrixSimulator()
        sim.from_image(frame)
        out = out_dir / f"frame_{idx:03d}.png"
        sim.save(out, scale=scale, grid=True)
        saved.append(out)
    return saved
