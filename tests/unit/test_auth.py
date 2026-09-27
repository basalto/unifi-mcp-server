"""Unit tests for src/auth.py StaticTokenAuth."""

import pytest

from src.auth import StaticTokenAuth


class TestStaticTokenAuthInit:
    """Tests for StaticTokenAuth constructor."""

    def test_requires_non_empty_token(self):
        with pytest.raises(ValueError):
            StaticTokenAuth("")

    def test_accepts_token(self):
        auth = StaticTokenAuth("secret-token")
        assert auth is not None


class TestStaticTokenAuthVerify:
    """Tests for StaticTokenAuth.verify_token."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_access_token(self):
        auth = StaticTokenAuth("secret-token")
        result = await auth.verify_token("secret-token")
        assert result is not None
        assert result.token == "secret-token"
        assert result.client_id == "unifi-mcp-server"
        assert result.scopes == []

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        auth = StaticTokenAuth("secret-token")
        assert await auth.verify_token("wrong-token") is None

    @pytest.mark.asyncio
    async def test_empty_token_returns_none(self):
        auth = StaticTokenAuth("secret-token")
        assert await auth.verify_token("") is None

    @pytest.mark.asyncio
    async def test_case_sensitive(self):
        auth = StaticTokenAuth("Secret-Token")
        assert await auth.verify_token("secret-token") is None
        assert await auth.verify_token("Secret-Token") is not None

    @pytest.mark.asyncio
    async def test_prefix_not_accepted(self):
        auth = StaticTokenAuth("secret-token")
        assert await auth.verify_token("secret-token-extra") is None
