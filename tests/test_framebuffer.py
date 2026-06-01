import pytest
from PIL import Image

from open_idotmatrix.exceptions import ProtocolError
from open_idotmatrix.framebuffer import MatrixFrame


def test_matrix_frame_pixel_diff_and_solid_color():
    previous = MatrixFrame(fill=(0, 0, 0))
    frame = previous.copy()

    frame[1, 2] = (10, 20, 30)

    assert frame[1, 2] == (10, 20, 30)
    assert frame.solid_color() is None
    diff = frame.diff(previous)
    assert len(diff) == 1
    assert (diff[0].x, diff[0].y, diff[0].color.as_tuple()) == (1, 2, (10, 20, 30))
    assert previous.solid_color() == (0, 0, 0)


def test_matrix_frame_image_roundtrip_resizes_to_matrix():
    image = Image.new("RGB", (64, 64), (1, 2, 3))
    image.putpixel((63, 63), (255, 0, 0))

    frame = MatrixFrame.from_image(image)

    assert frame.to_image().size == (32, 32)
    assert frame[0, 0] == (1, 2, 3)
    assert frame[31, 31] == (255, 0, 0)


def test_matrix_frame_validates_size_and_coordinates():
    with pytest.raises(ProtocolError):
        MatrixFrame(data=b"\x00")
    with pytest.raises(ProtocolError):
        MatrixFrame().set_pixel(32, 0, (0, 0, 0))
