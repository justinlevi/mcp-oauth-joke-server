"""
HTTP transport implementation for the MCP joke server.

This module provides a Streamable HTTP transport layer for the MCP server,
enabling web-based clients to interact with the joke generation tools.
"""

import sys
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mcp.server import Server
from mcp.types import Tool, TextContent

from .jokes import JokeGenerator


# Initialize joke generator
joke_gen = JokeGenerator()

# Create MCP server instance
mcp_server = Server("joke-server-http")


# Store active sessions
sessions: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles server startup and shutdown.
    """
    # Startup
    sys.stderr.write("Starting HTTP MCP server...\n")
    yield
    # Shutdown
    sys.stderr.write("Shutting down HTTP MCP server...\n")


# Create FastAPI application
app = FastAPI(
    title="Joke MCP Server",
    description="MCP server providing dad and mom joke generation via HTTP/SSE",
    version="0.1.0",
    lifespan=lifespan,
)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available tools.

    Returns:
        List of Tool objects describing available joke generators
    """
    return [
        Tool(
            name="get_dad_joke",
            description="Get a random dad joke. Dad jokes are known for being cheesy, "
            "corny, and often involving puns or wordplay. Perfect for groans and eye rolls!",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_mom_joke",
            description="Get a random mom joke. These are classic sayings and phrases "
            "that mothers often use. Nostalgic and relatable!",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool execution requests.

    Args:
        name: Name of the tool to execute
        arguments: Tool arguments (not used for joke tools)

    Returns:
        List containing a TextContent with the joke

    Raises:
        ValueError: If tool name is not recognized
    """
    if name == "get_dad_joke":
        joke = joke_gen.get_dad_joke()
        return [TextContent(type="text", text=joke)]
    elif name == "get_mom_joke":
        joke = joke_gen.get_mom_joke()
        return [TextContent(type="text", text=joke)]
    else:
        raise ValueError(f"Unknown tool: {name}")


@app.get("/")
async def root():
    """Root endpoint providing server information."""
    return {
        "name": "Joke MCP Server",
        "version": "0.1.0",
        "description": "MCP server providing dad and mom joke generation tools",
        "transport": "streamable-http",
        "endpoints": {
            "mcp": "/mcp",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}




async def _handle_mcp_message(message: dict) -> JSONResponse:
    """
    Internal handler for MCP protocol messages.

    Args:
        message: The JSON-RPC message to handle

    Returns:
        JSONResponse with the result or error
    """
    method = message.get("method")

    if method == "tools/list":
        tools = await list_tools()
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                        }
                        for tool in tools
                    ]
                },
            }
        )

    elif method == "tools/call":
        params = message.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = await call_tool(tool_name, arguments)

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "content": [{"type": r.type, "text": r.text} for r in result]
                },
            }
        )

    elif method == "initialize":
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "joke-server-http",
                        "version": "0.1.0",
                    },
                },
            }
        )

    else:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            },
            status_code=400,
        )


@app.post("/mcp")
async def handle_mcp_endpoint(request: Request):
    """
    Standard MCP endpoint for Streamable HTTP transport.

    This is the primary endpoint that MCP Inspector and other clients use.
    Processes JSON-RPC messages according to the MCP protocol.
    """
    try:
        message = await request.json()
        return await _handle_mcp_message(message)
    except Exception as e:
        sys.stderr.write(f"Error handling MCP message: {e}\n")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            },
            status_code=500,
        )




def main(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Start the HTTP MCP server.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)
    """
    sys.stderr.write(f"Starting HTTP MCP server on {host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()