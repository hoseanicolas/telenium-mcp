# Telenium MCP Server - Setup Guide

Setup MCP server untuk remote control Kivy app via AI assistant (any client yang support MCP SSE).

## Requirements

- Linux server (Debian/Ubuntu)
- Python 3.10+
- Port 8901 terbuka

## Install (5 menit)

```bash
# 1. Buat folder
sudo mkdir -p /opt/telenium-mcp
sudo chown $USER:$USER /opt/telenium-mcp
cd /opt/telenium-mcp

# 2. Buat venv + install deps
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" telenium requests uvicorn starlette

# 3. Buat server.py (lihat section "Source Code" di bawah)

# 4. Buat server_wrapper.py (lihat section "Source Code" di bawah)

# 5. Test
.venv/bin/python -c "from server import mcp; print('OK')"
```

## Auto-start (systemd)

```bash
sudo tee /etc/systemd/system/telenium-mcp.service > /dev/null << 'EOF'
[Unit]
Description=Telenium MCP Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/telenium-mcp/.venv/bin/python /opt/telenium-mcp/server_wrapper.py
WorkingDirectory=/opt/telenium-mcp
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telenium-mcp
sudo systemctl start telenium-mcp
sudo systemctl status telenium-mcp
```

## Verify

```bash
# Dari server sendiri (akan hang - normal, SSE streaming):
curl -s http://localhost:8901/sse

# Dari network lain:
curl -s http://<SERVER_IP>:8901/sse
```

## Register di AI Gateway (LiteLLM / dll)

| Field | Value |
|-------|-------|
| Name | `telenium` |
| URL | `http://<DOCKER_GATEWAY_IP>:8901/sse` |
| Transport | SSE |
| Auth | none |
| Access | Public |

> Jika LiteLLM jalan di Docker, gunakan Docker gateway IP (biasanya `172.17.0.1`).
> Jika LiteLLM jalan di host yang sama, gunakan `http://localhost:8901/sse`.

## Register di MCP Client (Kiro / OpenCode / Claude / dll)

### OpenCode (`~/.config/opencode/opencode.jsonc`):
```jsonc
{
  "mcp": {
    "telenium": {
      "type": "sse",
      "url": "http://<SERVER_IP>:8901/sse",
      "enabled": true
    }
  }
}
```

### Kiro (`.kiro/settings/mcp.json` - local stdio mode):
```json
{
  "mcpServers": {
    "telenium": {
      "command": "/opt/telenium-mcp/.venv/bin/python",
      "args": ["/opt/telenium-mcp/server.py"],
      "env": {
        "TELENIUM_ALLOWED_HOST": "localhost",
        "TELENIUM_ALLOWED_PORT": "9901"
      }
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "telenium": {
      "command": "/opt/telenium-mcp/.venv/bin/python",
      "args": ["/opt/telenium-mcp/server.py"]
    }
  }
}
```

## Tools Available

| Tool | Fungsi |
|------|--------|
| `connect(host, port)` | Connect ke device |
| `status()` | Cek connection status |
| `version()` | API version |
| `execute(code)` | Jalankan Python di app |
| `evaluate(expr)` | Eval expression, return value |
| `select(selector)` | Cari widget (XPATH-like) |
| `click_on(selector)` | Klik widget |
| `screenshot()` | Screenshot (base64 PNG) |
| `getattr_(selector, key)` | Ambil atribut widget |
| `setattr_(selector, key, value)` | Set atribut widget |
| `wait_click(selector, timeout)` | Tunggu widget muncul + klik |
| `pick(all)` | Identify widget by touch |
| `select_and_store(key, selector)` | Simpan widget reference |
| `evaluate_and_store(key, expr)` | Simpan eval result |

## Connect ke Device

Device harus menjalankan Kivy app dengan Telenium enabled (port 9901).

```
# Direct (device reachable dari server):
AI: "connect ke 192.168.1.101:9901"

# Via reverse tunnel (device di jaringan lain):
# Dari laptop yang satu jaringan dengan device:
ssh -N -R 9901:<DEVICE_IP>:9901 <SERVER_IP>
# Lalu AI: "connect ke localhost:9901"
```

