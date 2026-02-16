"""Auth0 JWT verification for MCP server."""

import logging
import os

logger = logging.getLogger(__name__)


def create_auth_verifier():
    """Create Auth0 JWT verifier from environment variables.

    Returns None if AUTH0_DOMAIN is not configured (auth disabled for local dev).
    """
    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_AUDIENCE")

    if not domain:
        logger.warning("AUTH0_DOMAIN not set — running WITHOUT authentication")
        return None

    if not audience:
        raise ValueError("AUTH0_AUDIENCE is required when AUTH0_DOMAIN is set")

    # Import here to avoid hard dependency when auth is disabled
    from fastmcp.server.auth.providers.jwt import JWTVerifier

    jwks_uri = f"https://{domain}/.well-known/jwks.json"
    issuer = f"https://{domain}/"

    logger.info(f"Auth0 JWT verification enabled (issuer: {issuer})")

    return JWTVerifier(
        jwks_uri=jwks_uri,
        issuer=issuer,
        audience=audience,
    )
