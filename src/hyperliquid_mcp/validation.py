"""Input validation and error sanitization for security."""


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_order_size(size: float, price: float, max_order_size: float) -> None:
    """Validate order does not exceed maximum notional size."""
    if size <= 0:
        raise ValidationError("Order size must be positive")
    if price < 0:
        raise ValidationError("Order price cannot be negative")
    notional = abs(size * price) if price > 0 else 0
    if max_order_size > 0 and notional > max_order_size:
        raise ValidationError(
            f"Order notional ${notional:,.2f} exceeds limit ${max_order_size:,.2f}. "
            f"Adjust MAX_ORDER_SIZE to change."
        )


def validate_coin_name(coin: str, valid_coins: set[str]) -> None:
    """Validate coin name exists in exchange metadata."""
    if not coin or not coin.strip():
        raise ValidationError("Coin name cannot be empty")
    if coin not in valid_coins:
        raise ValidationError(
            f"Unknown coin '{coin}'. Use hyperliquid_get_meta for perp coins or hyperliquid_get_spot_meta for spot pairs."
        )


def validate_asset_index(asset: int, universe_size: int) -> None:
    """Validate asset index is within bounds."""
    if asset < 0 or asset >= universe_size:
        raise ValidationError(
            f"Asset index {asset} out of range [0, {universe_size - 1}]."
        )


def sanitize_error(error: Exception) -> str:
    """Return a safe error message without leaking arguments or internals."""
    return f"{type(error).__name__}: {error}"
