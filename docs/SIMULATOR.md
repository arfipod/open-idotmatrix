# Simulator

The simulator uses Pillow to render a 32x32 RGB matrix into a scaled image.

It is useful for:

- checking text without hardware;
- visualizing raw packets;
- previewing GIFs;
- writing approximate rendering tests;
- debugging pixel orientation.

## CLI

Text:

```bash
open-idotmatrix simulate --text "Hello" --save out/hello.png
```

Animated text:

```bash
open-idotmatrix simulate --text-animation "Hello world" --save out/hello_anim.gif
```

Solid color:

```bash
open-idotmatrix simulate --fill 255 0 0 --save out/red.png
```

Pixels:

```bash
open-idotmatrix simulate \
  --fill 0 0 0 \
  --pixel 0 0 255 0 0 \
  --pixel 31 0 0 255 0 \
  --pixel 0 31 0 0 255 \
  --pixel 31 31 255 255 255 \
  --save out/corners.png
```

Raw packet:

```bash
open-idotmatrix simulate --packet-hex "0a 00 05 01 00 ff 00 00 1f 1f" --save out/raw_pixel.png
```

Preview the first GIF frame:

```bash
open-idotmatrix simulate --gif demo.gif --save out/demo_first_frame.png
```

Export GIF frames:

```bash
open-idotmatrix gif-preview demo.gif out/frames --max-frames 16
```

## Python API

```python
from open_idotmatrix.simulator import MatrixSimulator
from open_idotmatrix.protocol import build_fullscreen_color, build_pixel

sim = MatrixSimulator()
sim.apply_packet(build_fullscreen_color((0, 0, 0)))
sim.apply_packet(build_pixel(31, 31, (255, 0, 0)))
sim.save("out/test.png")
```

Text:

```python
from open_idotmatrix.protocol import build_text_packet
from open_idotmatrix.text import render_text_bitmap_bytes
from open_idotmatrix.simulator import MatrixSimulator

bitmaps = render_text_bitmap_bytes("Hello")
packet = build_text_packet(bitmaps, text_color=(255, 255, 255))

sim = MatrixSimulator()
sim.apply_packet(packet, text_scroll_offset=10)
sim.save("out/text.png")
```

## Current Limitations

The simulator is not intended to replicate every exact firmware effect. Today it covers:

- on/off;
- approximate brightness;
- solid color;
- single pixel;
- fixed text and approximate horizontal scrolling;
- first GIF frame.

Pending:

- real vertical scrolling;
- strobe/fade/falling blocks/laser;
- exact simulation of text color gradients;
- GIF animation playback inside the simulator;
- interactive GUI improvements.
