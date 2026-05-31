# Arquitectura

## Capas

```text
CLI / ejemplos
    ↓
OpenIDotMatrix       # API async de alto nivel
    ↓
protocol.py          # bytes puros
transport.py         # BLE con bleak
    ↓
iDotMatrix 32x32
```

El simulador usa `protocol.py` y `text.py`, pero no usa BLE.

## Por qué separar protocolo y transporte

Permite:

- testear sin hardware;
- comparar bytes contra capturas;
- reutilizar el protocolo con otro backend BLE;
- añadir simulación y tooling sin conectar a la matriz.

## Módulos

| Módulo | Responsabilidad |
|---|---|
| `constants.py` | UUIDs, tamaños, ACKs |
| `types.py` | enums y validación básica |
| `protocol.py` | construir/parsear paquetes |
| `text.py` | PIL → bitmaps 16×32 |
| `gif.py` | GIF/image → GIF 32×32 → chunks |
| `transport.py` | BLE scan/connect/write/notify |
| `device.py` | API cómoda async |
| `simulator.py` | vista local 32×32 |
| `cli.py` | comandos de usuario |

## Estabilidad

- `protocol.py`: debe ser la parte más testeada y estable.
- `transport.py`: puede necesitar ajustes por BlueZ/MTU.
- `gif.py`: probablemente necesitará validación por firmware.
- `simulator.py`: aproximado, no pretende ser firmware exacto.
