"""
Tests for the HTTP MCP server.

Tests HTTP endpoints and SSE functionality.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from joke_mcp_server.http_server import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test that root endpoint returns server information."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Joke MCP Server"
        assert data["version"] == "0.1.0"
        assert "transport" in data
        assert "endpoints" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that health check endpoint works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_initialize_message():
    """Test MCP initialize message handling."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        response = await client.post("/mcp", json=message)
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"


@pytest.mark.asyncio
async def test_list_tools_message():
    """Test MCP tools/list message handling."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = await client.post("/mcp", json=message)
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        assert "result" in data
        tools = data["result"]["tools"]
        assert len(tools) == 2

        # Check dad joke tool
        dad_tool = next(t for t in tools if t["name"] == "get_dad_joke")
        assert dad_tool is not None
        assert "description" in dad_tool
        assert "inputSchema" in dad_tool

        # Check mom joke tool
        mom_tool = next(t for t in tools if t["name"] == "get_mom_joke")
        assert mom_tool is not None
        assert "description" in mom_tool
        assert "inputSchema" in mom_tool


@pytest.mark.asyncio
async def test_call_dad_joke_tool():
    """Test calling the dad joke tool via MCP protocol."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_dad_joke", "arguments": {}},
        }
        response = await client.post("/mcp", json=message)
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 3
        assert "result" in data
        content = data["result"]["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"
        assert len(content[0]["text"]) > 0


@pytest.mark.asyncio
async def test_call_mom_joke_tool():
    """Test calling the mom joke tool requires authorization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without authorization, mom joke should return 401
        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_mom_joke", "arguments": {}},
        }
        response = await client.post("/mcp", json=message)

        # Check if auth is bypassed for testing
        import os
        if os.getenv("ALLOW_AUTH_BYPASS") == "true":
            # In test mode with auth bypass, should work
            assert response.status_code == 200
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == 4
            assert "result" in data
            content = data["result"]["content"]
            assert len(content) > 0
            assert content[0]["type"] == "text"
            assert len(content[0]["text"]) > 0
        else:
            # In production mode, should require auth
            assert response.status_code == 401
            assert "WWW-Authenticate" in response.headers


@pytest.mark.asyncio
async def test_call_invalid_tool():
    """Test calling an invalid tool returns an error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "invalid_tool", "arguments": {}},
        }
        response = await client.post("/mcp", json=message)
        assert response.status_code == 500
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
async def test_invalid_method():
    """Test that invalid methods return an error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        message = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "invalid/method",
            "params": {},
        }
        response = await client.post("/mcp", json=message)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601