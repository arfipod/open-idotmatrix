# Applications And Games

Use the CLI for humans, shell scripts, and hardware experiments. External apps
and games should import `open_idotmatrix`, keep one connection open, and render
frames through the Python API.

Do not launch this per frame:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 5 5 0 255 0
```

That creates process and connection overhead in the hottest part of the app.

## Async Apps

```python
import asyncio
from open_idotmatrix import MatrixFrame, MatrixRenderer, OpenIDotMatrix

async def main():
    async with OpenIDotMatrix(address="AA:BB:CC:DD:EE:FF") as device:
        renderer = MatrixRenderer(device)
        frame = MatrixFrame(fill=(0, 0, 0))
        frame[5, 5] = (0, 255, 0)
        await renderer.show(frame)

asyncio.run(main())
```

`MatrixRenderer` chooses a practical strategy:

- no changes: no-op;
- solid frame: `fill`;
- sparse changes: `pixels_fast`;
- dense changes: single-frame GIF upload.

## Synchronous Game Loops

Pygame and many simple game loops are synchronous. Use `MatrixRuntime` to run
BLE and asyncio on a background thread:

```python
from open_idotmatrix import MatrixFrame, MatrixRuntime

runtime = MatrixRuntime(address="AA:BB:CC:DD:EE:FF")
runtime.start()

try:
    frame = MatrixFrame(fill=(0, 0, 0))
    frame[5, 5] = (0, 255, 0)
    runtime.submit_frame(frame)
finally:
    runtime.close()
```

`submit_frame()` is non-blocking. The runtime keeps a queue of one frame; if the
game produces frames faster than BLE can send them, the old queued frame is
dropped and the newest frame wins.

## Simulator And Hardware Together

Use `TeeOutput` to render to a local simulator and the physical matrix from the
same `MatrixFrame`:

```python
import asyncio
from open_idotmatrix import (
    HardwareOutput,
    MatrixFrame,
    OpenIDotMatrix,
    SimulatorOutput,
    TeeOutput,
)

async def main():
    async with OpenIDotMatrix(address="AA:BB:CC:DD:EE:FF") as device:
        output = TeeOutput(
            SimulatorOutput(save_path="out/latest.png"),
            HardwareOutput(device),
        )
        frame = MatrixFrame(fill=(0, 0, 0))
        frame[0, 0] = (255, 0, 0)
        await output.show(frame)

asyncio.run(main())
```

For app tests without hardware, use `FakeTransport`:

```python
from open_idotmatrix import FakeTransport, MatrixFrame, OpenIDotMatrix

transport = FakeTransport()
matrix = OpenIDotMatrix(transport=transport)
```

## Demo: Conway's Game Of Life

The package includes a local Game of Life demo that computes every generation on
the host computer and only sends frame diffs to the matrix. It keeps one BLE
connection open and clears the display once before streaming live cells, which
keeps startup and per-generation traffic low.

Hardware:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF life --seed random --generations 200 --fps 12
```

Preview without hardware:

```bash
open-idotmatrix life --seed glider --generations 120 --simulate out/life.gif
```

The Qt app exposes the same demo in the Demos tab.

## Playable Qt Games

The Qt app also has a Games tab with three live games rendered on the matrix:

- Flappy Bird;
- Tetris;
- Space Invaders.

The game loop runs on the computer, keyboard input updates the game state, and
only the resulting 32x32 frames are sent to the matrix through `MatrixRuntime`.
Use the keyboard while the game is running:

- arrows: movement;
- space: flap, drop, or fire depending on the game;
- up/Z/X: rotate in Tetris;
- R: reset.
