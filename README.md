# open-idotmatrix

Toolkit abierto para controlar y estudiar pantallas iDotMatrix **32×32 RGB** desde Linux usando Python.

Este repo está preparado como punto de partida limpio para:

- controlar la matriz por Bluetooth Low Energy desde Linux;
- construir paquetes del protocolo sin depender de hardware;
- enviar comandos básicos, texto y GIFs;
- simular en pantalla de PC lo que se verá en la matriz;
- dejar una base clara para que Codex continúe probando hardware real y ayude a descifrar el protocolo completo.

> Estado: **alpha / reverse engineering**. El objetivo inicial es la matriz iDotMatrix 32×32 cuyo nombre BLE suele empezar por `IDM-`.

## Qué incluye

```text
open-idotmatrix/
  open_idotmatrix/
    constants.py      # UUIDs, geometría y constantes de protocolo
    protocol.py       # builders/parsers puros de paquetes BLE
    text.py           # render de texto 16x32 con Pillow
    gif.py            # procesado y chunking de GIFs 32x32
    transport.py      # transporte BLE con bleak
    device.py         # API async de alto nivel
    simulator.py      # simulador 32x32 con Pillow
    cli.py            # CLI open-idotmatrix
  docs/
    PROTOCOL.md
    ROADMAP.md
    CODEX_BRIEF.md
    REVERSE_ENGINEERING.md
    SIMULATOR.md
    LINUX_BLUETOOTH.md
    TEST_PLAN.md
  examples/
  tests/
  .github/workflows/ci.yml
```

## Instalación local

Requisitos de sistema:

- Python 3.10 o superior.
- Linux con Bluetooth activo para usar hardware real.
- BlueZ instalado si vas a usar BLE.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

El proyecto declara todas sus dependencias Python en `pyproject.toml`: `bleak`, `pillow`, `pytest`, `pytest-asyncio` y `ruff` para desarrollo.

## Primer uso sin hardware: simulador

Renderizar texto a una imagen local:

```bash
open-idotmatrix simulate --text "Hola" --save out/hola.png
```

Renderizar una animación GIF de texto desplazándose:

```bash
open-idotmatrix simulate --text-animation "open-idotmatrix" --save out/text.gif
```

Simular paquetes raw:

```bash
open-idotmatrix simulate --packet-hex "07 00 02 02 ff 00 00" --save out/red.png
open-idotmatrix simulate --packet-hex "0a 00 05 01 00 00 ff 00 1f 1f" --save out/pixel.png
```

## Primer uso con hardware real

Escanear dispositivos:

```bash
open-idotmatrix scan
```

Encender/apagar:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
open-idotmatrix --address AA:BB:CC:DD:EE:FF off
```

Color sólido:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 255 0 0
```

Píxel individual:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 31 0 0 255
```

Texto:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hola" --rgb 255 255 255 --mode 1 --speed 95
```

GIF:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif ./demo.gif
```

Si el ACK por notificaciones falla durante el primer test de GIF:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif ./demo.gif --no-ack
```

## API Python

```python
import asyncio
from open_idotmatrix import OpenIDotMatrix, TextMode

async def main():
    async with OpenIDotMatrix(address="AA:BB:CC:DD:EE:FF") as m:
        await m.on()
        await m.set_brightness(80)
        await m.sync_time()
        await m.fill((0, 0, 0))
        await m.pixel(0, 0, (255, 0, 0))
        await m.pixel(31, 31, (0, 0, 255))
        await m.text("Hola", mode=TextMode.SCROLL_LEFT_TO_RIGHT, color=(255, 255, 255))
        await m.gif("demo.gif")

asyncio.run(main())
```

## Protocolo conocido resumido

UUIDs principales:

```text
Service: 000000fa-0000-1000-8000-00805f9b34fb
Write:   0000fa02-0000-1000-8000-00805f9b34fb
Notify:  0000fa03-0000-1000-8000-00805f9b34fb
```

Comandos básicos:

| Acción | Bytes |
|---|---|
| Encender | `05 00 07 01 01` |
| Apagar | `05 00 07 01 00` |
| Brillo | `05 00 04 80 <percent>` |
| Color pantalla completa | `07 00 02 02 <r> <g> <b>` |
| Pixel | `0a 00 05 01 00 <r> <g> <b> <x> <y>` |
| Hora | `0b 00 01 80 <yy> <mm> <dd> <dow> <hh> <min> <sec>` |

Más detalles en [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Decodificar paquetes

```bash
open-idotmatrix decode "05 00 07 01 01"
open-idotmatrix decode "0a 00 05 01 00 ff 00 00 1f 1f"
```

Esto imprime JSON con el tipo de paquete reconocido, longitudes y campos.

## Tests

```bash
pytest
```

Los tests actuales cubren:

- bytes exactos de comandos básicos;
- validación de rangos;
- paquetización de texto y CRC32;
- chunking de GIF;
- simulación de pixel, color sólido y texto.

Ver [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md).

## Cómo debe continuar Codex

Este repo ya incluye una guía específica para continuar con hardware real: [`docs/CODEX_BRIEF.md`](docs/CODEX_BRIEF.md).

Resumen de la primera petición a Codex:

```text
Lee README.md, docs/PROTOCOL.md, docs/TEST_PLAN.md y docs/CODEX_BRIEF.md.
Ejecuta pytest. Después, con mi matriz iDotMatrix 32x32 conectada por Bluetooth,
prueba scan, on/off, fill, pixel, text y gif. Registra los bytes enviados,
notificaciones recibidas y cualquier discrepancia. No ejecutes comandos
destructivos salvo que lo pida explícitamente.
```

## Principios del proyecto

1. **Código limpio desde cero.** No se copia código de otros repos; se reimplementan paquetes a partir de conocimiento público y pruebas.
2. **Builders puros.** El protocolo está separado del transporte BLE.
3. **Hardware opcional para tests.** Los tests unitarios funcionan sin matriz.
4. **32×32 primero.** No se intenta soportar 16×16 o 64×64 hasta estabilizar el caso real.
5. **Reverse engineering reproducible.** Cada comando nuevo debe documentarse con bytes, hipótesis, tests y captura si existe.

## Licencia

MIT. Ver [`LICENSE`](LICENSE).

## Créditos técnicos

Este proyecto parte del análisis público existente sobre iDotMatrix, especialmente las notas de 8none1 y el trabajo de la comunidad alrededor de clientes Python para iDotMatrix. La implementación de este repo es nueva y está organizada para pruebas, simulación y reverse engineering incremental.
