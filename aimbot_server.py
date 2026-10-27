# language: Python, file: aimbot_server.py, target: Windows/Linux, Free Fire en BlueStacks/LDPlayer
# Backend del panel SensiAura: WebSocket + ADB input + Frida entity reader.

import asyncio, json, math, os, subprocess, sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("[!] Falta websockets: pip install -r requirements.txt")
    sys.exit(1)

try:
    import frida
    FRIDA_OK = True
except ImportError:
    FRIDA_OK = False

# ---------------------------------------------------------------- config
ADB        = os.getenv("ADB_BIN", "adb")
SERIAL     = os.getenv("ADB_SERIAL", "")
WS_HOST    = "127.0.0.1"
WS_PORT    = int(os.getenv("WS_PORT", "8765"))
SCREEN_W   = int(os.getenv("SCREEN_W", "1920"))
SCREEN_H   = int(os.getenv("SCREEN_H", "1080"))
AIM_GAIN   = float(os.getenv("AIM_GAIN", "0.35"))
TICK_HZ    = int(os.getenv("TICK_HZ", "30"))
CX, CY     = SCREEN_W // 2, SCREEN_H // 2

HOOK_PATH  = Path(__file__).parent / "ff_hook.js"

# ---------------------------------------------------------------- adb
def detect_serial() -> str:
    try:
        out = subprocess.check_output([ADB, "devices"], text=True, timeout=3)
    except FileNotFoundError:
        print(f"[!] '{ADB}' no está en PATH")
        return ""
    except Exception:
        return ""
    for line in out.splitlines()[1:]:
        if "\tdevice" in line:
            return line.split("\t")[0]
    return ""

SERIAL = SERIAL or detect_serial()

def adb(args, timeout=1.5) -> str:
    if not SERIAL:
        return ""
    try:
        r = subprocess.run(
            [ADB, "-s", SERIAL, "shell", *args],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout
    except Exception:
        return ""

def drag(dx: int, dy: int, ms: int = 20):
    if dx == 0 and dy == 0:
        return
    adb(["input", "swipe", str(CX), str(CY),
         str(CX + dx), str(CY + dy), str(ms)])

# ---------------------------------------------------------------- state
class State:
    def __init__(self):
        self.enabled = False
        self.fov_px  = 0
        self.sens    = 1.0
        self.entities = []
state = State()

# ---------------------------------------------------------------- frida
_script = None
_session = None

def frida_start():
    global _script, _session
    if not FRIDA_OK:
        print("[!] frida no instalado — modo sin lectura de memoria")
        return
    if not HOOK_PATH.is_file():
        print(f"[!] Falta {HOOK_PATH.name}")
        return
    try:
        dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
        target = None
        for p in dev.enumerate_processes():
            n = p.name.lower()
            if "free fire" in n or "freefire" in n:
                target = p
                break
        if not target:
            print("[!] Free Fire no encontrado en frida — ábrelo primero")
            return
        print(f"[frida] attach a {target.name} (pid {target.pid})")
        _session = dev.attach(target.pid)
        _script = _session.create_script(HOOK_PATH.read_text(encoding="utf-8"))
        _script.load()
        print("[frida] hook cargado")
    except Exception as e:
        print(f"[frida] error: {e}")

def frida_entities() -> list:
    if not _script:
        return []
    try:
        raw = _script.exports_sync.get_entities()
        out = []
        for e in raw or []:
            try:
                out.append((float(e["x"]), float(e["y"]), float(e.get("d", 0))))
            except Exception:
                continue
        return out
    except Exception:
        return []

# ---------------------------------------------------------------- aim
def pick_target(entities, fov_px):
    best, best_d = None, float("inf")
    for ex, ey, _ in entities:
        dx, dy = ex - CX, ey - CY
        d = math.hypot(dx, dy)
        if d < best_d and (fov_px <= 0 or d <= fov_px):
            best, best_d = (ex, ey), d
    return best

async def aim_loop():
    while True:
        await asyncio.sleep(1.0 / TICK_HZ)
        if not state.enabled:
            continue
        state.entities = frida_entities()
        tgt = pick_target(state.entities, state.fov_px)
        if not tgt:
            continue
        dx = int((tgt[0] - CX) * AIM_GAIN * state.sens)
        dy = int((tgt[1] - CY) * AIM_GAIN * state.sens)
        if abs(dx) < 1 and abs(dy) < 1:
            continue
        await asyncio.to_thread(drag, dx, dy)

# ---------------------------------------------------------------- ws
async def handler(ws):
    print("[ws] cliente conectado")
    try:
        await ws.send(json.dumps({"type": "status", "text": "backend conectado"}))
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "config":
                state.enabled = bool(msg.get("enabled"))
                state.fov_px  = int(float(msg.get("fov", 0)) * 8)
                state.sens    = float(msg.get("sensitivity", 1.0))
                await ws.send(json.dumps({
                    "type": "status",
                    "text": f"aim {'ON' if state.enabled else 'OFF'} · fov {msg.get('fov')}"
                }))
    finally:
        print("[ws] cliente desconectado")

# ---------------------------------------------------------------- preflight
def preflight() -> bool:
    print("=== Preflight ===")
    try:
        out = subprocess.run([ADB, "version"], capture_output=True, text=True, timeout=3)
        first = out.stdout.splitlines()[0] if out.stdout else "?"
        print(f"[adb] {first}")
    except FileNotFoundError:
        print(f"[!] {ADB} no encontrado en PATH")
        return False
    if not SERIAL:
        print("[!] no hay dispositivo en adb devices")
        return False
    print(f"[adb] serial: {SERIAL}")
    pid = adb(["pidof", "com.dts.freefireth"]).strip() or adb(["pidof", "com.dts.freefiremax"]).strip()
    print(f"[game] pid: {pid or 'NO CORRIENDO'}")
    if FRIDA_OK:
        try:
            dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
            n = len(dev.enumerate_processes())
            print(f"[frida-server] OK ({n} procesos)")
        except Exception as e:
            print(f"[frida-server] no responde: {e}")
            print("    Corre en el emulador: adb shell su -c /data/local/tmp/frida-server &")
    else:
        print("[frida] módulo Python no instalado — sin lectura de entidades")
    return True

# ---------------------------------------------------------------- main
async def main():
    if not preflight():
        print("\n[!] Preflight falló. Abortando.")
        return
    frida_start()
    asyncio.create_task(aim_loop())
    async with websockets.serve(handler, WS_HOST, WS_PORT):
        print(f"\n[ws] ws://{WS_HOST}:{WS_PORT} — abre panel.html en el navegador")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] cerrando")