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
    # Force 0.0.0.0 on Render / Cloud environments regardless of any HOST env var
    is_cloud = bool(os.getenv("RENDER") or os.getenv("PORT") or os.getenv("IS_RENDER"))
    host = "0.0.0.0" if is_cloud else os.getenv("HOST", "0.0.0.0")
    
    # Render assigns its routing port in the PORT environment variable (typically 10000)
    port = int(os.getenv("PORT", "10000" if is_cloud else "8000"))
    
    reload_env = os.getenv("RELOAD", "").lower()
    should_reload = reload_env in ("true", "1") if reload_env else not is_cloud

    print("\n" + "=" * 55)
    print(f"[*] SignalDesk Terminal starting on http://{host}:{port} (Cloud: {is_cloud})")
    print("=" * 55 + "\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=should_reload)
