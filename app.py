"""Vercel FastAPI entrypoint.

Vercel's Python runtime can auto-detect FastAPI apps when an `app = FastAPI()`
instance is exported from common entrypoints like `app.py` or `index.py`.

We keep our main implementation in `api.py` and re-export the ASGI app here.
"""

from api import app

