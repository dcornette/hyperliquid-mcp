"""Auth0 OAuth provider for MCP server."""

import logging
import os

logger = logging.getLogger(__name__)


def create_auth_verifier():
    """Create Auth0 OAuth provider from environment variables.

    Returns None if AUTH0_DOMAIN is not configured (auth disabled for local dev).
    Uses Auth0Provider for full OAuth flow (authorize, token, discovery endpoints).
    """
    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_AUDIENCE")
    client_id = os.getenv("AUTH0_CLIENT_ID")
    client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    base_url = os.getenv("MCP_BASE_URL")

    if not domain:
        logger.warning("AUTH0_DOMAIN not set — running WITHOUT authentication")
        return None

    if not all([client_id, client_secret, audience, base_url]):
        raise ValueError(
            "AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_AUDIENCE, and MCP_BASE_URL "
            "are required when AUTH0_DOMAIN is set"
        )

    from fastmcp.server.auth.providers.auth0 import Auth0Provider

    config_url = f"https://{domain}/.well-known/openid-configuration"

    logger.info(f"Auth0 OAuth enabled (domain: {domain})")

    return Auth0Provider(
        config_url=config_url,
        client_id=client_id,
        client_secret=client_secret,
        audience=audience,
        base_url=base_url,
    )
