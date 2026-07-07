"""Wrapper that disables host validation for MCP SSE server."""
import os
os.environ["MCP_TRANSPORT"] = "sse"
os.environ["MCP_HOST"] = "0.0.0.0"
os.environ["MCP_PORT"] = "8901"

# Monkey-patch to disable host checking in starlette
import starlette.requests
original_host = starlette.requests.Request.url_for
# No need - let's just use a simple ASGI middleware

from starlette.types import ASGIApp, Receive, Scope, Send

class HostRewriteMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            # Rewrite headers to set Host = localhost:8901
            headers = dict(scope.get("headers", []))
            new_headers = []
            for k, v in scope.get("headers", []):
                if k == b"host":
                    new_headers.append((b"host", b"localhost:8901"))
                else:
                    new_headers.append((k, v))
            scope = dict(scope)
            scope["headers"] = new_headers
        await self.app(scope, receive, send)

# Import and run
import sys
sys.path.insert(0, "/opt/telenium-mcp")
from server import mcp

import uvicorn

app = HostRewriteMiddleware(mcp.sse_app())
uvicorn.run(app, host="0.0.0.0", port=8901)
