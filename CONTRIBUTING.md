# Contributing

Gracias por contribuir a `open-idotmatrix`.

## Reglas de diseño

- Mantener el protocolo en funciones puras dentro de `open_idotmatrix/protocol.py`.
- Mantener BLE en `open_idotmatrix/transport.py`.
- Mantener API de usuario en `open_idotmatrix/device.py`.
- Todo paquete nuevo debe tener test de bytes exactos.
- Toda hipótesis de protocolo debe documentarse en `docs/PROTOCOL.md`.
- No copiar código de proyectos con licencias incompatibles; reimplementar desde comportamiento documentado y pruebas.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
ruff check .
```

## Pull requests

Una PR ideal incluye:

1. explicación del comando o función;
2. bytes enviados;
3. fuente de la hipótesis o captura;
4. test unitario;
5. documentación actualizada;
6. resultado en hardware si aplica.
