"""Centralized configuration loaded from environment variables."""

import os


class Config:
    """Application configuration."""

    def __init__(self):
        # Hyperliquid SDK
        self.private_key: str = self._require("HYPERLIQUID_PRIVATE_KEY")
        self.account_address: str | None = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS") or None
        self.vault_address: str | None = os.getenv("HYPERLIQUID_VAULT_ADDRESS") or None
        self.testnet: bool = os.getenv("HYPERLIQUID_TESTNET", "").lower() == "true"

        # Security limits
        self.max_order_size: float = float(os.getenv("MAX_ORDER_SIZE", "100000"))

        # Auth0
        self.auth0_domain: str | None = os.getenv("AUTH0_DOMAIN")
        self.auth0_client_id: str | None = os.getenv("AUTH0_CLIENT_ID")
        self.auth0_client_secret: str | None = os.getenv("AUTH0_CLIENT_SECRET")
        self.auth0_audience: str | None = os.getenv("AUTH0_AUDIENCE")
        self.base_url: str | None = os.getenv("MCP_BASE_URL")

        # Server
        self.host: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("MCP_PORT", "8000"))
        self.transport: str = os.getenv("MCP_TRANSPORT", "streamable-http")

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise ValueError(f"{name} environment variable is required")
        return value
