"""
MCP Server implementation for joke generation tools.

This server provides two tools:
1. get_dad_joke - Generates random dad jokes
2. get_mom_joke - Generates random mom jokes

The server supports stdio transport for communication.
"""

import asyncio
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .jokes import JokeGenerator


# Initialize joke generator
joke_gen = JokeGenerator()


async def serve() -> None:
    """
    Main server function that sets up and runs the MCP server.

    This function:
    1. Creates an MCP server instance
    2. Registers tool handlers
    3. Starts the stdio transport
    """
    # Create server instance
    server = Server("joke-server")

    @server.list_tools()
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

    @server.call_tool()
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

    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """
    Entry point for the joke MCP server.

    This function is called when the server is started from the command line.
    """
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        # Clean shutdown on Ctrl+C
        sys.stderr.write("\nShutting down server...\n")
        sys.exit(0)
    except Exception as e:
        # Log errors to stderr (not stdout, as per MCP best practices)
        sys.stderr.write(f"Server error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()