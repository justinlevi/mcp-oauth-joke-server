# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that provides dad and mom joke generation tools with dual transport support (stdio and HTTP/SSE) and OAuth 2.1 authorization.

## Development Commands

### Installation
```bash
# Install all dependencies (including dev)
uv sync --all-extras
```

### Running the Server
```bash
# Stdio transport (for local MCP clients)
uv run joke-server

# HTTP transport with SSE (runs on http://127.0.0.1:8000)
uv run python -m joke_mcp_server.http_server

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory /Users/jwinter/projects/mcp run joke-server
```

### Authorization Setup (for protected tools)
```bash
# Start Keycloak and PostgreSQL
docker-compose up -d

# Follow manual setup in scripts/setup-keycloak.sh
# Key environment variables:
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=mcp
export RESOURCE_SERVER_URL=http://localhost:8000
```

### Testing
```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_jokes.py

# Run specific test
uv run pytest tests/test_jokes.py::TestJokeGenerator::test_get_dad_joke_returns_string

# Generate coverage report
uv run pytest --cov=joke_mcp_server --cov-report=html
```

## Architecture

### Core Components

1. **`src/joke_mcp_server/jokes.py`** - Business logic
   - `JokeGenerator` class with dad/mom joke collections
   - Supports reproducible testing with seed parameter

2. **`src/joke_mcp_server/server.py`** - Stdio MCP server
   - Entry point: `joke-server` command
   - Implements MCP protocol over stdin/stdout
   - Exposes `get_dad_joke` and `get_mom_joke` tools

3. **`src/joke_mcp_server/http_server.py`** - HTTP/SSE transport
   - FastAPI application on port 8000
   - Endpoints: `/mcp` (main), `/health`, `/.well-known/oauth-protected-resource`
   - Stateless JSON-RPC 2.0 message handling

4. **`src/joke_mcp_server/auth.py`** - OAuth 2.1 authorization
   - Implements RFC 9728 (Protected Resource Metadata)
   - `get_mom_joke` requires authorization, `get_dad_joke` is public
   - Keycloak integration for token validation
   - Set `ALLOW_AUTH_BYPASS=true` for development without auth

### MCP Protocol Implementation

- **Protocol Version**: 2024-11-05
- **Supported Methods**: `initialize`, `tools/list`, `tools/call`
- **Transport**: stdio (primary), HTTP/SSE (alternative)
- **Tools**:
  - `get_dad_joke` - Public, returns random dad joke
  - `get_mom_joke` - Protected (requires `tools:mom_jokes` scope), returns random mom saying

### Testing Strategy

- **Unit tests** in `tests/test_jokes.py` - JokeGenerator logic
- **Integration tests** in `tests/test_http_server.py` - HTTP endpoints
- **Authorization tests** in `tests/test_authorization.py` - OAuth flow
- All async tests use `pytest-asyncio`
- Test configuration in `pytest.ini`

## Key Development Patterns

1. **Adding New Tools**:
   - Add tool definition in both `server.py` and `http_server.py` `list_tools()`
   - Implement handler in `call_tool()` functions
   - Add business logic to appropriate module
   - Write tests following existing patterns
   - For protected tools, add to `PROTECTED_TOOLS` in `auth.py`

2. **Authorization Flow**:
   - Protected tools return 401 with `WWW-Authenticate` header
   - Client discovers auth server from `/.well-known/oauth-protected-resource`
   - Token validation via Keycloak introspection
   - Scope-based access control (`tools:mom_jokes`)

3. **Error Handling**:
   - Stdio: errors to stderr, protocol to stdout
   - HTTP: JSON-RPC error responses with appropriate status codes
   - Authorization: 401 with RFC 9728 compliant headers

4. **Environment Variables**:
   - `KEYCLOAK_URL` (default: `http://localhost:8080`)
   - `KEYCLOAK_REALM` (default: `mcp`)
   - `RESOURCE_SERVER_URL` (default: `http://localhost:8000`)
   - `ALLOW_AUTH_BYPASS` (set to `true` for dev without auth)

## Dependencies

Managed via `uv` package manager (faster alternative to pip):
- **Core**: `mcp>=1.0.0`, `fastapi>=0.115.0`, `uvicorn>=0.30.0`
- **Auth**: `python-jose[cryptography]>=3.3.0`, `python-keycloak>=4.0.0`
- **Testing**: `pytest>=8.0.0`, `pytest-asyncio>=0.24.0`, `pytest-cov>=5.0.0`

Full dependencies in `pyproject.toml`, locked versions in `uv.lock`.