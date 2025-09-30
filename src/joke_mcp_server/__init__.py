"""
Joke MCP Server - A Model Context Protocol server for joke generation.

This package provides:
- Dad joke generation tool
- Mom joke generation tool
- stdio transport support
- HTTP/SSE transport support
"""

from .jokes import JokeGenerator

__version__ = "0.1.0"
__all__ = ["JokeGenerator"]
