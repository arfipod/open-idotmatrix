import zlib

from open_idotmatrix.constants import ACK_CHUNK_OK, ACK_UPLOAD_DONE, GIF_CHUNK_HEADER_SIZE
from open_idotmatrix.protocol import build_gif_chunks, expected_gif_ack_for_chunk, parse_packet
from open_idotmatrix.types import GifTotalLengthMode


def test_gif_chunking_include_headers():
    gif_bytes = b"GIF89a" + bytes(range(256)) * 20
    chunks = build_gif_chunks(gif_bytes, total_length_mode=GifTotalLengthMode.INCLUDE_HEADERS)
    assert len(chunks) == 2
    assert chunks[0].header[4] == 0
    assert chunks[1].header[4] == 2
    assert len(chunks[0].data) == 4096 + GIF_CHUNK_HEADER_SIZE
    assert int.from_bytes(chunks[0].header[9:13], "little") == zlib.crc32(gif_bytes) & 0xFFFFFFFF
    total = len(gif_bytes) + GIF_CHUNK_HEADER_SIZE * len(chunks)
    assert int.from_bytes(chunks[0].header[5:9], "little") == total
    assert parse_packet(chunks[0].data)["kind"] == "gif_chunk"


def test_gif_chunking_raw_payload_only():
    gif_bytes = b"GIF89a" + b"x" * 20
    chunks = build_gif_chunks(gif_bytes, total_length_mode=GifTotalLengthMode.RAW_PAYLOAD_ONLY)
    assert int.from_bytes(chunks[0].header[5:9], "little") == len(gif_bytes)


def test_expected_acks():
    assert expected_gif_ack_for_chunk(0, 2) == ACK_CHUNK_OK
    assert expected_gif_ack_for_chunk(1, 2) == ACK_UPLOAD_DONE
