import asyncio

import pytest

from open_idotmatrix.framebuffer import MatrixFrame
from open_idotmatrix.outputs import HardwareOutput, SimulatorOutput, TeeOutput
from open_idotmatrix.runtime import MatrixRuntime
from open_idotmatrix.testing import FakeTransport


class RecordingDevice:
    def __init__(self, *, delay: float = 0.0):
        self.connected = False
        self.disconnected = False
        self.delay = delay
        self.fills = []
        self.pixel_batches = []
        self.frames = []

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.disconnected = True

    async def fill(self, color):
        self.fills.append(tuple(color))
        if self.delay:
            await asyncio.sleep(self.delay)
        return {"kind": "fullscreen_color"}

    async def pixels_fast(self, pixels, *, parse=False):
        self.pixel_batches.append(list(pixels))
        if self.delay:
            await asyncio.sleep(self.delay)
        return []

    async def frame(self, frame, **kwargs):
        self.frames.append(frame.copy())
        if self.delay:
            await asyncio.sleep(self.delay)
        return [{"kind": "gif_chunk"}]


@pytest.mark.asyncio
async def test_simulator_and_hardware_outputs_can_be_teed(tmp_path):
    device = RecordingDevice()
    simulator_output = SimulatorOutput(save_path=tmp_path / "frame.png", scale=2, grid=False)
    hardware_output = HardwareOutput(device)
    tee = TeeOutput(simulator_output, hardware_output)
    frame = MatrixFrame(fill=(1, 2, 3))

    result = await tee.show(frame)

    assert result[0]["output"] == "simulator"
    assert (tmp_path / "frame.png").exists()
    assert result[1]["output"] == "hardware"
    assert device.fills == [(1, 2, 3)]


def test_matrix_runtime_submits_frames_from_sync_code():
    transport = FakeTransport()
    runtime = MatrixRuntime(transport=transport)
    frame = MatrixFrame(fill=(10, 20, 30))

    runtime.start(timeout=1)
    try:
        assert runtime.submit_frame(frame) is True
        runtime.wait_until_idle(timeout=1)
    finally:
        runtime.close(timeout=1)

    assert transport.writes
    assert transport.is_connected() is False


def test_matrix_runtime_backpressure_keeps_latest_queued_frame():
    device = RecordingDevice(delay=0.05)
    runtime = MatrixRuntime(device=device)
    first = MatrixFrame(fill=(1, 0, 0))
    second = MatrixFrame(fill=(0, 2, 0))
    third = MatrixFrame(fill=(0, 0, 3))

    runtime.start(timeout=1)
    try:
        assert runtime.submit_frame(first) is True
        assert runtime.submit_frame(second) is True
        assert runtime.submit_frame(third) is True
        runtime.wait_until_idle(timeout=2)
    finally:
        runtime.close(timeout=1)

    assert device.connected is True
    assert device.disconnected is True
    assert device.fills[-1] == (0, 0, 3)
    assert (0, 2, 0) not in device.fills
