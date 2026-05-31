# Linux Bluetooth / BlueZ

## Requisitos

Instalar Bluetooth/BlueZ según distribución.

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y bluetooth bluez bluez-tools rfkill
sudo systemctl enable --now bluetooth
```

Comprobar estado:

```bash
rfkill list bluetooth
bluetoothctl show
```

Si está bloqueado:

```bash
sudo rfkill unblock bluetooth
```

## Permisos

Normalmente `bleak` habla con BlueZ por D-Bus. Si el usuario no puede acceder, probar:

```bash
sudo usermod -aG bluetooth "$USER"
```

Cerrar sesión y volver a entrar.

Si sigue fallando, probar temporalmente como root para aislar si es problema de permisos:

```bash
sudo .venv/bin/open-idotmatrix scan
```

## Escaneo

```bash
open-idotmatrix scan
```

Salida esperada:

```json
[
  {
    "address": "AA:BB:CC:DD:EE:FF",
    "name": "IDM-xxxx",
    "rssi": -42
  }
]
```

## Diagnóstico manual con bluetoothctl

```bash
bluetoothctl
power on
scan on
```

Buscar dispositivos cuyo nombre empiece por `IDM-`.

## Capturas con btmon

```bash
sudo btmon | tee captures/session.btmon.txt
```

Mientras `btmon` está activo, ejecutar comandos desde otra terminal.

## Problemas habituales

### No aparece el dispositivo

- Acercar la matriz al PC.
- Reiniciar Bluetooth: `sudo systemctl restart bluetooth`.
- Desconectar y reconectar alimentación de la matriz.
- Comprobar que la app móvil no está conectada a la vez.
- Comprobar `rfkill`.

### Conecta pero no escribe

- Probar `reset`.
- Probar `--no-response` en GIF.
- Probar comandos cortos primero: `on`, `off`, `fill`.
- Añadir logging de sesión como tarea de roadmap.

### GIF falla

Probar combinaciones:

```bash
open-idotmatrix --address ... gif demo.gif --total-length-mode include_headers
open-idotmatrix --address ... gif demo.gif --total-length-mode raw_payload_only
open-idotmatrix --address ... gif demo.gif --no-ack
open-idotmatrix --address ... gif demo.gif --no-response
```

Registrar cuál funciona.
