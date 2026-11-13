import os
import sys
from pathlib import Path
import uvicorn

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if __name__ == "__main__":
    # In cloud environments (Render, Koyeb, Docker), bind to 0.0.0.0
    # On local Windows, default to 127.0.0.1 unless specified
    default_host = "0.0.0.0" if os.getenv("RENDER") or os.getenv("PORT") else "127.0.0.1"
    host = os.getenv("HOST", default_host)
    port = int(os.getenv("PORT", "8000"))
    is_prod = bool(os.getenv("RENDER"))
    print("\n" + "=" * 55)
    print(f"[*] SignalDesk Terminal starting on http://{host}:{port}")
    print("=" * 55 + "\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=not is_prod)
