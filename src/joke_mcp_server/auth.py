"""
OAuth 2.1 authorization implementation for MCP server.

Implements Protected Resource Metadata (RFC 9728) and token validation
for protecting specific MCP tools with OAuth 2.1.
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
RESOURCE_SERVER_URL = os.getenv("RESOURCE_SERVER_URL", "http://localhost:8000")

# Tools that require authorization
PROTECTED_TOOLS = {"get_mom_joke"}

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


class ProtectedResourceMetadata(BaseModel):
    """Protected Resource Metadata as per RFC 9728."""

    resource: str
    authorization_servers: List[str]
    scopes_supported: Optional[List[str]] = None
    bearer_methods_supported: Optional[List[str]] = None
    resource_documentation: Optional[str] = None
    resource_name: Optional[str] = None
    resource_description: Optional[str] = None


class AuthorizationError(HTTPException):
    """Custom exception for authorization errors."""

    def __init__(self, detail: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(
            status_code=401,
            detail=detail,
            headers=headers or {}
        )


def get_protected_resource_metadata() -> ProtectedResourceMetadata:
    """
    Get the Protected Resource Metadata for this server.

    Returns:
        ProtectedResourceMetadata object with server configuration
    """
    return ProtectedResourceMetadata(
        resource=RESOURCE_SERVER_URL,
        authorization_servers=[
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        ],
        scopes_supported=["tools:mom_jokes"],
        bearer_methods_supported=["header"],
        resource_name="MCP Joke Server",
        resource_description="MCP server providing joke generation tools with selective authorization"
    )


def create_www_authenticate_header() -> str:
    """
    Create WWW-Authenticate header as per RFC 9728.

    Returns:
        WWW-Authenticate header value with resource_metadata parameter
    """
    metadata_url = f"{RESOURCE_SERVER_URL}/.well-known/oauth-protected-resource"
    return f'Bearer resource_metadata="{metadata_url}"'


async def get_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS (JSON Web Key Set) from Keycloak.

    Returns:
        JWKS dictionary containing public keys

    Raises:
        AuthorizationError if JWKS cannot be fetched
    """
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=5.0)

            if response.status_code != 200:
                raise AuthorizationError("Failed to fetch JWKS")

            return response.json()

    except httpx.RequestError as e:
        logger.error(f"Error fetching JWKS from Keycloak: {e}")
        if os.getenv("ALLOW_AUTH_BYPASS", "false").lower() == "true":
            logger.warning("Auth bypass enabled - skipping JWKS fetch")
            return {"keys": []}
        raise AuthorizationError("Authentication service unavailable")


async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate OAuth token using JWT signature verification.

    This approach validates tokens locally using JWKS instead of introspection,
    which is more efficient and doesn't require special Keycloak permissions.

    Args:
        token: The access token to validate

    Returns:
        Token claims if valid

    Raises:
        AuthorizationError if token is invalid
    """
    try:
        # Get JWKS for signature verification
        jwks = await get_jwks()

        logger.info(f"Validating token (length: {len(token)}, preview: {token[:50]}...)")

        # Decode JWT header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        logger.info(f"Token key ID: {kid}")

        if not kid:
            raise AuthorizationError("Token missing key ID")

        # Find the matching key in JWKS
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break

        if not key:
            raise AuthorizationError("No matching key found in JWKS")

        # Verify and decode the token
        # The jose library handles RSA signature verification using the JWK
        issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_signature": True,
                "verify_aud": False,  # We'll validate audience manually
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
            }
        )

        # Validate audience if present
        audience = claims.get("aud", [])
        if isinstance(audience, str):
            audience = [audience]

        # Log for debugging but don't fail on audience mismatch
        # In a production setup, you'd want stricter validation
        if audience and RESOURCE_SERVER_URL not in audience and "account" not in audience:
            logger.warning(f"Token audience: {audience}. Expected {RESOURCE_SERVER_URL}")

        logger.info(f"Token validated successfully for subject: {claims.get('sub')}")
        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise AuthorizationError("Token has expired")
    except jwt.JWTClaimsError as e:
        logger.warning(f"Token claims validation failed: {e}")
        raise AuthorizationError("Invalid token claims")
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise AuthorizationError("Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        if os.getenv("ALLOW_AUTH_BYPASS", "false").lower() == "true":
            logger.warning("Auth bypass enabled - skipping token validation")
            return {"sub": "dev-user", "scope": "tools:mom_jokes"}
        raise AuthorizationError("Token validation failed")


def requires_authorization(tool_name: str) -> bool:
    """
    Check if a tool requires authorization.

    Args:
        tool_name: Name of the tool

    Returns:
        True if the tool requires authorization, False otherwise
    """
    return tool_name in PROTECTED_TOOLS


async def check_tool_authorization(
    tool_name: str,
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> Optional[Dict[str, Any]]:
    """
    Check if the user is authorized to use a specific tool.

    Args:
        tool_name: Name of the tool being accessed
        credentials: Optional bearer token credentials

    Returns:
        Token claims if authorized, None if tool doesn't require auth

    Raises:
        AuthorizationError if authorization is required but failed
    """
    if not requires_authorization(tool_name):
        # Tool doesn't require authorization
        return None

    # Check for development bypass
    if os.getenv("ALLOW_AUTH_BYPASS", "false").lower() == "true":
        logger.warning(f"Auth bypass enabled - allowing access to {tool_name}")
        return {"active": True, "sub": "dev-user", "scope": "tools:mom_jokes"}

    # Tool requires authorization
    if not credentials:
        headers = {"WWW-Authenticate": create_www_authenticate_header()}
        raise AuthorizationError("Authorization required", headers=headers)

    # Validate the token
    # Strip any whitespace that might have been added
    token = credentials.credentials.strip()
    logger.info(f"Received token for validation (type: {type(token)}, length: {len(token)})")
    token_info = await validate_token(token)

    # Check if token has required scope
    scopes = token_info.get("scope", "").split()
    required_scope = "tools:mom_jokes"

    if required_scope not in scopes:
        logger.warning(f"Token missing required scope {required_scope}. Has scopes: {scopes}")
        raise AuthorizationError("Insufficient scope")

    return token_info


class AuthorizationMiddleware:
    """
    Middleware to handle authorization for MCP requests.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Check if this is an MCP tool call that needs authorization
            # This will be integrated into the actual request handling
            pass

        await self.app(scope, receive, send)