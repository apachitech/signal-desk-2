import sys
from pathlib import Path

# Ensure project root is in sys.path for Netlify Serverless environment
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mangum import Mangum
from app.main import app

# Mangum translates Netlify/AWS Lambda events to ASGI and back
handler = Mangum(app, lifespan="off")
