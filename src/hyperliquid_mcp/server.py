"""Hyperliquid MCP Server — FastMCP with HTTP transport and Auth0 authentication."""

import json
import logging
import sys

from fastmcp import FastMCP

from .auth import create_auth_verifier
from .config import Config
from .handlers import HyperliquidHandler
from .validation import sanitize_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize
config = Config()
auth_verifier = create_auth_verifier()

mcp = FastMCP(
    "hyperliquid-mcp",
    auth=auth_verifier,
)

handler = HyperliquidHandler(config)


def _ok(result: dict) -> str:
    return json.dumps(result, indent=2)


def _err(e: Exception) -> str:
    return json.dumps({"error": sanitize_error(e)}, indent=2)


# =============================================================================
# Account & Position Management
# =============================================================================


@mcp.tool()
def hyperliquid_get_account_info(userAddress: str = "", dex: str = "") -> str:
    """Get user's perpetual account summary including positions and margin."""
    try:
        return _ok(handler.get_account_info(userAddress, dex))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_positions(userAddress: str = "", dex: str = "") -> str:
    """Get user's open positions with margin summary."""
    try:
        return _ok(handler.get_positions(userAddress, dex))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_balance(userAddress: str = "", dex: str = "") -> str:
    """Get user's account balance and withdrawable amount."""
    try:
        return _ok(handler.get_balance(userAddress, dex))
    except Exception as e:
        return _err(e)


# =============================================================================
# Order Management
# =============================================================================


@mcp.tool()
def hyperliquid_place_order(
    asset: int,
    isBuy: bool,
    size: str,
    price: str = "0",
    reduceOnly: bool = False,
    orderType: dict | None = None,
    cloid: str | None = None,
) -> str:
    """Place a single order on Hyperliquid. Minimum order value is $10. Use asset index from get_meta (e.g., 0=BTC, 1=ETH, 5=SOL)."""
    try:
        return _ok(handler.place_order(asset, isBuy, size, price, reduceOnly, orderType, cloid))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_place_bracket_order(
    asset: int,
    isBuy: bool,
    size: str,
    takeProfitPrice: str,
    stopLossPrice: str,
    entryPrice: str = "0",
    reduceOnly: bool = False,
    entryOrderType: dict | None = None,
) -> str:
    """Place a bracket order (entry + take profit + stop loss) atomically. Minimum order value is $10."""
    try:
        return _ok(handler.place_bracket_order(
            asset, isBuy, size, takeProfitPrice, stopLossPrice, entryPrice, reduceOnly, entryOrderType
        ))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_cancel_order(coin: str, oid: int) -> str:
    """Cancel a specific order by coin name and order ID (oid)."""
    try:
        return _ok(handler.cancel_order(coin, oid))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_cancel_all_orders(userAddress: str = "", dex: str = "") -> str:
    """Cancel all open orders for the user."""
    try:
        return _ok(handler.cancel_all_orders(userAddress, dex))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_modify_order(
    oid: int,
    coin: str,
    isBuy: bool,
    size: str,
    price: str,
    reduceOnly: bool = False,
    orderType: dict | None = None,
) -> str:
    """Modify an existing order."""
    try:
        return _ok(handler.modify_order(oid, coin, isBuy, size, price, reduceOnly, orderType))
    except Exception as e:
        return _err(e)


# =============================================================================
# Order Queries
# =============================================================================


@mcp.tool()
def hyperliquid_get_open_orders(userAddress: str = "", dex: str = "") -> str:
    """Get user's currently open orders."""
    try:
        return _ok(handler.get_open_orders(userAddress, dex))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_order_status(oid: int, userAddress: str = "") -> str:
    """Get the status of a specific order by oid."""
    try:
        return _ok(handler.get_order_status(oid, userAddress))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_user_fills(
    startTime: int,
    endTime: int | None = None,
    aggregateByTime: bool = False,
    userAddress: str = "",
) -> str:
    """Get user's historical trade fills."""
    try:
        return _ok(handler.get_user_fills(startTime, endTime, aggregateByTime, userAddress))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_user_funding(
    startTime: int,
    endTime: int | None = None,
    userAddress: str = "",
) -> str:
    """Get user's funding payment history."""
    try:
        return _ok(handler.get_user_funding(startTime, endTime, userAddress))
    except Exception as e:
        return _err(e)


# =============================================================================
# Market Data
# =============================================================================


@mcp.tool()
def hyperliquid_get_meta() -> str:
    """Get exchange metadata including all available trading assets with their indices, names, max leverage, and trading parameters."""
    try:
        return _ok(handler.get_meta())
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_all_mids() -> str:
    """Get current mid prices for all assets."""
    try:
        return _ok(handler.get_all_mids())
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_order_book(coin: str) -> str:
    """Get order book (market depth) for a specific asset."""
    try:
        return _ok(handler.get_order_book(coin))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_recent_trades(coin: str) -> str:
    """Get recent trades for a specific asset."""
    try:
        return _ok(handler.get_recent_trades(coin))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_historical_funding(
    coin: str, startTime: int, endTime: int | None = None
) -> str:
    """Get historical funding rates for an asset."""
    try:
        return _ok(handler.get_historical_funding(coin, startTime, endTime))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_get_candles(
    coin: str, interval: str, startTime: int, endTime: int | None = None
) -> str:
    """Get historical candle/OHLCV data for an asset. Intervals: 1m, 5m, 15m, 1h, 4h, 1d."""
    try:
        return _ok(handler.get_candles(coin, interval, startTime, endTime))
    except Exception as e:
        return _err(e)


# =============================================================================
# Vault Management
# =============================================================================


@mcp.tool()
def hyperliquid_vault_details(vaultAddress: str) -> str:
    """Get detailed information about a specific vault."""
    try:
        return _ok(handler.vault_details(vaultAddress))
    except Exception as e:
        return _err(e)


@mcp.tool()
def hyperliquid_vault_performance(
    vaultAddress: str, startTime: int, endTime: int | None = None
) -> str:
    """Get performance metrics for a specific vault."""
    try:
        return _ok(handler.vault_performance(vaultAddress, startTime, endTime))
    except Exception as e:
        return _err(e)


# =============================================================================
# Utility
# =============================================================================


@mcp.tool()
def hyperliquid_get_server_time() -> str:
    """Get estimated server time."""
    try:
        return _ok(handler.get_server_time())
    except Exception as e:
        return _err(e)


# =============================================================================
# Entry points
# =============================================================================

# ASGI app for uvicorn (production)
app = mcp.http_app(path="/mcp", stateless_http=True)


def main():
    """CLI entry point (backward compatible with stdio)."""
    try:
        mcp.run(
            transport=config.transport,
            host=config.host,
            port=config.port,
            stateless_http=True,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
