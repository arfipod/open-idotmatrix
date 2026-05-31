# Protocolo iDotMatrix 32×32

Este documento resume el protocolo conocido para una matriz iDotMatrix RGB 32×32 accesible por BLE.

El protocolo no está completo. Las partes marcadas como `experimental` o `hipótesis` deben validarse con hardware real y trazas.

## BLE

| Campo | Valor |
|---|---|
| Nombre BLE esperado | prefijo `IDM-` |
| Service UUID | `000000fa-0000-1000-8000-00805f9b34fb` |
| Write UUID | `0000fa02-0000-1000-8000-00805f9b34fb` |
| Notify UUID | `0000fa03-0000-1000-8000-00805f9b34fb` |

Los paquetes básicos observados no requieren cifrado.

## Convenciones

- Los bytes de longitud multi-byte se codifican en little-endian salvo que se indique lo contrario.
- Los colores se codifican como RGB: `r g b`.
- En este repo se valida la matriz como 32×32: `x = 0..31`, `y = 0..31`.
- Los builders de `open_idotmatrix.protocol` devuelven `bytes` puros.

## Comandos básicos

### Encender

```text
05 00 07 01 01
```

### Apagar

```text
05 00 07 01 00
```

### Brillo

```text
05 00 04 80 <brightness>
```

Rango probable: `5..100`.

Ejemplo, 80%:

```text
05 00 04 80 50
```

### Flip / rotación 180°

```text
05 00 06 80 <enabled>
```

`enabled = 00` normal, `01` rotado.

### Freeze / unfreeze

```text
04 00 03 00
```

Estado: inconsistente. No usar como base de funcionalidades críticas hasta validar.

### Recovery / soft reset

```text
04 00 03 80
05 00 04 80 50
```

Nota: el segundo paquete coincide con un comando de brillo a 80. En este repo se trata como `reset/recover`, no como factory reset.

## Tiempo

Formato:

```text
0b 00 01 80 <year_byte> <month> <day> <dow> <hour> <minute> <second>
```

`dow` usa lunes = 1, domingo = 7.

Hay dos estrategias conocidas para `year_byte`:

| Estrategia | Cálculo |
|---|---|
| `low_byte` | `year & 0xff` |
| `two_digit` | `year % 100` |

