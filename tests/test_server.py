"""Unit tests for telenium-mcp server tools."""

from unittest.mock import MagicMock, patch

import pytest

from telenium_mcp import server


@pytest.fixture(autouse=True)
def reset_cli():
    """Reset global client state between tests."""
    server._cli = None
    yield
    server._cli = None


class TestValidation:
    def test_empty_selector_raises(self):
        server._cli = MagicMock()
        with pytest.raises(server.TeleniumError, match="must not be empty"):
            server.select("")

    def test_long_selector_raises(self):
        server._cli = MagicMock()
        with pytest.raises(server.TeleniumError, match="exceeds max length"):
            server.select("x" * 501)

    def test_empty_code_raises(self):
        server._cli = MagicMock()
        with pytest.raises(server.TeleniumError, match="must not be empty"):
            server.execute("")

    def test_long_code_raises(self):
        server._cli = MagicMock()
        with pytest.raises(server.TeleniumError, match="exceeds max length"):
            server.execute("x" * 2001)


class TestConnection:
    def test_require_connection_raises_when_not_connected(self):
        with pytest.raises(server.TeleniumError, match="Not connected"):
            server._require_connection()

    @patch("telenium.connect")
    def test_connect_success(self, mock_connect):
        mock_connect.return_value = MagicMock()
        result = server.connect("localhost", 9901)
        assert "Connected" in result

    def test_connect_disallowed_host(self):
        with pytest.raises(server.TeleniumError, match="denied"):
            server.connect("evil.example.com", 9901)

    def test_connect_disallowed_port(self):
        with pytest.raises(server.TeleniumError, match="denied"):
            server.connect("localhost", 1234)


class TestTools:
    @pytest.fixture(autouse=True)
    def mock_cli(self):
        server._cli = MagicMock()
        yield server._cli

    def test_select(self, mock_cli):
        mock_cli.select.return_value = ["//Label[0]"]
        assert server.select("//Label") == ["//Label[0]"]

    def test_element(self, mock_cli):
        mock_cli.element.return_value = True
        assert server.element("//Button") is True

    def test_click_on(self, mock_cli):
        mock_cli.click_on.return_value = True
        assert server.click_on("//Button") is True

    def test_getattr_empty_key_raises(self, mock_cli):
        with pytest.raises(server.TeleniumError, match="key must not be empty"):
            server.getattr_("//Label", "")

    def test_evaluate(self, mock_cli):
        mock_cli.evaluate.return_value = 42
        assert server.evaluate("1+1") == "42"
