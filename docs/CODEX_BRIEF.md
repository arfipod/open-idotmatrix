# Guía para Codex

Este documento está escrito para que Codex pueda continuar desde este repo con hardware real y mejorar la biblioteca sin perder contexto.

## Contexto

Tenemos una matriz iDotMatrix RGB 32×32. Queremos controlarla desde Linux por BLE y descifrar progresivamente el protocolo completo.

El repo ya incluye:

- builders puros de paquetes en `open_idotmatrix/protocol.py`;
- transporte BLE en `open_idotmatrix/transport.py`;
- API de alto nivel en `open_idotmatrix/device.py`;
- CLI en `open_idotmatrix/cli.py`;
- simulador visual en `open_idotmatrix/simulator.py`;
- tests sin hardware en `tests/`;
- documentación de protocolo en `docs/PROTOCOL.md`.

## Primera petición recomendada a Codex

```text
Lee README.md, docs/PROTOCOL.md, docs/TEST_PLAN.md, docs/ROADMAP.md y docs/CODEX_BRIEF.md.
Ejecuta pytest y corrige solo si falla.
Después prepara una sesión de hardware smoke test para una iDotMatrix 32x32 en Linux:
scan, on, off, brightness, fill, pixel corners, sync-time, text A, text Hola y GIF pequeño.
No ejecutes build_delete_device_data ni comandos destructivos.
Registra para cada prueba: comando CLI, bytes enviados, notificaciones recibidas,
resultado visual esperado, resultado visual observado y cambios propuestos.
```

## Reglas para Codex

1. No borrar documentación de protocolo; ampliarla.
2. No mezclar transporte BLE con construcción de paquetes.
3. No copiar código de repos GPL u otros proyectos si se mantiene licencia MIT.
4. Si se cambia un paquete, añadir o actualizar test de bytes exactos.
5. Si un comportamiento depende de hardware, marcarlo como `experimental` hasta validarlo.
6. No ejecutar comandos destructivos salvo instrucción explícita.
7. Registrar discrepancias; no ocultarlas.

## Tareas prioritarias

### Tarea 1 — Logging de sesión BLE

Añadir opción CLI:

```bash
open-idotmatrix --address ... --session-log out/session.jsonl text "Hola"
```

Cada línea JSONL debería contener:

```json
{"ts":"...", "direction":"tx", "hex":"05 00 07 01 01", "kind":"screen_on"}
{"ts":"...", "direction":"rx", "hex":"05 00 01 00 01", "kind":"notification"}
```

### Tarea 2 — Smoke test automatizado

Crear comando:

```bash
open-idotmatrix --address ... smoke-test --out out/smoke.json
```

Debe ejecutar comandos seguros y pedir confirmación visual al usuario o guardar checklist.

### Tarea 3 — GIF ACK validation

Probar dos modos:

```bash
open-idotmatrix --address ... gif demo.gif --total-length-mode include_headers
open-idotmatrix --address ... gif demo.gif --total-length-mode raw_payload_only
```

Registrar cuál funciona con:

- write with response;
- write without response;
- esperando ACK;
- sin esperar ACK.

### Tarea 4 — MTU / write splitting

Inspeccionar si `max_write_without_response_size` funciona de forma estable en BlueZ. Si no, añadir opción:

```bash
--gatt-chunk-size 20
--gatt-chunk-size 244
```

### Tarea 5 — Capturas BLE

Añadir herramienta para importar logs `btmon` o `btsnoop` si se exportan en texto. Objetivo: extraer writes a `fa02` y notificaciones de `fa03`.

### Tarea 6 — Simulador avanzado

Mejorar animaciones de texto:

- modo 1/2 horizontal real;
- modo 3/4 vertical;
- modo 5 strobe;
- modo 6 fade;
- modo 7 falling blocks;
- modo 8 laser/filling.

### Tarea 7 — Documentar unknowns

Añadir `docs/UNKNOWN_BYTES.md` o ampliar `PROTOCOL.md` con:

- byte offset;
- valores observados;
- hipótesis;
- prueba realizada;
- resultado.

## Formato recomendado para resultados de hardware

```markdown
## Hardware test YYYY-MM-DD

- OS:
- Kernel:
- BlueZ:
- Python:
- bleak:
- Device BLE name:
- Device address:
- Firmware/app version si se conoce:

| Test | Command | TX bytes | RX bytes | Expected | Observed | Status |
|---|---|---|---|---|---|---|
| on | `open-idotmatrix ... on` | `05 00 07 01 01` | ... | screen on | screen on | pass |
```

## Zonas donde tener cuidado

- `delete_device_data` puede borrar datos del dispositivo.
- Password/protection no está integrado en la API de alto nivel.
- Fuzzing con comandos desconocidos puede dejar el firmware en estado raro; usar `reset` si se atasca.
- GIFs grandes pueden tardar bastante o fallar por timing.
