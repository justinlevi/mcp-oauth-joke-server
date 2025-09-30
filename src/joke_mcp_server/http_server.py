"""
HTTP transport implementation for the MCP joke server.

This module provides a Streamable HTTP transport layer for the MCP server,
enabling web-based clients to interact with the joke generation tools.
"""

import sys
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import uvicorn

logger = logging.getLogger(__name__)
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from mcp.server import Server
from mcp.types import Tool, TextContent

from .jokes import JokeGenerator
from .auth import (
    get_protected_resource_metadata,
    check_tool_authorization,
    requires_authorization,
    AuthorizationError,
    bearer_scheme
)


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

# Configure CORS to allow MCP Inspector and other clients
# In production, be more restrictive with allowed origins
import os

cors_origins = [
    "http://localhost:6274",    # MCP Inspector default port
    "http://localhost:3000",    # Common dev server port
    "http://127.0.0.1:6274",    # MCP Inspector on 127.0.0.1
    "http://127.0.0.1:3000",    # Dev server on 127.0.0.1
]

# Allow all origins in development mode
if os.getenv("ALLOW_AUTH_BYPASS", "false").lower() == "true":
    cors_origins = ["*"]  # Allow all origins in dev mode

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS for preflight
    allow_headers=["*"],  # Allow all headers including Authorization
    expose_headers=["WWW-Authenticate", "Content-Type"],  # Expose necessary headers
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


@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    """
    Protected Resource Metadata endpoint as per RFC 9728.

    Returns metadata about this resource server and its authorization requirements.
    """
    metadata = get_protected_resource_metadata()
    return JSONResponse(content=metadata.model_dump(exclude_none=True))




async def _handle_mcp_message(
    message: dict,
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> JSONResponse:
    """
    Internal handler for MCP protocol messages.

    Args:
        message: The JSON-RPC message to handle
        credentials: Optional bearer token credentials

    Returns:
        JSONResponse with the result or error
    """
    method = message.get("method")

    if method == "tools/list":
        tools = await list_tools()
        logger.info(f"tools/list called with credentials: {bool(credentials)}")
        # Filter tools based on authorization status
        accessible_tools = []
        for tool in tools:
            # Check if tool requires authorization
            if requires_authorization(tool.name):
                # Only include protected tools if user is authenticated
                if credentials:
                    try:
                        # Validate token to check if user has access
                        # This will check the token and scopes
                        logger.info(f"Checking authorization for protected tool: {tool.name}")
                        await check_tool_authorization(tool.name, credentials)
                        # User is authorized, include the tool
                        logger.info(f"User authorized for tool: {tool.name}")
                        accessible_tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                        })
                    except AuthorizationError as e:
                        # User is authenticated but lacks required scope
                        # Don't include this tool
                        logger.info(f"Authorization failed for {tool.name}: {e}")
                        pass
                else:
                    logger.info(f"No credentials provided, skipping protected tool: {tool.name}")
                # If no credentials, don't include protected tools
            else:
                # Public tool, always include
                accessible_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                })

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": accessible_tools
                },
            }
        )

    elif method == "tools/call":
        params = message.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # Check authorization for protected tools
        try:
            await check_tool_authorization(tool_name, credentials)
        except AuthorizationError as e:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e.detail),
                    },
                },
                status_code=e.status_code,
                headers=e.headers
            )

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
async def handle_mcp_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
):
    """
    Standard MCP endpoint for Streamable HTTP transport.

    This is the primary endpoint that MCP Inspector and other clients use.
    Processes JSON-RPC messages according to the MCP protocol.
    """
    try:
        message = await request.json()
        return await _handle_mcp_message(message, credentials)
    except AuthorizationError as e:
        # Authorization errors should be handled with proper headers
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e.detail),
                },
            },
            status_code=e.status_code,
            headers=e.headers
        )
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