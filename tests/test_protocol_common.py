from datetime import datetime

import pytest

from open_idotmatrix.exceptions import ProtocolError
from open_idotmatrix.protocol import (
    build_chronograph,
    build_clock_mode,
    build_countdown,
    build_delete_device_data,
    build_eco_mode,
    build_effect,
    build_flip_screen,
    build_freeze_screen,
    build_fullscreen_color,
    build_pixel,
    build_scoreboard,
    build_screen_off,
    build_screen_on,
    build_set_brightness,
    build_set_time,
    parse_packet,
)
from open_idotmatrix.types import YearByteMode


def test_basic_packets_are_exact():
    assert build_screen_on() == bytes.fromhex("05 00 07 01 01")
    assert build_screen_off() == bytes.fromhex("05 00 07 01 00")
    assert build_set_brightness(80) == bytes.fromhex("05 00 04 80 50")
    assert build_fullscreen_color((255, 0, 0)) == bytes.fromhex("07 00 02 02 ff 00 00")
    assert build_pixel(31, 31, (255, 0, 0)) == bytes.fromhex("0a 00 05 01 00 ff 00 00 1f 1f")


def test_set_time_year_modes():
    dt = datetime(2026, 5, 31, 12, 34, 56)
    low = build_set_time(dt, year_mode=YearByteMode.LOW_BYTE)
    two = build_set_time(dt, year_mode=YearByteMode.TWO_DIGIT)
    assert low == bytes((0x0B, 0x00, 0x01, 0x80, 2026 & 0xFF, 5, 31, 7, 12, 34, 56))
    assert two == bytes((0x0B, 0x00, 0x01, 0x80, 26, 5, 31, 7, 12, 34, 56))


def test_parse_known_packets():
    assert parse_packet(build_screen_on())["kind"] == "screen_on"
    assert parse_packet(build_set_brightness(80)) == {
        "brightness": 80,
        "hex": "05 00 04 80 50",
        "kind": "brightness",
        "length": 5,
    }
    assert parse_packet(build_freeze_screen())["kind"] == "freeze_screen"
    assert parse_packet(build_flip_screen(True))["kind"] == "flip_screen"
    assert parse_packet(build_fullscreen_color((1, 2, 3)))["color"] == (1, 2, 3)
    assert parse_packet(build_pixel(1, 2, (3, 4, 5)))["kind"] == "pixel"
    assert parse_packet(build_clock_mode(1))["kind"] == "clock"
    assert parse_packet(build_chronograph(2))["kind"] == "chronograph"
    assert parse_packet(build_countdown(1, 2, 3))["kind"] == "countdown"
    assert parse_packet(build_scoreboard(12, 34))["score_right"] == 34
    assert parse_packet(build_eco_mode(1, 22, 0, 7, 30, 20))["kind"] == "eco"
    assert parse_packet(build_effect(1, [(255, 0, 0), (0, 255, 0)]))["color_count"] == 2
    assert parse_packet(build_delete_device_data())["kind"] == "delete_device_data"


def test_validation():
    with pytest.raises(ProtocolError):
        build_set_brightness(4)
    with pytest.raises(ProtocolError):
        build_pixel(32, 0, (255, 0, 0))
    with pytest.raises(ProtocolError):
        build_fullscreen_color((0, 0, 300))
