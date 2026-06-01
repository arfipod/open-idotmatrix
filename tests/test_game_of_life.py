import pytest

from open_idotmatrix.game_of_life import GameOfLife, render_life_preview, run_life_hardware


class LifeDevice:
    def __init__(self):
        self.fills = []
        self.pixel_batches = []

    async def fill(self, color):
        self.fills.append(tuple(color))
        return {"kind": "fullscreen_color"}

    async def pixels_fast(self, pixels, *, parse=False):
        self.pixel_batches.append(list(pixels))
        return []

    async def frame(self, frame, **kwargs):
        raise AssertionError("life demo should use pixel diffs, not GIF frames")


def test_blinker_steps_between_vertical_and_horizontal():
    game = GameOfLife.pattern("blinker", offset=(10, 10), wrap=False)

    assert game.alive == {(10, 11), (11, 11), (12, 11)}
    game.step()
    assert game.alive == {(11, 10), (11, 11), (11, 12)}
    game.step()
    assert game.alive == {(10, 11), (11, 11), (12, 11)}


def test_life_preview_writes_gif(tmp_path):
    path = render_life_preview(tmp_path / "life.gif", seed="glider", generations=4, fps=12, scale=2)

    assert path.exists()
    assert path.read_bytes().startswith(b"GIF")


@pytest.mark.asyncio
async def test_run_life_hardware_clears_then_sends_sparse_diffs():
    device = LifeDevice()

    stats = await run_life_hardware(
        device,
        seed="glider",
        generations=2,
        fps=0,
        wrap=False,
        alive_color=(0, 255, 80),
        dead_color=(0, 0, 0),
    )

    assert stats.generations == 2
    assert device.fills == [(0, 0, 0)]
    assert len(device.pixel_batches) == 2
    assert len(device.pixel_batches[0]) == 5
    assert all(len(batch) < 32 for batch in device.pixel_batches)
