"""
AffectEV — tek komutla yerel çalıştırma.

    pip install -r requirements.txt
    python run.py

Tarayıcıda http://127.0.0.1:8000 açılır. (Arayüz frontend/dist içinde derlenmiş olarak gelir;
Node.js gerekmez. Arayüzü değiştirmek isterseniz: cd frontend && npm install && npm run dev)
"""
import os
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

REQUIRED = ["numpy", "scipy", "fastapi", "uvicorn", "pydantic"]
missing = []
for m in REQUIRED:
    try:
        __import__(m)
    except ImportError:
        missing.append(m)
if missing:
    print("Eksik paketler:", ", ".join(missing))
    print("Kurulum:  pip install -r requirements.txt")
    sys.exit(1)

HOST = "127.0.0.1"
PREFERRED_PORT = int(os.environ.get("AFFECTEV_PORT", "8000"))


def _port_free(port: int) -> bool:
    """Portu dinleyen bir sunucu yoksa True (bağlantı denemesiyle; TIME_WAIT durumundan etkilenmez)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) != 0


APP_VERSION = "2.3"   # backend/api.py ile aynı olmalı


def _running_version(port: int):
    """Portta bir AffectEV sunucusu varsa sürümünü ('?' = eski sürüm), yoksa None döndürür."""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=2) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d.get("version", "?") if "osm_timestamp" in d else None
    except Exception:
        return None


def _ask_shutdown(port: int) -> None:
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://{HOST}:{port}/api/shutdown", data=b"", method="POST"),
                               timeout=2)
    except Exception:
        pass


def _open_browser(url: str, delay: float = 1.5):
    if "--no-browser" not in sys.argv:
        threading.Thread(target=lambda: (time.sleep(delay), webbrowser.open(url)), daemon=True).start()


def main():
    import uvicorn
    port = PREFERRED_PORT
    if not _port_free(port):
        ver = _running_version(port)
        if ver == APP_VERSION:
            url = f"http://{HOST}:{port}"
            print(f"AffectEV zaten çalışıyor: {url}  (tarayıcıda açılıyor)")
            if "--no-browser" not in sys.argv:
                webbrowser.open(url)
            return
        if ver is not None:
            print("Eski bir AffectEV sürümü çalışıyor; kapatılıyor...")
            _ask_shutdown(port)
            for _ in range(20):
                time.sleep(0.25)
                if _port_free(port):
                    break
            if not _port_free(port):
                print("  Eski sürüm otomatik kapatılamadı. Açık kalan eski AffectEV penceresini kapatabilirsiniz.")
    if not _port_free(port):
        print(f"{port} numaralı port kullanımda; boş port aranıyor...")
        port = next((p for p in range(PREFERRED_PORT + 1, PREFERRED_PORT + 50) if _port_free(p)), None)
        if port is None:
            print("Boş port bulunamadı. Diğer sunucuları kapatıp tekrar deneyin.")
            sys.exit(1)

    from affectev import face
    if face.CV2_PROBLEM:
        print("UYARI (yüz okuma):", face.CV2_PROBLEM)
    from affectev.network import load_network
    print("Ankara OSM yol ağı yükleniyor...")
    net = load_network()
    print(f"  {net.n_nodes} düğüm, {net.n_edges} kenar (OSM {net.osm_timestamp[:10]})")
    if not os.path.isdir(os.path.join(ROOT, "frontend", "dist")):
        print("UYARI: frontend/dist yok. 'cd frontend && npm install && npm run build' çalıştırın.")
    url = f"http://{HOST}:{port}"
    _open_browser(url)
    print(f"AffectEV çalışıyor: {url}   (durdurmak için Ctrl+C)")
    uvicorn.run("backend.api:app", host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
