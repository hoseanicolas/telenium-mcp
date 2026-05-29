# telenium-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that exposes [Telenium](https://github.com/tito/telenium) as tools, enabling LLM-driven automation and testing of [Kivy](https://kivy.org/) applications.

## Overview

telenium-mcp bridges AI assistants (Claude, Kiro, etc.) with Kivy applications by wrapping Telenium's JSON-RPC API into MCP tools. This allows LLMs to:

- Navigate and interact with Kivy UI widgets using XPATH selectors
- Inspect and modify widget properties at runtime
- Execute arbitrary Python code inside the running app
- Take screenshots for visual verification
- Drive end-to-end test scenarios conversationally

```
┌─────────────┐       MCP        ┌───────────────┐     JSON-RPC     ┌──────────────┐
│  LLM Client │ ◄──────────────► │ telenium-mcp  │ ◄──────────────► │  Kivy App    │
│  (Claude,   │   stdio/tools    │   (this pkg)  │   localhost:9901 │  + telenium  │
│   Kiro)     │                  └───────────────┘                  │    client    │
└─────────────┘                                                     └──────────────┘
```

## Prerequisites

- Python 3.10+
- A Kivy application with the [Telenium client](https://github.com/tito/telenium) enabled
- An MCP-compatible client (Claude Desktop, Kiro, VS Code with MCP extension, etc.)

## Installation

```bash
# From source
pip install -e .

# Or with uv
uv pip install -e .
```

## Quick Start

### 1. Start your Kivy app with Telenium

```bash
pip install telenium
python -m telenium.execute your_app/main.py
```

This launches your app with the Telenium JSON-RPC server listening on `localhost:9901`.

### 2. Run the MCP server

```bash
telenium-mcp
```

### 3. Configure your MCP client

Add to your MCP client configuration:

<details>
<summary><strong>Claude Desktop</strong> (~/.claude/claude_desktop_config.json)</summary>

```json
{
  "mcpServers": {
    "telenium": {
      "command": "telenium-mcp",
      "env": {
        "TELENIUM_ALLOWED_HOST": "localhost",
        "TELENIUM_ALLOWED_PORT": "9901"
      }
    }
  }
}
```
</details>

<details>
<summary><strong>Kiro</strong> (.kiro/settings/mcp.json)</summary>

```json
{
  "mcpServers": {
    "telenium": {
      "command": "telenium-mcp",
      "env": {
        "TELENIUM_ALLOWED_HOST": "localhost",
        "TELENIUM_ALLOWED_PORT": "9901"
      }
    }
  }
}
```
</details>

<details>
<summary><strong>VS Code</strong> (.vscode/mcp.json)</summary>

```json
{
  "servers": {
    "telenium": {
      "command": "telenium-mcp",
      "env": {
        "TELENIUM_ALLOWED_HOST": "localhost",
        "TELENIUM_ALLOWED_PORT": "9901"
      }
    }
  }
}
```
</details>

### 4. Start automating

Ask your LLM to interact with the app:

> "Connect to the Kivy app and click the Login button"

The LLM will call `connect`, then `click_on("//Button[@text=\"Login\"]")`.

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TELENIUM_ALLOWED_HOST` | `localhost` | Restrict connections to this host only |
| `TELENIUM_ALLOWED_PORT` | `9901` | Restrict connections to this port only |
| `TELENIUM_MAX_CODE_LENGTH` | `2000` | Max characters for execute/evaluate code |
| `TELENIUM_SELECTOR_MAX_LENGTH` | `500` | Max characters for XPATH selectors |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

See [`.env.example`](.env.example) for a template.

### Security

The host/port allowlist prevents the LLM from connecting to arbitrary network endpoints. Only the configured host and port are permitted. Selector and code length limits provide basic protection against excessively large inputs.

## Available Tools

### Connection

| Tool | Description |
|------|-------------|
| `connect(host, port)` | Connect to a Telenium-enabled Kivy app |
| `version()` | Get the Telenium API version |

### Widget Interaction

| Tool | Description |
|------|-------------|
| `select(selector)` | Find all widgets matching an XPATH selector |
| `element(selector)` | Check if a widget exists (returns bool) |
| `click_on(selector)` | Simulate touch on the first matching widget |
| `wait_click(selector, timeout)` | Wait for a widget to appear, then click it |
| `pick(all)` | Get selector by touching the screen interactively |

### Widget Properties

| Tool | Description |
|------|-------------|
| `getattr_(selector, key)` | Get an attribute from the first matching widget |
| `setattr_(selector, key, value)` | Set an attribute on all matching widgets |

### Code Execution

| Tool | Description |
|------|-------------|
| `execute(code)` | Run Python code in the app (only `app` is available) |
| `evaluate(expr)` | Evaluate an expression and return the result |

### Storage

| Tool | Description |
|------|-------------|
| `select_and_store(key, selector)` | Store a widget reference for later use in execute/evaluate |
| `evaluate_and_store(key, expr)` | Store an expression result for later use |

### Capture

| Tool | Description |
|------|-------------|
| `screenshot(filename)` | Take a PNG screenshot of the app |

## Selector Syntax

telenium-mcp uses Telenium's XPATH-like selector syntax:

```
//ClassName                    # Any widget of this class anywhere in the tree
/Parent/Child                  # Direct descendant
//Parent//Child                # Any descendant (recursive)
//Widget[0]                    # First match (index)
//Widget[@attr="value"]        # Attribute equals
//Widget[@attr!="value"]       # Attribute not equals
//Widget[@attr~="value"]       # Attribute contains
//Widget[@attr!~="value"]      # Attribute does not contain
//Widget[@attr]                # Attribute exists
```

### Examples

```python
# All Labels in the app
"//Label"

# Button with exact text
'//Button[@text="Submit"]'

# First BoxLayout's direct child Button
"//BoxLayout[0]/Button"

# Any TextInput containing "email" in hint_text
'//TextInput[@hint_text~="email"]'

# Disabled buttons
'//Button[@disabled="True"]'
```

## Development

```bash
# Clone
git clone https://github.com/timotihm/telenium-mcp.git
cd telenium-mcp

# Install with dev dependencies
pip install -e ".[dev]"
pip install pytest

# Run tests
pytest

# Run tests with coverage
pytest --cov=telenium_mcp
```

### Project Structure

```
telenium-mcp/
├── src/
│   └── telenium_mcp/
│       ├── __init__.py
│       └── server.py          # MCP server + tool definitions
├── tests/
│   ├── __init__.py
│   └── test_server.py         # Unit tests
├── .env.example               # Environment variable template
├── pyproject.toml              # Package configuration
├── LICENSE                     # MIT
└── README.md
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Not connected" error | Call `connect` tool first before any other tool |
| Connection denied | Check `TELENIUM_ALLOWED_HOST` and `TELENIUM_ALLOWED_PORT` match your app |
| App not responding | Ensure your Kivy app is running with Telenium client enabled |
| Selector returns empty | Use `//` for recursive search; check widget class names with `select("//Widget")` |
| execute returns False | Check app logs for Python exceptions in the executed code |

## License

[MIT](LICENSE)
