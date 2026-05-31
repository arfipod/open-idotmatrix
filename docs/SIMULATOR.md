# Simulador

El simulador usa Pillow para renderizar una matriz RGB 32×32 en una imagen escalada.

Sirve para:

- comprobar texto sin hardware;
- visualizar paquetes raw;
- previsualizar GIFs;
- escribir tests de rendering aproximado;
- depurar orientación de píxeles.

## CLI

Texto:

```bash
open-idotmatrix simulate --text "Hola" --save out/hola.png
```

Texto animado:

```bash
open-idotmatrix simulate --text-animation "Hola mundo" --save out/hola_anim.gif
```

Color sólido:

```bash
open-idotmatrix simulate --fill 255 0 0 --save out/red.png
```

Píxeles:

```bash
open-idotmatrix simulate \
  --fill 0 0 0 \
  --pixel 0 0 255 0 0 \
  --pixel 31 0 0 255 0 \
  --pixel 0 31 0 0 255 \
  --pixel 31 31 255 255 255 \
  --save out/corners.png
```

Paquete raw:

```bash
open-idotmatrix simulate --packet-hex "0a 00 05 01 00 ff 00 00 1f 1f" --save out/raw_pixel.png
```

Previsualizar primer frame de GIF:

```bash
open-idotmatrix simulate --gif demo.gif --save out/demo_first_frame.png
```

Exportar frames de un GIF:

```bash
open-idotmatrix gif-preview demo.gif out/frames --max-frames 16
```

## API Python

```python
from open_idotmatrix.simulator import MatrixSimulator
from open_idotmatrix.protocol import build_fullscreen_color, build_pixel

sim = MatrixSimulator()
sim.apply_packet(build_fullscreen_color((0, 0, 0)))
sim.apply_packet(build_pixel(31, 31, (255, 0, 0)))
sim.save("out/test.png")
```

Texto:

```python
from open_idotmatrix.protocol import build_text_packet
from open_idotmatrix.text import render_text_bitmap_bytes
from open_idotmatrix.simulator import MatrixSimulator

bitmaps = render_text_bitmap_bytes("Hola")
packet = build_text_packet(bitmaps, text_color=(255, 255, 255))

sim = MatrixSimulator()
sim.apply_packet(packet, text_scroll_offset=10)
sim.save("out/text.png")
```

## Limitaciones actuales

El simulador no pretende replicar todos los efectos exactos del firmware. Hoy cubre:

- on/off;
- brightness aproximado;
- color sólido;
- píxel individual;
- texto fijo y scroll horizontal aproximado;
- primer frame de GIF.

Pendiente:

- scroll vertical real;
- strobe/fade/falling blocks/laser;
- simulación exacta de gradientes de color de texto;
- animación de GIF como playback dentro del simulador;
- GUI interactiva.
