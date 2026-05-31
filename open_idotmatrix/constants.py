"""Protocol constants for iDotMatrix-compatible BLE pixel displays."""

DEVICE_NAME_PREFIX = "IDM-"

# Primary BLE UUIDs observed on iDotMatrix 32x32 devices.
SERVICE_UUID = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fa02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fa03-0000-1000-8000-00805f9b34fb"

# 32x32 display geometry.
WIDTH = 32
HEIGHT = 32
PIXEL_COUNT = WIDTH * HEIGHT

# Text glyph format used by the 32x32 display: each character is a 16x32 bitmap.
TEXT_GLYPH_WIDTH = 16
TEXT_GLYPH_HEIGHT = 32
TEXT_GLYPH_BYTES = TEXT_GLYPH_WIDTH * TEXT_GLYPH_HEIGHT // 8
TEXT_SEPARATOR_32 = b"\x05\xff\xff\xff"

# GIF upload chunking. The protocol-level chunk is 4096 bytes plus a 16-byte header.
GIF_PAYLOAD_CHUNK_SIZE = 4096
GIF_CHUNK_HEADER_SIZE = 16

# Notifications observed during GIF/image upload.
ACK_CHUNK_OK = bytes.fromhex("05 00 01 00 01")
ACK_UPLOAD_DONE = bytes.fromhex("05 00 01 00 03")