Este repo usa `low_byte` por defecto, pero expone ambas para pruebas:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode low_byte
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode two_digit
```

## Pixel / graffiti

Formato:

```text
0a 00 05 01 00 <r> <g> <b> <x> <y>
```

Ejemplo: píxel rojo en la esquina inferior derecha:

```text
0a 00 05 01 00 ff 00 00 1f 1f
```

## Color de pantalla completa

Formato:

```text
07 00 02 02 <r> <g> <b>
```

Ejemplo: rojo:

```text
07 00 02 02 ff 00 00
```

## Reloj

Formato conocido:

```text
08 00 06 01 <flags> <r> <g> <b>
```

Flags:

```python
flags = style | (0x80 if visible_date else 0x00) | (0x40 if hour24 else 0x00)
```

`style` conocido: `0..7`.

## Cronómetro

```text
05 00 09 80 <mode>
```

Modos conocidos:

| Mode | Acción |
|---:|---|
| 0 | reset |
| 1 | start/restart |
| 2 | pause |
| 3 | continue |

## Cuenta atrás

```text
07 00 08 80 <mode> <minutes> <seconds>
```

Modos conocidos:

| Mode | Acción |
|---:|---|
| 0 | disable |
| 1 | start |
| 2 | pause |
| 3 | restart |

## Marcador

```text
08 00 0a 80 <left_lo> <left_hi> <right_lo> <right_hi>
```

Puntuaciones recomendadas: `0..999`.

## Eco mode

```text
0a 00 02 80 <flag> <start_hour> <start_minute> <end_hour> <end_minute> <brightness>
```

Estado: parcialmente conocido.

## Efectos

Formato implementado:

```text
<length> 00 03 02 <style> <speed> <num_colors> <r1> <g1> <b1> ...
```

Estilos conocidos por notas comunitarias:

| Style | Descripción tentativa |
|---:|---|
| 0 | rainbow horizontal graduado |
| 1 | píxeles aleatorios de colores sobre negro |
| 2 | píxeles blancos aleatorios sobre fondo cambiante |
| 3 | rainbow vertical |
| 4 | rainbow diagonal derecha |
| 5 | rainbow diagonal izquierda sobre negro |
| 6 | píxeles aleatorios de colores |

## Texto 32×32

El texto no se envía como UTF-8 plano. Cada carácter se renderiza a un bitmap monocromo de 16×32.

Cada carácter:

```text
05 ff ff ff <64 bytes bitmap>
```

El bitmap es row-major y little-endian dentro de cada byte:

- 16 píxeles por fila;
- 32 filas;
- 2 bytes por fila;
- 64 bytes por carácter.

### Paquete completo de texto

```text
[header 16 bytes] [metadata 14 bytes] [glyph blocks]
```

Header:

| Offset | Tamaño | Descripción |
|---:|---:|---|
| 0 | 2 | longitud total incluyendo header |
| 2 | 1 | `03` |
| 3 | 1 | `00` |
| 4 | 1 | marcador de continuación, normalmente `00` |
| 5 | 4 | longitud de metadata + bitmaps |
| 9 | 4 | CRC32 de metadata + bitmaps |
| 13 | 2 | `00 00` |
| 15 | 1 | `0c` |

Metadata:

| Offset | Tamaño | Descripción |
|---:|---:|---|
| 0 | 2 | número de caracteres |
| 2 | 1 | `00` |
| 3 | 1 | `01` |
| 4 | 1 | modo de texto |
| 5 | 1 | velocidad |
| 6 | 1 | modo de color de texto |
| 7 | 1 | R texto |
| 8 | 1 | G texto |
| 9 | 1 | B texto |
| 10 | 1 | modo de fondo |
| 11 | 1 | R fondo |
| 12 | 1 | G fondo |
| 13 | 1 | B fondo |

Modos de texto conocidos:

| Valor | Efecto |
|---:|---|
| 0 | fijo |
| 1 | scroll izquierda/derecha, según firmware/app |
| 2 | scroll inverso / RTL |
| 3 | scroll arriba |
| 4 | scroll abajo |
| 5 | strobe / parpadeo |
| 6 | fade |
| 7 | falling blocks |
| 8 | laser / filling |

Modos de color:

| Valor | Efecto |
|---:|---|
| 0 | desconocido / default app |
| 1 | RGB fijo |
| 2 | gradiente azul-rojo |
| 3 | gradiente pastel |
| 4 | gradiente rosa-naranja |
| 5 | desconocido |

Fondo:

| Valor | Efecto |
|---:|---|
| 0 | off / negro |
| 1 | sólido RGB |

## GIFs

La ruta más útil para imágenes y animaciones es subir GIFs de 32×32.

Los GIFs se dividen en chunks de 4096 bytes. Cada chunk de aplicación lleva un header de 16 bytes:

```text
[header 16 bytes] [hasta 4096 bytes GIF]
```

Header:

| Offset | Tamaño | Descripción |
|---:|---:|---|
| 0 | 2 | longitud de este chunk incluyendo header |
| 2 | 1 | `01` |
| 3 | 1 | `00` |
| 4 | 1 | `00` primer chunk, `02` siguientes |
| 5 | 4 | longitud total, modo a validar |
| 9 | 4 | CRC32 del GIF completo |
| 13 | 1 | `05` |
| 14 | 1 | `00` |
| 15 | 1 | `0d` |

Hay dos variantes para el campo `total_length`:

| Modo | Cálculo |
|---|---|
| `include_headers` | `len(gif_bytes) + 16 * num_chunks` |
| `raw_payload_only` | `len(gif_bytes)` |

El repo usa `include_headers` por defecto, pero permite elegir:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode include_headers
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode raw_payload_only
```

Notificaciones esperadas:

```text
05 00 01 00 01 = chunk aceptado / continuar
05 00 01 00 03 = upload terminado
```

## PNG / DIY image

Hay una función experimental `build_png_payloads_experimental`. No está incluida en la API principal porque GIF de un frame debería ser más seguro para imagen fija hasta validar más trazas.

## Comandos destructivos

`build_delete_device_data()` existe para documentar el protocolo, pero no debe usarse durante fuzzing o pruebas iniciales.

## Cómo añadir nuevos comandos

1. Captura o deduce bytes.
2. Añade builder puro en `open_idotmatrix/protocol.py`.
3. Añade parser en `parse_packet` si aplica.
4. Añade método de alto nivel en `device.py`.
5. Añade CLI si es útil.
6. Añade tests de bytes exactos.
7. Documenta aquí el formato y el estado: confirmado, experimental o hipótesis.
