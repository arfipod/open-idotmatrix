"""Small typed values used by the public API."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, IntEnum

from .constants import HEIGHT, WIDTH
from .exceptions import ProtocolError

RGBTuple = tuple[int, int, int]


@dataclass(frozen=True)
class Color:
    """RGB color with byte-range validation."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for name, value in (("r", self.r), ("g", self.g), ("b", self.b)):
            if not isinstance(value, int) or not 0 <= value <= 255:
                raise ProtocolError(f"color component {name} must be an integer in 0..255")

    def as_tuple(self) -> RGBTuple:
        return self.r, self.g, self.b

    def as_bytes(self) -> bytes:
        return bytes((self.r, self.g, self.b))

    @classmethod
    def parse(cls, value: Color | RGBTuple | Iterable[int]) -> Color:
        if isinstance(value, cls):
            return value
        items = tuple(value)
        if len(items) != 3:
            raise ProtocolError("color must contain exactly 3 components: r, g, b")
        return cls(int(items[0]), int(items[1]), int(items[2]))


@dataclass(frozen=True)
class Point:
    """Pixel coordinate for a 32x32 matrix."""

    x: int
    y: int

    def __post_init__(self) -> None:
        if not isinstance(self.x, int) or not 0 <= self.x < WIDTH:
            raise ProtocolError(f"x must be an integer in 0..{WIDTH - 1}")
        if not isinstance(self.y, int) or not 0 <= self.y < HEIGHT:
            raise ProtocolError(f"y must be an integer in 0..{HEIGHT - 1}")


@dataclass(frozen=True)
class Pixel:
    """One colored pixel."""

    x: int
    y: int
    color: Color

    @classmethod
    def parse(cls, x: int, y: int, color: Color | RGBTuple | Iterable[int]) -> Pixel:
        point = Point(x, y)
        return cls(point.x, point.y, Color.parse(color))


class TextMode(IntEnum):
    """Known text animation modes."""

    FIXED = 0
    SCROLL_LEFT_TO_RIGHT = 1
    SCROLL_RIGHT_TO_LEFT = 2
    SCROLL_UP = 3
    SCROLL_DOWN = 4
    STROBE = 5
    FADE = 6
    FALLING_BLOCKS = 7
    LASER = 8


class TextColorMode(IntEnum):
    """Known text color modes."""

    UNKNOWN_WHITE_OR_APP_DEFAULT = 0
    FIXED = 1
    GRADIENT_BLUE_RED = 2
    GRADIENT_PASTELS = 3
    GRADIENT_PINK_ORANGE = 4
    UNKNOWN_5 = 5


class TextBackgroundMode(IntEnum):
    """Known text background modes."""

    OFF = 0
    SOLID = 1


class YearByteMode(str, Enum):
    """How to encode the year byte in the time packet.

    Different public implementations disagree here. ``LOW_BYTE`` follows the
    observed 8none1 packet notes: year & 0xff. ``TWO_DIGIT`` follows a later
    Python library implementation: year % 100.
    """

    LOW_BYTE = "low_byte"
    TWO_DIGIT = "two_digit"


class GifTotalLengthMode(str, Enum):
    """How to fill bytes 5..8 of the GIF upload header.

    Public packet notes suggest including all 16-byte GIF chunk headers in the
    total. Another implementation uses the raw GIF byte length. Both are kept
    to make hardware experiments explicit and reproducible.
    """

    INCLUDE_HEADERS = "include_headers"
    RAW_PAYLOAD_ONLY = "raw_payload_only"


class GifAckPolicy(str, Enum):
    """How strictly to wait for GIF/image upload ACK notifications."""

    EXACT = "exact"
    OK_OR_DONE = "ok_or_done"
    WAIT_DONE_AFTER_FINAL = "wait_done_after_final"
    NONE = "none"
