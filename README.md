# SensiAura aimbot — panel + backend

Panel HTML controla aim (FOV, on/off) por WebSocket; el backend lee posiciones de enemigos con Frida y mueve la mira con ADB en un emulador Android.

## Estructura

    panel.html          tu HTML original (parchear con patch.py)
    patch.py            inyecta el puente WebSocket
    aimbot_server.py    backend
    ff_hook.js          Frida hook (offsets en OFFSETS.md)
    requirements.txt
    run.bat / run.sh
    OFFSETS.md          cómo derivar offsets
    README.md

## Setup

### 1. Python

Python 3.10+ en PATH.

    pip install -r requirements.txt

### 2. Emulador + Free Fire

BlueStacks o LDPlayer con Free Fire instalado y corriendo.
`adb devices` debe listar el serial (ej: `emulator-5554`).

### 3. frida-server en el emulador

Descarga frida-server de https://github.com/frida/frida/releases con la arquitectura del emulador (x86_64 normalmente).

    adb push frida-server /data/local/tmp/
    adb shell chmod 755 /data/local/tmp/frida-server
    adb shell su -c /data/local/tmp/frida-server &
    adb forward tcp:27042 tcp:27042

### 4. Offsets

Sigue `OFFSETS.md`. Sin offsets correctos, `ff_hook.js` devuelve `[]`.

### 5. Parchear el HTML

Coloca tu HTML como `panel.html` y:

    python patch.py

Crea backup `panel.html.bak` y añade el puente WebSocket.

### 6. Arrancar

Windows: doble clic `run.bat`.
Linux/Mac: `./run.sh`.

Abre `panel.html` en Chrome. Login `Aimbot`. El estado debe decir `backend conectado`. Toggle ON. FOV 90.

## Cómo funciona

    panel.html --ws--> aimbot_server --adb--> emulador (Free Fire)
                            |
                            +--frida--> memoria del juego (posiciones)

- `aimbot_server.py` recibe `{enabled, fov, sensitivity}` por WS.
- Cada tick (30 Hz): pide posiciones a Frida, elige enemigo más cercano dentro del FOV, calcula delta desde centro, envía `adb input swipe`.
- El juego interpreta el swipe como giro de cámara.

## Ajustes

    ADB_BIN         ruta a adb (default: adb)
    ADB_SERIAL      serial (default: auto)
    WS_PORT         puerto (default: 8765)
    SCREEN_W/H      resolución (default: 1920x1080)
    AIM_GAIN        fracción del delta por tick (default: 0.35)
    TICK_HZ         frecuencia del loop (default: 30)

`AIM_GAIN` alto = más agresivo. Bajo = suave, más natural.

## Límites

- iOS: no funciona sin jailbreak + tweak. Este stack es Android/emulador.
- Offsets: cambian por versión. `OFFSETS.md` cubre la re-derivación.
- Anticheat: Free Fire detecta patrones de input server-side. `AIM_GAIN` bajo y `TICK_HZ` moderado reducen huella, no la eliminan.