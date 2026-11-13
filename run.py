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
    # Always bind to 0.0.0.0 by default.
    # 0.0.0.0 works universally on both local Windows (accessible via localhost/127.0.0.1)
    # and all cloud hosts (Render, Docker, Koyeb, AWS) where external routing is required.
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "10000" if os.getenv("RENDER") else "8000"))
    reload_env = os.getenv("RELOAD", "").lower()
    is_prod = bool(os.getenv("RENDER") or os.getenv("PORT"))
    should_reload = reload_env in ("true", "1") if reload_env else not is_prod

    print("\n" + "=" * 55)
    print(f"[*] SignalDesk Terminal starting on http://{host}:{port}")
    print("=" * 55 + "\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=should_reload)
