# language: Python, file: patch.py, target: cualquier SO
import shutil, sys
from pathlib import Path

BRIDGE = r'''
/* ============================================================
   SensiAura aimbot bridge — WebSocket al backend local
   ============================================================ */
const WS_URL = "ws://127.0.0.1:8765";
let aimWS = null;

function aimConnect() {
    if (aimWS && aimWS.readyState <= 1) return;
    aimWS = new WebSocket(WS_URL);
    aimWS.onopen = () => {
        console.log("[aim] backend conectado");
        if (typeof setStatus === "function") setStatus("Backend conectado");
        aimSend();
    };
    aimWS.onmessage = (ev) => {
        try {
            const m = JSON.parse(ev.data);
            if (m.type === "status" && typeof setStatus === "function") setStatus(m.text);
        } catch (_) {}
    };
    aimWS.onclose = () => setTimeout(aimConnect, 2000);
    aimWS.onerror = () => {};
}

function aimSend() {
    if (!aimWS || aimWS.readyState !== 1) return;
    aimWS.send(JSON.stringify({
        type: "config",
        enabled: typeof enabled !== "undefined" ? enabled : false,
        fov: typeof fov !== "undefined" ? Number(fov.value) : 0,
        sensitivity: 1.0
    }));
}

if (typeof power !== "undefined") power.addEventListener("click", () => setTimeout(aimSend, 0));
if (typeof fov !== "undefined") fov.addEventListener("input", () => aimSend());
aimConnect();
'''

def patch(src: Path) -> bool:
    text = src.read_text(encoding="utf-8")
    if "SensiAura aimbot bridge" in text:
        print(f"[=] Ya parchado: {src}")
        return True
    idx = text.find("</script>")
    if idx == -1:
        print(f"[!] No encontré </script> en {src}")
        return False
    backup = src.with_suffix(src.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(src, backup)
        print(f"[+] Backup: {backup.name}")
    text = text[:idx] + BRIDGE + "\n" + text[idx:]
    src.write_text(text, encoding="utf-8")
    print(f"[+] Parchado: {src}")
    return True

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "panel.html"
    if not target.is_file():
        print(f"[!] No existe: {target}")
        sys.exit(1)
    sys.exit(0 if patch(target) else 1)