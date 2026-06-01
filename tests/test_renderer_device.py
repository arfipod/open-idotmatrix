import pytest

from open_idotmatrix.device import OpenIDotMatrix
from open_idotmatrix.framebuffer import MatrixFrame
from open_idotmatrix.profile import DeviceProfile
from open_idotmatrix.renderer import MatrixRenderer
from open_idotmatrix.types import Pixel


class FakeTransport:
    def __init__(self):
        self.writes = []
        self.packet_batches = []

    async def write(self, data, *, response=False):
        self.writes.append((bytes(data), response))

    async def write_many_packets(self, packets, *, response=False, inter_packet_delay=0.0, concatenate=False):
        self.packet_batches.append(
            {
                "packets": [bytes(packet) for packet in packets],
                "response": response,
                "inter_packet_delay": inter_packet_delay,
                "concatenate": concatenate,
            }
        )


class FakeDevice:
    def __init__(self):
        self.fills = []
        self.pixel_batches = []
        self.frames = []

    async def fill(self, color):
        self.fills.append(tuple(color))
        return {"kind": "fullscreen_color"}

    async def pixels_fast(self, pixels, *, parse=False):
        self.pixel_batches.append(list(pixels))
        return []

    async def frame(self, frame, **kwargs):
        self.frames.append((frame.copy(), kwargs))
        return [{"kind": "gif_chunk"}]


@pytest.mark.asyncio
async def test_pixels_fast_uses_transport_batch_path():
    transport = FakeTransport()
    matrix = OpenIDotMatrix(
        transport=transport,
        profile=DeviceProfile(write_response=True, pixel_batch_mode="concatenate"),
    )

    result = await matrix.pixels_fast(
        [Pixel.parse(0, 0, (1, 2, 3)), Pixel.parse(31, 31, (4, 5, 6))],
        inter_packet_delay=0.25,
        parse=True,
    )

    assert [item["kind"] for item in result] == ["pixel", "pixel"]
    assert len(transport.packet_batches) == 1
    batch = transport.packet_batches[0]
    assert batch["response"] is True
    assert batch["inter_packet_delay"] == 0.25
    assert batch["concatenate"] is True
    assert len(batch["packets"]) == 2


@pytest.mark.asyncio
async def test_matrix_renderer_auto_strategy_fill_noop_pixels_and_image():
    device = FakeDevice()
    renderer = MatrixRenderer(device, max_pixel_updates=1, image_wait_for_ack=False)

    solid = MatrixFrame(fill=(1, 2, 3))
    assert (await renderer.show(solid))["strategy"] == "fill"
    assert device.fills == [(1, 2, 3)]

    assert (await renderer.show(solid.copy()))["strategy"] == "noop"

    sparse = solid.copy()
    sparse[0, 0] = (9, 9, 9)
    sparse_result = await renderer.show(sparse)
    assert sparse_result["strategy"] == "pixels"
    assert len(device.pixel_batches[-1]) == 1

    dense = sparse.copy()
    dense[1, 0] = (8, 8, 8)
    dense[2, 0] = (7, 7, 7)
    dense_result = await renderer.show(dense)
    assert dense_result["strategy"] == "image"
    assert device.frames[-1][1]["wait_for_ack"] is False
