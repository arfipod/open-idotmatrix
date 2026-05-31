# Test plan

## Tests sin hardware

Ejecutar:

```bash
pytest
```

Cubre:

- bytes exactos de comandos básicos;
- validación de coordenadas y colores;
- encoding de hora con dos estrategias de año;
- packet builder de texto;
- CRC32 de texto;
- chunking de GIF;
- simulator básico.

## Tests con hardware

Usar una matriz iDotMatrix 32×32 encendida y cerca del PC.

### 1. Scan

```bash
open-idotmatrix scan
```

Registrar:

- nombre BLE;
- address;
- RSSI.

### 2. On/off

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
open-idotmatrix --address AA:BB:CC:DD:EE:FF off
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
```

Esperado: pantalla apaga/enciende.

### 3. Brillo

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF brightness 20
open-idotmatrix --address AA:BB:CC:DD:EE:FF brightness 80
```

Esperado: cambio visible de brillo.

### 4. Color sólido

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 255 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 255 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 0
```

Esperado: pantalla roja, verde, azul, negra.

### 5. Orientación de píxeles

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 0 0 255 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 0 0 255 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 0 31 0 0 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 31 255 255 255
```

Registrar orientación real:

| Coordenada | Color | Posición observada |
|---|---|---|
| 0,0 | rojo | |
| 31,0 | verde | |
| 0,31 | azul | |
| 31,31 | blanco | |

### 6. Hora

Probar ambos modos:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode low_byte
open-idotmatrix --address AA:BB:CC:DD:EE:FF clock 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode two_digit
open-idotmatrix --address AA:BB:CC:DD:EE:FF clock 0
```

Registrar cuál muestra fecha/hora correcta si el modo reloj muestra fecha.

### 7. Texto

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "A" --mode 0 --rgb 255 255 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hola" --mode 1 --speed 95 --rgb 255 0 0
```

Registrar:

- orientación;
- dirección de scroll;
- velocidad;
- color real.

### 8. GIF

Usar un GIF pequeño. Si no se tiene, crear uno con Pillow o usar una imagen y dejar que el CLI procese.

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif
```

Si falla:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --no-ack
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode raw_payload_only
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --no-response
```

Registrar notificaciones si hay logging.

## Plantilla de reporte

```markdown
# Hardware test

- Date:
- OS:
- Kernel:
- BlueZ:
- Python:
- bleak:
- Device name:
- Address:

| Test | Command | Expected | Observed | Status | Notes |
|---|---|---|---|---|---|
| scan | `open-idotmatrix scan` | find IDM-* | | | |
| on | `... on` | screen on | | | |
```
