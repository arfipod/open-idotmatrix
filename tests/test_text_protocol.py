import zlib

from open_idotmatrix.constants import TEXT_SEPARATOR_32
from open_idotmatrix.protocol import build_text_packet, inspect_text_packet, parse_packet
from open_idotmatrix.text import render_text_bitmap_bytes, split_text_bitmap_bytes


def test_render_text_bitmap_shape():
    bitmaps = render_text_bitmap_bytes("AB")
    glyphs = split_text_bitmap_bytes(bitmaps)
    assert len(glyphs) == 2
    assert bitmaps.count(TEXT_SEPARATOR_32) == 2
    assert len(glyphs[0]) == 64


def test_text_packet_lengths_and_crc():
    bitmaps = render_text_bitmap_bytes("A")
    packet = build_text_packet(bitmaps, text_color=(255, 0, 0))
    assert packet[2:5] == bytes.fromhex("03 00 00")
    assert packet[15] == 0x0C
    assert int.from_bytes(packet[0:2], "little") == len(packet)
    assert int.from_bytes(packet[5:9], "little") == len(packet) - 16
    expected_crc = int.from_bytes(packet[9:13], "little")
    assert expected_crc == zlib.crc32(packet[16:]) & 0xFFFFFFFF
    info = inspect_text_packet(packet)
    assert info.num_chars == 1
    parsed = parse_packet(packet)
    assert parsed["kind"] == "text"
    assert parsed["crc32_ok"] is True
