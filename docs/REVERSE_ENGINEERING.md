# Proceso de reverse engineering

## Objetivo

Completar el protocolo de iDotMatrix 32×32 de forma reproducible, con pruebas y documentación.

## Fuentes de verdad

1. Lo que el hardware real hace.
2. Capturas BLE de la app oficial o de esta biblioteca.
3. Tests de bytes exactos.
4. Documentación en `docs/PROTOCOL.md`.

## Capturar tráfico en Linux

Con BlueZ se puede usar `btmon`:

```bash
sudo btmon | tee captures/session.btmon.txt
```

En otra terminal ejecutar comandos:

```bash
open-idotmatrix scan
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hola"
```

Después buscar writes a `fa02` y notificaciones de `fa03`.

## Capturar tráfico desde Android

En Android suele existir la opción de activar HCI snoop log en opciones de desarrollador. El nombre exacto depende del fabricante. El flujo general es:

1. Activar Bluetooth HCI snoop log.
2. Abrir app iDotMatrix oficial.
3. Ejecutar una acción concreta, por ejemplo cambiar reloj o enviar texto.
4. Exportar el log.
5. Abrir con Wireshark.
6. Filtrar por GATT writes/notifies y UUID `fa02`/`fa03`.

No subir capturas con información personal o direcciones BLE privadas si el repo es público.

## Formato de registro recomendado

Crear archivos de texto o JSONL con esta estructura:

```json
{"direction":"tx","uuid":"0000fa02-0000-1000-8000-00805f9b34fb","hex":"05 00 07 01 01","note":"screen on"}
{"direction":"rx","uuid":"0000fa03-0000-1000-8000-00805f9b34fb","hex":"05 00 01 00 01","note":"chunk ack"}
```

## Método para descifrar comandos nuevos

1. Ejecutar una sola acción en la app oficial.
2. Capturar bytes.
3. Repetir con un parámetro cambiado.
4. Comparar diffs byte a byte.
5. Aislar campos.
6. Crear builder en `protocol.py`.
7. Añadir parser en `parse_packet`.
8. Añadir test unitario.
9. Probar con hardware.
10. Documentar resultado.

## No hacer al principio

- No fuzzear comandos destructivos.
- No enviar payloads enormes sin límites.
- No probar passwords/protección hasta tener recovery claro.
- No asumir que todos los firmwares iDotMatrix se comportan igual.

## Hipótesis actuales importantes

| Tema | Hipótesis | Acción necesaria |
|---|---|---|
| Año en `sync-time` | `year & 0xff` o `year % 100` | probar reloj con fecha |
| GIF total length | incluye headers o raw payload | probar ambos modos |
| ACK final GIF | último chunk responde `0500010003` | registrar notificaciones |
| Texto modo 1/2 | dirección depende de firmware/app | probar visualmente |
| PNG/DIY | formato no confirmado | priorizar GIF de un frame |

## Herramientas del repo

Decodificar paquete:

```bash
open-idotmatrix decode "0a 00 05 01 00 ff 00 00 1f 1f"
```

Simular paquete:

```bash
open-idotmatrix simulate --packet-hex "07 00 02 02 00 00 ff" --save out/blue.png
```

Generar texto y visualizarlo:

```bash
open-idotmatrix simulate --text "ABC" --save out/abc.png
```
