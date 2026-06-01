"""Small playable 32x32 games rendered as MatrixFrame objects."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .constants import HEIGHT, WIDTH
from .framebuffer import MatrixFrame
from .types import RGBTuple


class MatrixGame(Protocol):
    name: str

    def reset(self) -> None: ...

    def tick(self) -> MatrixFrame: ...

    def control(self, action: str) -> None: ...


def available_game_names() -> tuple[str, ...]:
    return ("flappy", "tetris", "space_invaders")


def create_game(name: str, *, seed: int | None = None) -> MatrixGame:
    if name == "flappy":
        return FlappyBirdGame(seed=seed)
    if name == "tetris":
        return TetrisGame(seed=seed)
    if name == "space_invaders":
        return SpaceInvadersGame(seed=seed)
    raise ValueError(f"unknown game: {name}")


def _draw_rect(frame: MatrixFrame, x: int, y: int, w: int, h: int, color: RGBTuple) -> None:
    for yy in range(max(0, y), min(HEIGHT, y + h)):
        for xx in range(max(0, x), min(WIDTH, x + w)):
            frame[xx, yy] = color


@dataclass
class Pipe:
    x: int
    gap_y: int


class FlappyBirdGame:
    name = "flappy"

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.bird_x = 7
        self.bird_y = 15.0
        self.velocity = 0.0
        self.pipes: list[Pipe] = []
        self.score = 0
        self.dead_ticks = 0
        self._spawn_pipe(34)

    def control(self, action: str) -> None:
        if action == "flap":
            if self.dead_ticks:
                self.reset()
            else:
                self.velocity = -2.2

    def tick(self) -> MatrixFrame:
        if self.dead_ticks:
            self.dead_ticks -= 1
            if self.dead_ticks == 0:
                self.reset()
            return self.to_frame()

        self.velocity = min(2.4, self.velocity + 0.34)
        self.bird_y += self.velocity
        for pipe in self.pipes:
            pipe.x -= 1
        self.pipes = [pipe for pipe in self.pipes if pipe.x > -4]
        if not self.pipes or self.pipes[-1].x < 18:
            self._spawn_pipe(34)
        for pipe in self.pipes:
            if pipe.x + 3 == self.bird_x:
                self.score += 1
        if self._collides():
            self.dead_ticks = 12
        return self.to_frame()

    def _spawn_pipe(self, x: int) -> None:
        self.pipes.append(Pipe(x=x, gap_y=self.rng.randint(7, 21)))

    def _collides(self) -> bool:
        bird_y = round(self.bird_y)
        if bird_y < 0 or bird_y >= HEIGHT - 2:
            return True
        for pipe in self.pipes:
            if pipe.x <= self.bird_x <= pipe.x + 2 and not pipe.gap_y - 4 <= bird_y <= pipe.gap_y + 4:
                return True
        return False

    def to_frame(self) -> MatrixFrame:
        frame = MatrixFrame(fill=(0, 8, 24))
        _draw_rect(frame, 0, HEIGHT - 2, WIDTH, 2, (40, 110, 40))
        for pipe in self.pipes:
            _draw_rect(frame, pipe.x, 0, 3, pipe.gap_y - 4, (0, 180, 70))
            _draw_rect(frame, pipe.x, pipe.gap_y + 5, 3, HEIGHT - pipe.gap_y - 7, (0, 180, 70))
        bird_color = (255, 40, 40) if self.dead_ticks else (255, 220, 0)
        _draw_rect(frame, self.bird_x, round(self.bird_y), 2, 2, bird_color)
        return frame


PIECES = {
    "I": (((0, 1), (1, 1), (2, 1), (3, 1)), ((2, 0), (2, 1), (2, 2), (2, 3))),
    "O": (((1, 0), (2, 0), (1, 1), (2, 1)),),
    "T": (((1, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (2, 1), (1, 2)), ((0, 1), (1, 1), (2, 1), (1, 2)), ((1, 0), (0, 1), (1, 1), (1, 2))),
    "S": (((1, 0), (2, 0), (0, 1), (1, 1)), ((1, 0), (1, 1), (2, 1), (2, 2))),
    "Z": (((0, 0), (1, 0), (1, 1), (2, 1)), ((2, 0), (1, 1), (2, 1), (1, 2))),
    "J": (((0, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (2, 0), (1, 1), (1, 2)), ((0, 1), (1, 1), (2, 1), (2, 2)), ((1, 0), (1, 1), (0, 2), (1, 2))),
    "L": (((2, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (1, 2), (2, 2)), ((0, 1), (1, 1), (2, 1), (0, 2)), ((0, 0), (1, 0), (1, 1), (1, 2))),
}

PIECE_COLORS: dict[str, RGBTuple] = {
    "I": (0, 220, 220),
    "O": (240, 220, 0),
    "T": (160, 60, 240),
    "S": (0, 220, 80),
    "Z": (240, 50, 50),
    "J": (40, 80, 240),
    "L": (255, 140, 20),
}


class TetrisGame:
    name = "tetris"
    board_w = 10
    board_h = 20
    offset_x = 11
    offset_y = 6

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.board: list[list[RGBTuple | None]] = [[None for _x in range(self.board_w)] for _y in range(self.board_h)]
        self.game_over_ticks = 0
        self._spawn()

    def control(self, action: str) -> None:
        if action == "left":
            self._try_move(-1, 0)
        elif action == "right":
            self._try_move(1, 0)
        elif action == "down":
            self._try_move(0, 1)
        elif action == "rotate":
            self._try_rotate()
        elif action == "drop":
            while self._try_move(0, 1):
                pass
            self._lock_piece()
        elif action == "reset":
            self.reset()

    def tick(self) -> MatrixFrame:
        if self.game_over_ticks:
            self.game_over_ticks -= 1
            if self.game_over_ticks == 0:
                self.reset()
            return self.to_frame()
        if not self._try_move(0, 1):
            self._lock_piece()
        return self.to_frame()

    def _spawn(self) -> None:
        self.piece = self.rng.choice(tuple(PIECES))
        self.rotation = 0
        self.piece_x = 3
        self.piece_y = 0
        if self._collides(self.piece_x, self.piece_y, self.rotation):
            self.game_over_ticks = 16

    def _piece_cells(self, x: int | None = None, y: int | None = None, rotation: int | None = None):
        x = self.piece_x if x is None else x
        y = self.piece_y if y is None else y
        rotations = PIECES[self.piece]
        rotation = self.rotation if rotation is None else rotation % len(rotations)
        for cx, cy in rotations[rotation]:
            yield x + cx, y + cy

    def _collides(self, x: int, y: int, rotation: int) -> bool:
        for cx, cy in self._piece_cells(x, y, rotation):
            if cx < 0 or cx >= self.board_w or cy >= self.board_h:
                return True
            if cy >= 0 and self.board[cy][cx] is not None:
                return True
        return False

    def _try_move(self, dx: int, dy: int) -> bool:
        nx = self.piece_x + dx
        ny = self.piece_y + dy
        if self._collides(nx, ny, self.rotation):
            return False
        self.piece_x = nx
        self.piece_y = ny
        return True

    def _try_rotate(self) -> None:
        next_rotation = (self.rotation + 1) % len(PIECES[self.piece])
        for kick in (0, -1, 1, -2, 2):
            if not self._collides(self.piece_x + kick, self.piece_y, next_rotation):
                self.piece_x += kick
                self.rotation = next_rotation
                return

    def _lock_piece(self) -> None:
        color = PIECE_COLORS[self.piece]
        for x, y in self._piece_cells():
            if 0 <= y < self.board_h:
                self.board[y][x] = color
        self._clear_lines()
        self._spawn()

    def _clear_lines(self) -> None:
        kept = [row for row in self.board if any(cell is None for cell in row)]
        cleared = self.board_h - len(kept)
        self.board = [[None for _x in range(self.board_w)] for _y in range(cleared)] + kept

    def to_frame(self) -> MatrixFrame:
        frame = MatrixFrame(fill=(0, 0, 0))
        border = (35, 35, 45)
        _draw_rect(frame, self.offset_x - 1, self.offset_y - 1, self.board_w + 2, 1, border)
        _draw_rect(frame, self.offset_x - 1, self.offset_y + self.board_h, self.board_w + 2, 1, border)
        _draw_rect(frame, self.offset_x - 1, self.offset_y - 1, 1, self.board_h + 2, border)
        _draw_rect(frame, self.offset_x + self.board_w, self.offset_y - 1, 1, self.board_h + 2, border)
        for y, row in enumerate(self.board):
            for x, color in enumerate(row):
                if color is not None:
                    frame[self.offset_x + x, self.offset_y + y] = color
        color = (255, 255, 255) if self.game_over_ticks else PIECE_COLORS[self.piece]
        for x, y in self._piece_cells():
            if 0 <= x < self.board_w and 0 <= y < self.board_h:
                frame[self.offset_x + x, self.offset_y + y] = color
        return frame


class SpaceInvadersGame:
    name = "space_invaders"

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.player_x = WIDTH // 2
        self.player_cooldown = 0
        self.bullets: list[tuple[int, int]] = []
        self.enemy_bullets: list[tuple[int, int]] = []
        self.aliens = {(x, y) for y in (4, 7, 10) for x in range(5, 27, 4)}
        self.direction = 1
        self.tick_count = 0
        self.dead_ticks = 0

    def control(self, action: str) -> None:
        if action == "left":
            self.player_x = max(1, self.player_x - 2)
        elif action == "right":
            self.player_x = min(WIDTH - 2, self.player_x + 2)
        elif action == "fire" and self.player_cooldown == 0 and not self.dead_ticks:
            self.bullets.append((self.player_x, HEIGHT - 5))
            self.player_cooldown = 4
        elif action == "reset":
            self.reset()

    def tick(self) -> MatrixFrame:
        if self.dead_ticks:
            self.dead_ticks -= 1
            if self.dead_ticks == 0:
                self.reset()
            return self.to_frame()

        self.tick_count += 1
        self.player_cooldown = max(0, self.player_cooldown - 1)
        self.bullets = [(x, y - 2) for x, y in self.bullets if y > 0]
        self.enemy_bullets = [(x, y + 1) for x, y in self.enemy_bullets if y < HEIGHT - 1]

        hit_aliens = set()
        remaining_bullets = []
        for bullet in self.bullets:
            bx, by = bullet
            hit = next((alien for alien in self.aliens if abs(alien[0] - bx) <= 1 and abs(alien[1] - by) <= 1), None)
            if hit is None:
                remaining_bullets.append(bullet)
            else:
                hit_aliens.add(hit)
        self.bullets = remaining_bullets
        self.aliens -= hit_aliens

        if self.tick_count % 4 == 0 and self.aliens:
            min_x = min(x for x, _y in self.aliens)
            max_x = max(x for x, _y in self.aliens)
            step_down = max_x + self.direction >= WIDTH - 2 or min_x + self.direction <= 1
            if step_down:
                self.direction *= -1
                self.aliens = {(x, y + 1) for x, y in self.aliens}
            else:
                self.aliens = {(x + self.direction, y) for x, y in self.aliens}

        if self.aliens and self.rng.random() < 0.12:
            shooters = sorted(self.aliens, key=lambda item: item[1], reverse=True)[:6]
            x, y = self.rng.choice(shooters)
            self.enemy_bullets.append((x, y + 2))

        if any(abs(x - self.player_x) <= 1 and y >= HEIGHT - 3 for x, y in self.enemy_bullets):
            self.dead_ticks = 18
        if not self.aliens:
            self.reset()
        elif any(y >= HEIGHT - 4 for _x, y in self.aliens):
            self.dead_ticks = 18
        return self.to_frame()

    def to_frame(self) -> MatrixFrame:
        frame = MatrixFrame(fill=(0, 0, 10))
        player_color = (255, 40, 40) if self.dead_ticks else (0, 220, 255)
        _draw_rect(frame, self.player_x - 1, HEIGHT - 3, 3, 2, player_color)
        for x, y in self.aliens:
            _draw_rect(frame, x - 1, y, 3, 2, (80, 255, 80))
        for x, y in self.bullets:
            frame[x, max(0, min(HEIGHT - 1, y))] = (255, 255, 80)
        for x, y in self.enemy_bullets:
            frame[x, max(0, min(HEIGHT - 1, y))] = (255, 80, 80)
        return frame


__all__ = [
    "FlappyBirdGame",
    "MatrixGame",
    "SpaceInvadersGame",
    "TetrisGame",
    "available_game_names",
    "create_game",
]
