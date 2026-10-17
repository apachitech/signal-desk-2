import sys
from pathlib import Path

# Ensure project root is on sys.path for Vercel Serverless environment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app as fastapi_app

class VercelPathMiddleware:
    """
    Vercel Serverless Function rewrites pass the destination path (e.g. /api/index.py)
    into ASGI scope['path']. This middleware restores the real requested path
    from Vercel's 'x-matched-path' header so FastAPI router matches /api/signal,
    /api/backtest, /api/config, etc.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))
            # Check for Vercel's x-matched-path header
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8")
            if matched_path:
                path_only = matched_path.split("?")[0]
                scope["path"] = path_only
                scope["raw_path"] = path_only.encode("utf-8")
        await self.app(scope, receive, send)

app = VercelPathMiddleware(fastapi_app)
