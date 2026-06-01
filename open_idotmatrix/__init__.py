"""open-idotmatrix: Linux-first control toolkit for iDotMatrix 32x32 BLE displays."""

from .constants import DEVICE_NAME_PREFIX, HEIGHT, NOTIFY_UUID, SERVICE_UUID, WIDTH, WRITE_UUID
from .device import OpenIDotMatrix
from .exceptions import (
    AckTimeoutError,
    DeviceNotFoundError,
    OpenIDotMatrixError,
    ProtocolError,
    TransportError,
)
from .framebuffer import MatrixFrame
from .profile import DeviceProfile
from .protocol import (
    build_fullscreen_color,
    build_gif_chunks,
    build_pixel,
    build_screen_off,
    build_screen_on,
    build_set_brightness,
    build_set_time,
    build_text_packet,
    parse_packet,
)
from .renderer import MatrixRenderer
from .session import SessionLogger
from .simulator import MatrixSimulator
from .types import (
    Color,
    GifTotalLengthMode,
    Pixel,
    Point,
    TextBackgroundMode,
    TextColorMode,
    TextMode,
    YearByteMode,
)

__version__ = "0.1.0"

__all__ = [
    "AckTimeoutError",
    "Color",
    "DEVICE_NAME_PREFIX",
    "DeviceNotFoundError",
    "GifTotalLengthMode",
    "HEIGHT",
    "DeviceProfile",
    "MatrixFrame",
    "MatrixRenderer",
    "MatrixSimulator",
    "NOTIFY_UUID",
    "OpenIDotMatrix",
    "OpenIDotMatrixError",
    "Pixel",
    "Point",
    "ProtocolError",
    "SERVICE_UUID",
    "SessionLogger",
    "TextBackgroundMode",
    "TextColorMode",
    "TextMode",
    "TransportError",
    "WIDTH",
    "WRITE_UUID",
    "YearByteMode",
    "build_fullscreen_color",
    "build_gif_chunks",
    "build_pixel",
    "build_screen_off",
    "build_screen_on",
    "build_set_brightness",
    "build_set_time",
    "build_text_packet",
    "parse_packet",
]