### Multi-device:
```bash
ssh -N -R 9901:<DEVICE1_IP>:9901 -R 9902:<DEVICE2_IP>:9901 -R 9903:<DEVICE3_IP>:9901 <SERVER_IP>
```
AI: `"connect ke localhost:9901"` / `"connect ke localhost:9902"` / `"connect ke localhost:9903"`

---

## Source Code

### server.py

```python
"""Telenium MCP Server - exposes Kivy app automation as MCP tools."""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

import telenium

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "telenium",
    instructions=(
        "Automate Kivy applications via Telenium. "
        "Use 'connect' first to establish a connection to a device IP, then interact with "
        "widgets using XPATH selectors like //ClassName[@attr=\"value\"]. "
        "Multiple devices can be managed by calling connect with different host IPs."
    ),
)

_cli: Any = None
_connected_host: str = ""
_connected_port: int = 0

MAX_CODE_LENGTH = int(os.environ.get("TELENIUM_MAX_CODE_LENGTH", "2000"))
SELECTOR_MAX_LENGTH = int(os.environ.get("TELENIUM_SELECTOR_MAX_LENGTH", "500"))


class TeleniumError(Exception):
    """Raised when a Telenium operation fails."""


def _require_connection() -> Any:
    if _cli is None:
        raise TeleniumError("Not connected. Call 'connect' first.")
    return _cli


def _validate_selector(selector: str) -> str:
    selector = selector.strip()
    if not selector:
        raise TeleniumError("Selector must not be empty.")
    if len(selector) > SELECTOR_MAX_LENGTH:
        raise TeleniumError(f"Selector exceeds max length ({SELECTOR_MAX_LENGTH}).")
    return selector


@mcp.tool()
def connect(host: str = "localhost", port: int = 9901) -> str:
    """Connect to a running Telenium-enabled Kivy application.

    Args:
        host: IP address or hostname of the device running the Kivy app.
        port: Port of the Telenium server (default 9901).
    """
    global _cli, _connected_host, _connected_port
    _cli = telenium.connect(host, port)
    _connected_host = host
    _connected_port = port
    logger.info("Connected to %s:%d", host, port)
    return f"Connected to {host}:{port}"


@mcp.tool()
def status() -> str:
    """Return current connection status."""
    if _cli is None:
        return "Not connected"
    return f"Connected to {_connected_host}:{_connected_port}"


@mcp.tool()
def version() -> int:
    """Return the Telenium API version of the connected app."""
    return _require_connection().version()


@mcp.tool()
def select(selector: str) -> list[str]:
    """Return unique selectors for all widgets matching the XPATH selector.

    Args:
        selector: XPATH-like selector, e.g. //Label or //Button[@text="OK"]
    """
    return _require_connection().select(_validate_selector(selector))


@mcp.tool()
def element(selector: str) -> bool:
    """Check if at least one widget matches the selector.

    Args:
        selector: XPATH-like selector.
    """
    return _require_connection().element(_validate_selector(selector))


@mcp.tool()
def getattr_(selector: str, key: str) -> str:
    """Get an attribute value from the first widget matching the selector.

    Args:
        selector: XPATH-like selector.
        key: Attribute name to retrieve.
    """
    if not key.strip():
        raise TeleniumError("Attribute key must not be empty.")
    return _require_connection().getattr(_validate_selector(selector), key.strip())


@mcp.tool()
def setattr_(selector: str, key: str, value: str) -> bool:
    """Set an attribute on all widgets matching the selector.

    Args:
        selector: XPATH-like selector.
        key: Attribute name to set.
        value: Value to assign.
    """
    if not key.strip():
        raise TeleniumError("Attribute key must not be empty.")
    return _require_connection().setattr(_validate_selector(selector), key.strip(), value)


@mcp.tool()
def click_on(selector: str) -> bool:
    """Simulate a touch event on the first widget matching the selector.

    Args:
        selector: XPATH-like selector.
    """
    return _require_connection().click_on(_validate_selector(selector))


@mcp.tool()
def wait_click(selector: str, timeout: float = 10.0) -> bool:
    """Wait for a widget to appear, then click it.

    Args:
        selector: XPATH-like selector.
        timeout: Max seconds to wait (-1 for infinite, default 10).
    """
    return _require_connection().wait_click(_validate_selector(selector), timeout=timeout)


@mcp.tool()
def execute(code: str) -> bool:
    """Execute Python code inside the running Kivy app. Only 'app' is available.

    Args:
        code: Python code to execute (max length controlled by TELENIUM_MAX_CODE_LENGTH).
    """
    code = code.strip()
    if not code:
        raise TeleniumError("Code must not be empty.")
    if len(code) > MAX_CODE_LENGTH:
        raise TeleniumError(f"Code exceeds max length ({MAX_CODE_LENGTH} chars).")
    return _require_connection().execute(code)


@mcp.tool()
def evaluate(expr: str) -> str:
    """Evaluate a Python expression in the app and return the serializable result.

    Args:
        expr: Python expression to evaluate.
    """
    expr = expr.strip()
    if not expr:
        raise TeleniumError("Expression must not be empty.")
    if len(expr) > MAX_CODE_LENGTH:
        raise TeleniumError(f"Expression exceeds max length ({MAX_CODE_LENGTH} chars).")
    return str(_require_connection().evaluate(expr))


@mcp.tool()
def screenshot(filename: str | None = None) -> dict:
    """Take a PNG screenshot of the running app.

    Args:
        filename: Optional path to save the screenshot. Returns base64 data regardless.
    """
    return _require_connection().screenshot(filename)


@mcp.tool()
def pick(all: bool = False) -> str | list[str]:
    """Return the selector of the next widget touched on screen.

    Args:
        all: If True, return all widgets in the touch path.
    """
    return _require_connection().pick(all=all)


@mcp.tool()
def select_and_store(key: str, selector: str) -> bool:
    """Select a widget and store it in the id-map for use in execute/evaluate.

    Args:
        key: Variable name to store the widget reference.
        selector: XPATH-like selector.
    """
    if not key.strip():
        raise TeleniumError("Key must not be empty.")
    return _require_connection().select_and_store(key.strip(), _validate_selector(selector))


@mcp.tool()
def evaluate_and_store(key: str, expr: str) -> bool:
    """Evaluate an expression and store the result in the id-map.

    Args:
        key: Variable name to store the result.
        expr: Python expression to evaluate.
    """
    if not key.strip():
        raise TeleniumError("Key must not be empty.")
    expr = expr.strip()
    if not expr:
        raise TeleniumError("Expression must not be empty.")
    return _require_connection().evaluate_and_store(key.strip(), expr)


def main():
    """Entry point for the MCP server."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
    mcp.run()


if __name__ == "__main__":
    main()
```

