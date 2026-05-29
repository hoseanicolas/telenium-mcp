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
        "Use 'connect' first to establish a connection, then interact with "
        "widgets using XPATH selectors like //ClassName[@attr=\"value\"]."
    ),
)

_cli: Any = None

ALLOWED_HOST = os.environ.get("TELENIUM_ALLOWED_HOST", "localhost")
ALLOWED_PORT = int(os.environ.get("TELENIUM_ALLOWED_PORT", "9901"))
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
        host: Hostname of the Telenium server (restricted by TELENIUM_ALLOWED_HOST env var).
        port: Port of the Telenium server (restricted by TELENIUM_ALLOWED_PORT env var).
    """
    global _cli
    if host != ALLOWED_HOST:
        raise TeleniumError(
            f"Connection to '{host}' denied. Allowed host: '{ALLOWED_HOST}'. "
            "Set TELENIUM_ALLOWED_HOST env var to change."
        )
    if port != ALLOWED_PORT:
        raise TeleniumError(
            f"Connection to port {port} denied. Allowed port: {ALLOWED_PORT}. "
            "Set TELENIUM_ALLOWED_PORT env var to change."
        )
    _cli = telenium.connect(host, port)
    logger.info("Connected to %s:%d", host, port)
    return f"Connected to {host}:{port}"


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
        value: Value to assign (as string, will be interpreted by Kivy).
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
