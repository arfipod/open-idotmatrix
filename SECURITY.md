# Security and safety

Este proyecto controla hardware BLE. Algunas operaciones pueden dejar el dispositivo en un estado extraño o borrar datos.

## No hacer por defecto

- No fuzzear comandos desconocidos en dispositivos que no puedas resetear.
- No ejecutar `delete_device_data` salvo que se indique explícitamente.
- No subir logs públicos con direcciones BLE personales si te preocupa la privacidad.
- No asumir que todos los dispositivos iDotMatrix comparten firmware.

## Reportar problemas

Para vulnerabilidades o comportamientos peligrosos, abre un issue describiendo:

- dispositivo;
- firmware/app si se conoce;
- comandos enviados;
- efecto observado;
- si es reproducible.