### server_wrapper.py

```python
"""Wrapper that disables host validation for MCP SSE server."""
import os
os.environ["MCP_TRANSPORT"] = "sse"
os.environ["MCP_HOST"] = "0.0.0.0"
os.environ["MCP_PORT"] = "8901"

from starlette.types import ASGIApp, Receive, Scope, Send

class HostRewriteMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            new_headers = []
            for k, v in scope.get("headers", []):
                if k == b"host":
                    new_headers.append((b"host", b"localhost:8901"))
                else:
                    new_headers.append((k, v))
            scope = dict(scope)
            scope["headers"] = new_headers
        await self.app(scope, receive, send)

import sys
sys.path.insert(0, "/opt/telenium-mcp")
from server import mcp

import uvicorn

app = HostRewriteMiddleware(mcp.sse_app())
uvicorn.run(app, host="0.0.0.0", port=8901)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Unhealthy di LiteLLM | `sudo systemctl restart telenium-mcp` |
| Connection refused | Cek port 8901 open: `ss -tlnp \| grep 8901` |
| Invalid Host header | Pastikan pakai `server_wrapper.py` (bukan `server.py` langsung) |
| Device not reachable | Cek tunnel aktif / device satu jaringan |
| `Not connected` error | AI harus call `connect(host, port)` dulu sebelum action lain |
