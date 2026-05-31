# Roadmap

## Objetivo principal

Crear una biblioteca Linux-first, abierta y testeable para controlar matrices iDotMatrix 32×32 y, a largo plazo, descifrar el protocolo completo.

## Estado actual incluido en este ZIP

### Hecho

- Paquete Python instalable: `open-idotmatrix`.
- CLI: `open-idotmatrix`.
- Builders puros para comandos básicos.
- Parser/decoder best-effort de paquetes.
- Transporte BLE async con `bleak`.
- API de alto nivel `OpenIDotMatrix`.
- Texto 16×32 con Pillow.
- GIF processing y chunking 4096+16.
- Simulador 32×32 con Pillow.
- Tests unitarios sin hardware.
- Documentación de protocolo, Linux BLE, simulator, reverse engineering y Codex.
- GitHub Actions CI.

### Pendiente de validar con hardware real

- Confirmar que `write_gatt_char` troceado por MTU funciona igual que los prototipos originales.
- Confirmar si GIF `total_length` debe ser `include_headers` o `raw_payload_only` en tu matriz concreta.
- Confirmar ACKs exactos durante GIF upload.
- Confirmar `year_byte` en reloj: `year & 0xff` vs `year % 100`.
- Confirmar sentido real de modos de texto 1 y 2.
- Confirmar brillo, flip, freeze y reset/recover en firmware concreto.

## Fase 1 — Hardware smoke test

1. `open-idotmatrix scan`.
2. `on` / `off`.
3. `brightness 50`.
4. `fill 255 0 0`, `fill 0 255 0`, `fill 0 0 255`.
5. `pixel 0 0`, `pixel 31 0`, `pixel 0 31`, `pixel 31 31` para orientación.
6. `sync-time` con ambos modos de año.
7. `text "A"`, `text "Hola"`.
8. `gif demo.gif` con ACK y sin ACK.

Resultado esperado: tabla de compatibilidad por comando.

## Fase 2 — Robustez BLE

- Añadir logging estructurado de bytes enviados y notificaciones recibidas.
- Añadir retry configurable por comando.
- Añadir reconexión automática si BlueZ corta sesión.
- Detectar MTU real y comparar write-with-response vs write-without-response.
- Añadir opción `--dump-session out/session.jsonl`.

## Fase 3 — Protocolo de texto completo

- Confirmar todos los `TextMode`.
- Confirmar todos los `TextColorMode`.
- Añadir soporte de texto largo > 4096 bytes si el firmware lo requiere.
- Explorar tamaño de fuente 16: separador `02 ff ff ff` o variantes.
- Mejorar simulador para scroll vertical, fade, strobe y falling blocks.

## Fase 4 — GIF e imagen completa

- Validar flow-control por `0500010001` y `0500010003`.
- Comparar `include_headers` vs `raw_payload_only`.
- Añadir test de GIF real generado en memoria.
- Añadir single-frame GIF como modo de imagen fija recomendado.
- Investigar PNG/DIY y reemplazar `build_png_payloads_experimental` por función confirmada.

## Fase 5 — Reverse engineering sistemático

- Crear corpus de capturas en `captures/`, ignorado por git si contiene datos grandes.
- Herramienta `open-idotmatrix decode-capture` para extraer writes BLE.
- Matriz de comandos app oficial → bytes → efecto visual.
- Comparar Android app vs paquete generado por esta librería.
- Documentar unknown bytes con hipótesis y pruebas.

## Fase 6 — Funciones avanzadas

- Reloj con presets.
- Scoreboard completo.
- Countdown y chronograph con API estable.
- Efectos confirmados.
- Eco mode confirmado.
- Modo música / micrófono si el firmware lo permite.
- Home Assistant / MQTT.
- Pequeña GUI local.
- Exportador de animaciones desde spritesheets.

## Fase 7 — Soporte multi-dispositivo

- Configuración YAML/TOML de dispositivos.
- Grupos de matrices.
- Envío paralelo con `asyncio.gather`.
- Scheduler para relojes, alertas y dashboards.

## Definición de “comando confirmado”

Un comando pasa de experimental a confirmado si tiene:

1. builder puro;
2. test unitario de bytes;
3. prueba en hardware real documentada;
4. captura o log con bytes enviados y respuesta;
5. entrada en `docs/PROTOCOL.md`;
6. entrada CLI o API de alto nivel si aplica.
