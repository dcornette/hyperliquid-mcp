"""Hyperliquid trading handler — all SDK interaction logic."""

import logging
import time

import eth_account
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid

from .config import Config
from .validation import validate_asset_index, validate_coin_name, validate_order_size

logger = logging.getLogger(__name__)


def _mask_address(address: str) -> str:
    """Mask a wallet address for safe logging."""
    if len(address) >= 10:
        return f"{address[:6]}...{address[-4:]}"
    return "***"


class HyperliquidHandler:
    """Handles all Hyperliquid SDK interactions."""

    def __init__(self, config: Config):
        self.config = config
        self._coin_cache: set[str] | None = None
        self._init_sdk()

    def _init_sdk(self):
        """Initialize Hyperliquid Exchange and Info instances."""
        self.wallet: LocalAccount = eth_account.Account.from_key(self.config.private_key)

        if not self.config.account_address:
            self.config.account_address = self.wallet.address
            logger.info(f"Using wallet: {_mask_address(self.wallet.address)}")
        else:
            logger.info(
                f"Agent mode: wallet {_mask_address(self.wallet.address)} "
                f"signing for {_mask_address(self.config.account_address)}"
            )

        base_url = constants.TESTNET_API_URL if self.config.testnet else constants.MAINNET_API_URL
        logger.info(f"Network: {'testnet' if self.config.testnet else 'mainnet'}")

        self.info = Info(base_url, skip_ws=True)
        self.exchange = Exchange(
            wallet=self.wallet,
            base_url=base_url,
            account_address=self.config.account_address,
            vault_address=self.config.vault_address,
        )

        try:
            user_state = self.info.user_state(self.config.account_address)
            logger.info("Wallet verified successfully")
        except Exception as e:
            logger.warning(f"Could not verify wallet: {e}")

    @property
    def account_address(self) -> str:
        return self.config.account_address

    def _get_valid_coins(self) -> set[str]:
        """Get and cache valid coin names from metadata."""
        if self._coin_cache is None:
            meta = self.info.meta()
            self._coin_cache = {asset["name"] for asset in meta["universe"]}
        return self._coin_cache

    def _resolve_address(self, user_address: str | None) -> str:
        return user_address if user_address else self.account_address

    # --- Order response parsing ---

    def _parse_order_response(self, result: dict) -> dict:
        order_status = result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
        return self._parse_order_status(order_status)

    def _parse_order_status(self, status: dict) -> dict:
        if "resting" in status:
            return {
                "status": "resting",
                "orderId": status["resting"]["oid"],
                "message": "Order resting on order book",
            }
        elif "filled" in status:
            return {
                "status": "filled",
                "orderId": status["filled"]["oid"],
                "totalSize": status["filled"]["totalSz"],
                "averagePrice": status["filled"]["avgPx"],
                "message": "Order filled",
            }
        elif "error" in status:
            return {
                "status": "error",
                "error": status["error"],
                "message": "Order failed",
            }
        return {"status": "unknown", "rawStatus": status}

    # =========================================================================
    # Account & Position Management
    # =========================================================================

    def get_account_info(self, user_address: str = "", dex: str = "") -> dict:
        address = self._resolve_address(user_address)
        result = self.info.user_state(address, dex=dex)
        return {
            "message": "Account information retrieved",
            "data": result,
            "summary": {
                "accountValue": result["marginSummary"]["accountValue"],
                "totalMarginUsed": result["marginSummary"]["totalMarginUsed"],
                "withdrawable": result["withdrawable"],
                "numberOfPositions": len(result["assetPositions"]),
            },
        }

    def get_positions(self, user_address: str = "", dex: str = "") -> dict:
        address = self._resolve_address(user_address)
        result = self.info.user_state(address, dex=dex)
        return {
            "message": "Positions retrieved",
            "data": {
                "assetPositions": result["assetPositions"],
                "marginSummary": result["marginSummary"],
                "crossMarginSummary": result.get("crossMarginSummary"),
                "withdrawable": result["withdrawable"],
            },
            "summary": {
                "numberOfPositions": len(result["assetPositions"]),
                "accountValue": result["marginSummary"]["accountValue"],
                "totalMarginUsed": result["marginSummary"]["totalMarginUsed"],
            },
        }

    def get_balance(self, user_address: str = "", dex: str = "") -> dict:
        address = self._resolve_address(user_address)
        result = self.info.user_state(address, dex=dex)
        ms = result["marginSummary"]
        return {
            "message": "Balance retrieved",
            "data": {
                "accountValue": ms["accountValue"],
                "totalMarginUsed": ms["totalMarginUsed"],
                "totalNtlPos": ms["totalNtlPos"],
                "totalRawUsd": ms["totalRawUsd"],
                "withdrawable": result["withdrawable"],
            },
            "summary": {
                "accountValue": ms["accountValue"],
                "withdrawable": result["withdrawable"],
                "availableBalance": str(float(ms["accountValue"]) - float(ms["totalMarginUsed"])),
            },
        }

    # =========================================================================
    # Order Management
    # =========================================================================

    def place_order(
        self,
        asset: int,
        isBuy: bool,
        size: str,
        price: str = "0",
        reduceOnly: bool = False,
        orderType: dict | None = None,
        cloid: str | None = None,
    ) -> dict:
        meta = self.info.meta()
        universe = meta["universe"]

        validate_asset_index(asset, len(universe))

        size_f = float(size)
        price_f = float(price) if price else 0.0

        validate_order_size(size_f, price_f, self.config.max_order_size)

        coin_name = universe[asset]["name"]
        order_type = orderType or {"limit": {"tif": "Gtc"}}

        if "trigger" in order_type:
            trigger = order_type["trigger"]
            if "triggerPx" in trigger and isinstance(trigger["triggerPx"], str):
                trigger["triggerPx"] = float(trigger["triggerPx"])

        cloid_obj = Cloid(cloid) if cloid else None

        result = self.exchange.order(
            name=coin_name,
            is_buy=isBuy,
            sz=size_f,
            limit_px=price_f,
            order_type=order_type,
            reduce_only=reduceOnly,
            cloid=cloid_obj,
        )

        return {
            "message": f"Order placed for {coin_name}",
            "data": result,
            "orderInfo": self._parse_order_response(result),
        }

    def place_bracket_order(
        self,
        asset: int,
        isBuy: bool,
        size: str,
        takeProfitPrice: str,
        stopLossPrice: str,
        entryPrice: str = "0",
        reduceOnly: bool = False,
        entryOrderType: dict | None = None,
    ) -> dict:
        meta = self.info.meta()
        universe = meta["universe"]

        validate_asset_index(asset, len(universe))

        size_f = float(size)
        entry_price_f = float(entryPrice) if entryPrice else 0.0
        tp_price = float(takeProfitPrice)
        sl_price = float(stopLossPrice)

        validate_order_size(size_f, entry_price_f, self.config.max_order_size)

        coin_name = universe[asset]["name"]
        entry_ot = entryOrderType or {"limit": {"tif": "Gtc"}}

        orders = [
            {
                "coin": coin_name,
                "is_buy": isBuy,
                "sz": size_f,
                "limit_px": entry_price_f,
                "order_type": entry_ot,
                "reduce_only": reduceOnly,
            },
            {
                "coin": coin_name,
                "is_buy": not isBuy,
                "sz": size_f,
                "limit_px": tp_price,
                "order_type": {"trigger": {"triggerPx": tp_price, "isMarket": False, "tpsl": "tp"}},
                "reduce_only": True,
            },
            {
                "coin": coin_name,
                "is_buy": not isBuy,
                "sz": size_f,
                "limit_px": sl_price,
                "order_type": {"trigger": {"triggerPx": sl_price, "isMarket": False, "tpsl": "sl"}},
                "reduce_only": True,
            },
        ]

        result = self.exchange.bulk_orders(orders)

        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        order_infos = []
        labels = ["entry", "take-profit", "stop-loss"]
        for idx, status in enumerate(statuses):
            info = self._parse_order_status(status)
            info["orderType"] = labels[idx] if idx < len(labels) else "unknown"
            order_infos.append(info)

        return {
            "message": "Bracket order placed",
            "data": result,
            "orders": order_infos,
        }

    def cancel_order(self, coin: str, oid: int) -> dict:
        validate_coin_name(coin, self._get_valid_coins())
        result = self.exchange.cancel(coin, oid)
        return {
            "message": f"Order {oid} cancelled for {coin}",
            "data": result,
            "cancelledOrder": {"coin": coin, "orderId": oid},
        }

    def cancel_all_orders(self, user_address: str = "", dex: str = "") -> dict:
        address = self._resolve_address(user_address)
        open_orders = self.info.open_orders(address, dex=dex)

        if not open_orders:
            return {
                "message": "No open orders to cancel",
                "data": {"status": "ok"},
                "cancelledCount": 0,
            }

        cancel_requests = [{"coin": o["coin"], "oid": o["oid"]} for o in open_orders]
        result = self.exchange.bulk_cancel(cancel_requests)
        return {
            "message": f"Cancelled {len(cancel_requests)} orders",
            "data": result,
            "cancelledCount": len(cancel_requests),
        }

    def modify_order(
        self,
        oid: int,
        coin: str,
        isBuy: bool,
        size: str,
        price: str,
        reduceOnly: bool = False,
        orderType: dict | None = None,
    ) -> dict:
        validate_coin_name(coin, self._get_valid_coins())

        size_f = float(size)
        price_f = float(price)

        validate_order_size(size_f, price_f, self.config.max_order_size)

        order_type = orderType or {"limit": {"tif": "Gtc"}}

        result = self.exchange.modify_order(
            oid=oid,
            name=coin,
            is_buy=isBuy,
            sz=size_f,
            limit_px=price_f,
            order_type=order_type,
            reduce_only=reduceOnly,
        )
        return {
            "message": f"Order {oid} modified",
            "data": result,
            "modifiedOrder": {"orderId": oid, "coin": coin, "newPrice": price_f, "newSize": size_f},
        }

    # =========================================================================
    # Order Queries
    # =========================================================================

    def get_open_orders(self, user_address: str = "", dex: str = "") -> dict:
        address = self._resolve_address(user_address)
        result = self.info.open_orders(address, dex=dex)
        return {
            "message": "Open orders retrieved",
            "data": result,
            "summary": {"numberOfOrders": len(result) if result else 0},
        }

    def get_order_status(self, oid: int, user_address: str = "") -> dict:
        address = self._resolve_address(user_address)
        result = self.info.query_order_by_oid(address, oid)
        return {
            "message": "Order status retrieved",
            "data": result,
            "orderId": oid,
        }

    def get_user_fills(
        self,
        startTime: int,
        endTime: int | None = None,
        aggregateByTime: bool = False,
        user_address: str = "",
    ) -> dict:
        address = self._resolve_address(user_address)
        result = self.info.user_fills_by_time(
            user=address,
            start_time=startTime,
            end_time=endTime,
            aggregate_by_time=aggregateByTime,
        )
        return {
            "message": "User fills retrieved",
            "data": result,
            "summary": {
                "numberOfFills": len(result) if result else 0,
                "timeRange": {"startTime": startTime, "endTime": endTime or "current"},
            },
        }

    def get_user_funding(
        self,
        startTime: int,
        endTime: int | None = None,
        user_address: str = "",
    ) -> dict:
        address = self._resolve_address(user_address)
        result = self.info.user_funding(
            user=address,
            start_time=startTime,
            end_time=endTime,
        )
        return {
            "message": "User funding retrieved",
            "data": result,
            "summary": {
                "numberOfEntries": len(result) if result else 0,
                "timeRange": {"startTime": startTime, "endTime": endTime or "current"},
            },
        }

    # =========================================================================
    # Market Data
    # =========================================================================

    def get_meta(self) -> dict:
        result = self.info.meta()
        assets_with_indices = [
            {
                "index": idx,
                "name": asset["name"],
                "maxLeverage": asset["maxLeverage"],
                "onlyIsolated": asset.get("onlyIsolated", False),
            }
            for idx, asset in enumerate(result["universe"])
        ]
        # Refresh coin cache
        self._coin_cache = {a["name"] for a in result["universe"]}
        return {
            "message": "Exchange metadata retrieved",
            "data": result,
            "summary": {
                "numberOfAssets": len(result["universe"]),
                "assetsWithIndices": assets_with_indices,
            },
        }

    def get_all_mids(self) -> dict:
        result = self.info.all_mids()
        return {
            "message": "All mid prices retrieved",
            "data": result,
            "summary": {"numberOfAssets": len(result)},
        }

    def get_order_book(self, coin: str) -> dict:
        validate_coin_name(coin, self._get_valid_coins())
        result = self.info.l2_snapshot(coin)
        return {
            "message": f"Order book for {coin} retrieved",
            "data": result,
            "summary": {
                "coin": coin,
                "bidsCount": len(result["levels"][0]) if result.get("levels") else 0,
                "asksCount": len(result["levels"][1]) if result.get("levels") else 0,
            },
        }

    def get_recent_trades(self, coin: str) -> dict:
        validate_coin_name(coin, self._get_valid_coins())
        result = self.info.recent_trades(coin)
        return {
            "message": f"Recent trades for {coin} retrieved",
            "data": result,
            "summary": {"coin": coin, "numberOfTrades": len(result) if result else 0},
        }

    def get_historical_funding(
        self, coin: str, startTime: int, endTime: int | None = None
    ) -> dict:
        validate_coin_name(coin, self._get_valid_coins())
        result = self.info.funding_history(
            coin=coin, start_time=startTime, end_time=endTime
        )
        return {
            "message": f"Historical funding for {coin} retrieved",
            "data": result,
            "summary": {"coin": coin, "numberOfEntries": len(result) if result else 0},
        }

    def get_candles(
        self, coin: str, interval: str, startTime: int, endTime: int | None = None
    ) -> dict:
        validate_coin_name(coin, self._get_valid_coins())
        result = self.info.candles_snapshot(
            coin=coin, interval=interval, start_time=startTime, end_time=endTime
        )
        return {
            "message": f"Candles for {coin} ({interval}) retrieved",
            "data": result,
            "summary": {
                "coin": coin,
                "interval": interval,
                "numberOfCandles": len(result) if result else 0,
            },
        }

    # =========================================================================
    # Vault Management
    # =========================================================================

    def vault_details(self, vault_address: str) -> dict:
        result = self.info.vault_details(vault_address)
        return {
            "message": "Vault details retrieved",
            "data": result,
            "vaultAddress": vault_address,
        }

    def vault_performance(
        self, vault_address: str, startTime: int, endTime: int | None = None
    ) -> dict:
        result = self.info.vault_details(vault_address, startTime, endTime)
        return {
            "message": "Vault performance retrieved",
            "data": result,
            "summary": {
                "vaultAddress": vault_address,
                "timeRange": {"startTime": startTime, "endTime": endTime or "current"},
            },
        }

    # =========================================================================
    # Utility
    # =========================================================================

    def get_server_time(self) -> dict:
        server_time = int(time.time() * 1000)
        return {
            "message": "Server time retrieved",
            "data": {"serverTime": server_time},
        }
