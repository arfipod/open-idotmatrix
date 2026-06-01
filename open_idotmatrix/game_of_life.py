"""Conway's Game of Life demo for 32x32 matrix rendering."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from PIL import Image

from .constants import HEIGHT, WIDTH
from .framebuffer import MatrixFrame
from .renderer import MatrixRenderer
from .types import Color, RGBTuple

PatternName = str


_PATTERNS: dict[PatternName, tuple[tuple[int, int], ...]] = {
    "glider": ((1, 0), (2, 1), (0, 2), (1, 2), (2, 2)),
    "blinker": ((0, 1), (1, 1), (2, 1)),
    "toad": ((1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2)),
    "beacon": ((0, 0), (1, 0), (0, 1), (3, 2), (2, 3), (3, 3)),
    "pulsar": (
        (2, 0),
        (3, 0),
        (4, 0),
        (8, 0),
        (9, 0),
        (10, 0),
        (0, 2),
        (5, 2),
        (7, 2),
        (12, 2),
        (0, 3),
        (5, 3),
        (7, 3),
        (12, 3),
        (0, 4),
        (5, 4),
        (7, 4),
        (12, 4),
        (2, 5),
        (3, 5),
        (4, 5),
        (8, 5),
        (9, 5),
        (10, 5),
        (2, 7),
        (3, 7),
        (4, 7),
        (8, 7),
        (9, 7),
        (10, 7),
        (0, 8),
        (5, 8),
        (7, 8),
        (12, 8),
        (0, 9),
        (5, 9),
        (7, 9),
        (12, 9),
        (0, 10),
        (5, 10),
        (7, 10),
        (12, 10),
        (2, 12),
        (3, 12),
        (4, 12),
        (8, 12),
        (9, 12),
        (10, 12),
    ),
    "acorn": ((0, 2), (1, 0), (1, 2), (3, 1), (4, 2), (5, 2), (6, 2)),
}


@dataclass(frozen=True)
class LifeStats:
    generations: int
    alive: int
    elapsed_seconds: float
    frames_per_second: float


class GameOfLife:
    """32x32 Conway's Game of Life state and rendering helpers."""

    width = WIDTH
    height = HEIGHT

    def __init__(self, alive: set[tuple[int, int]] | None = None, *, wrap: bool = True) -> None:
        self.wrap = wrap
        self.alive: set[tuple[int, int]] = alive or set()

    @classmethod
    def random(
        cls,
        *,
        density: float = 0.28,
        seed: int | None = None,
        wrap: bool = True,
    ) -> GameOfLife:
        if not 0.0 <= density <= 1.0:
            raise ValueError("density must be in 0.0..1.0")
        rng = random.Random(seed)
        alive = {
            (x, y)
            for y in range(HEIGHT)
            for x in range(WIDTH)
            if rng.random() < density
        }
        return cls(alive, wrap=wrap)

    @classmethod
    def pattern(
        cls,
        name: PatternName,
        *,
        offset: tuple[int, int] | None = None,
        wrap: bool = True,
    ) -> GameOfLife:
        points = _PATTERNS[name]
        if offset is None:
            max_x = max(x for x, _y in points)
            max_y = max(y for _x, y in points)
            offset = ((WIDTH - max_x - 1) // 2, (HEIGHT - max_y - 1) // 2)
        ox, oy = offset
        alive = {((x + ox) % WIDTH, (y + oy) % HEIGHT) for x, y in points}
        return cls(alive, wrap=wrap)

    @classmethod
    def seed(
        cls,
        name: PatternName,
        *,
        density: float = 0.28,
        random_seed: int | None = None,
        wrap: bool = True,
    ) -> GameOfLife:
        if name == "random":
            return cls.random(density=density, seed=random_seed, wrap=wrap)
        return cls.pattern(name, wrap=wrap)

    @staticmethod
    def pattern_names() -> tuple[str, ...]:
        return ("random", *sorted(_PATTERNS))

    def step(self) -> None:
        counts: dict[tuple[int, int], int] = {}
        for x, y in self.alive:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if self.wrap:
                        nx %= WIDTH
                        ny %= HEIGHT
                    elif not (0 <= nx < WIDTH and 0 <= ny < HEIGHT):
                        continue
                    counts[(nx, ny)] = counts.get((nx, ny), 0) + 1
        self.alive = {
            point
            for point, count in counts.items()
            if count == 3 or (count == 2 and point in self.alive)
        }

    def to_frame(
        self,
        *,
        alive_color: Color | RGBTuple = (0, 255, 80),
        dead_color: Color | RGBTuple = (0, 0, 0),
    ) -> MatrixFrame:
        alive = Color.parse(alive_color).as_tuple()
        frame = MatrixFrame(fill=dead_color)
        for x, y in self.alive:
            frame[x, y] = alive
        return frame


async def run_life_hardware(
    device,
    *,
    seed: PatternName = "random",
    generations: int = 200,
    fps: float = 12.0,
    density: float = 0.28,
    random_seed: int | None = None,
    wrap: bool = True,
    alive_color: Color | RGBTuple = (0, 255, 80),
    dead_color: Color | RGBTuple = (0, 0, 0),
    max_pixel_updates: int = WIDTH * HEIGHT,
    clear_first: bool = True,
) -> LifeStats:
    game = GameOfLife.seed(seed, density=density, random_seed=random_seed, wrap=wrap)
    renderer = MatrixRenderer(device, strategy="pixels", max_pixel_updates=max_pixel_updates)
    if clear_first:
        await device.fill(dead_color)
        renderer.previous_frame = MatrixFrame(fill=dead_color)
    delay = 1.0 / fps if fps > 0 else 0.0
    rendered = 0
    started = perf_counter()
    while generations <= 0 or rendered < generations:
        frame_started = perf_counter()
        await renderer.show(game.to_frame(alive_color=alive_color, dead_color=dead_color))
        rendered += 1
        game.step()
        if delay:
            sleep_for = delay - (perf_counter() - frame_started)
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
    elapsed = perf_counter() - started
    actual_fps = rendered / elapsed if elapsed else 0.0
    return LifeStats(rendered, len(game.alive), elapsed, actual_fps)


def render_life_preview(
    path: str | Path,
    *,
    seed: PatternName = "random",
    generations: int = 120,
    fps: float = 12.0,
    density: float = 0.28,
    random_seed: int | None = None,
    wrap: bool = True,
    alive_color: Color | RGBTuple = (0, 255, 80),
    dead_color: Color | RGBTuple = (0, 0, 0),
    scale: int = 16,
) -> Path:
    if generations <= 0:
        raise ValueError("preview generations must be positive")
    if scale <= 0:
        raise ValueError("scale must be positive")
    game = GameOfLife.seed(seed, density=density, random_seed=random_seed, wrap=wrap)
    images: list[Image.Image] = []
    for _index in range(generations):
        image = game.to_frame(alive_color=alive_color, dead_color=dead_color).to_image()
        if scale > 1:
            image = image.resize((WIDTH * scale, HEIGHT * scale), Image.Resampling.NEAREST)
        images.append(image)
        game.step()
    duration = max(1, int(1000 / fps)) if fps > 0 else 1
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(out_path, save_all=True, append_images=images[1:], duration=duration, loop=0)
    return out_path


__all__ = ["GameOfLife", "LifeStats", "render_life_preview", "run_life_hardware"]
