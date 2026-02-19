# Hyperliquid MCP Server

A Model Context Protocol (MCP) server for Hyperliquid perpetual trading using the official Python SDK. This server provides AI assistants with secure, reliable access to Hyperliquid's trading platform.

> Originally forked from [edkdev/hyperliquid-mcp](https://github.com/edkdev/hyperliquid-mcp). This version adds HTTP transport, Auth0 authentication, Docker deployment, and CI/CD.

## Features

- **Official SDK** - Built on the official Hyperliquid Python SDK with proper EIP-712 signing
- **Complete Coverage** - 21 trading tools: orders, positions, market data, vaults
- **Dual Transport** - stdio for local MCP clients, Streamable HTTP for remote/production
- **Auth0 OAuth** - Full OAuth 2.0 flow for production deployments (works with Claude.ai)
- **Bracket Orders** - Atomic entry + TP + SL order placement
- **Docker Ready** - Multi-stage Dockerfile + Caddy reverse proxy with auto HTTPS
- **Input Validation** - Order size limits, coin name validation, asset index bounds
- **Security** - Error sanitization, address masking in logs, non-root Docker user
- **Testnet Support** - Test strategies safely before going live

## Architecture

```
MCP Client (Claude, Cursor, etc.)
        |  JSON-RPC (stdio or HTTP)
        v
  server.py          <- FastMCP server, 21 @mcp.tool() definitions
        |
  handlers.py        <- HyperliquidHandler: trading logic, SDK interaction
        |
  Hyperliquid Python SDK
        |
  Hyperliquid DEX API
```

Supporting modules:
- `config.py` — Environment-based configuration
- `auth.py` — Optional Auth0 OAuth provider (full OAuth 2.0 flow)
- `validation.py` — Input validation and error sanitization

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) for package management
- A Hyperliquid account with deposited funds

## Installation

### Using uvx (Recommended)

```bash
uvx --from mcp-hyperliquid hyperliquid-mcp
```

### Using pip

```bash
pip install mcp-hyperliquid
hyperliquid-mcp
```

### From Source

```bash
git clone https://github.com/dcornette/hyperliquid-mcp.git
cd hyperliquid-mcp
uv sync
uv run python -m hyperliquid_mcp.server
```

## Configuration

### 1. Register Your Wallet on Hyperliquid

Your wallet must be registered on Hyperliquid before trading.

**Mainnet:** Go to https://app.hyperliquid.xyz, connect your wallet, deposit funds from Arbitrum One.

**Testnet:** Go to https://app.hyperliquid-testnet.xyz, connect your wallet, get testnet funds from the faucet.

### 2. Configure Your MCP Client

#### Claude Desktop / Cursor (stdio mode)

Add to your MCP client config (`claude_desktop_config.json`, `mcp.json`, etc.):

```json
{
  "mcpServers": {
    "hyperliquid": {
      "command": "uvx",
      "args": ["--from", "mcp-hyperliquid", "hyperliquid-mcp"],
      "env": {
        "HYPERLIQUID_PRIVATE_KEY": "0x...",
        "HYPERLIQUID_TESTNET": "false"
      }
    }
  }
}
```

For local development from source:

```json
{
  "mcpServers": {
    "hyperliquid": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/hyperliquid-mcp",
        "run", "python", "-m", "hyperliquid_mcp.server"
      ],
      "env": {
        "HYPERLIQUID_PRIVATE_KEY": "0x...",
        "HYPERLIQUID_TESTNET": "true",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HYPERLIQUID_PRIVATE_KEY` | Yes | — | Wallet private key for signing |
| `HYPERLIQUID_ACCOUNT_ADDRESS` | No | — | For agent/API wallet mode |
| `HYPERLIQUID_VAULT_ADDRESS` | No | — | For vault trading |
| `HYPERLIQUID_TESTNET` | No | `false` | Set `true` for testnet |
| `MAX_ORDER_SIZE` | No | `100000` | Maximum order size limit |
| `AUTH0_DOMAIN` | No | — | Auth0 tenant domain (enables OAuth) |
| `AUTH0_CLIENT_ID` | No | — | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | No | — | Auth0 application client secret |
| `AUTH0_AUDIENCE` | No | — | Auth0 API audience |
| `MCP_BASE_URL` | No | — | Server public URL (e.g. `https://hl.example.com`) |
| `MCP_TRANSPORT` | No | `streamable-http` | Transport: `stdio` or `streamable-http` |
| `MCP_HOST` | No | `0.0.0.0` | Server bind address (HTTP mode) |
| `MCP_PORT` | No | `8000` | Server port (HTTP mode) |
| `DOMAIN` | No | — | Domain for Caddy reverse proxy |

## Transport Modes

### stdio (local MCP clients)

Used by Claude Desktop, Cursor, and other local MCP clients. The client spawns the server process and communicates via stdin/stdout.

```bash
MCP_TRANSPORT=stdio uv run python -m hyperliquid_mcp.server
```

### Streamable HTTP (remote/production)

Used for production deployments. The server runs as an HTTP service behind a reverse proxy.

```bash
# Direct
MCP_TRANSPORT=streamable-http uv run python -m hyperliquid_mcp.server

# Via uvicorn (production)
uvicorn hyperliquid_mcp.server:app --host 0.0.0.0 --port 8000
```

The MCP endpoint is available at `/mcp`.

## Production Deployment

### Docker Compose + Caddy

The project includes a production-ready Docker setup with Caddy as a reverse proxy handling automatic HTTPS via Let's Encrypt.

```bash
# Copy and configure environment
cp .env.production.example .env
# Edit .env with your values

# Run with Docker Compose
docker compose -f docker-compose.prod.yml up -d
```

**Stack:**
- `mcp-server` — Python app running uvicorn (internal port 8000)
- `caddy` — Reverse proxy with auto HTTPS, security headers

The Caddyfile uses a `{$DOMAIN}` environment variable so no domain is hardcoded in the repo.

### GitHub Actions CI/CD

Deployment is automated via GitHub Actions, triggered by pushing a version tag:

```bash
git tag v0.3.0
git push origin v0.3.0
```

The pipeline:
1. Builds the Docker image
2. Pushes to GitHub Container Registry (`ghcr.io`)
3. Copies deployment files to the VPS via SCP
4. SSHs into the VPS and restarts containers

Required GitHub Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `GHCR_TOKEN`.

### VPS Initial Setup

```bash
# Create app directory
mkdir -p ~/hyperliquid-mcp
cd ~/hyperliquid-mcp

# Create .env with your secrets (see .env.production.example)
nano .env
```

## Available Tools

### Account & Position Management

- **`hyperliquid_get_account_info`** - Get complete account summary
- **`hyperliquid_get_positions`** - Get all open positions
- **`hyperliquid_get_balance`** - Get account balance and withdrawable amount

### Order Management

- **`hyperliquid_place_order`** - Place a single order (limit, market, trigger)
- **`hyperliquid_place_bracket_order`** - Place entry + TP + SL atomically
- **`hyperliquid_cancel_order`** - Cancel a specific order
- **`hyperliquid_cancel_all_orders`** - Cancel all open orders
- **`hyperliquid_modify_order`** - Modify an existing order

### Order Queries

- **`hyperliquid_get_open_orders`** - Get all open orders
- **`hyperliquid_get_order_status`** - Get status of specific order
- **`hyperliquid_get_user_fills`** - Get trade fill history
- **`hyperliquid_get_user_funding`** - Get funding payment history

### Market Data

- **`hyperliquid_get_meta`** - Get exchange metadata (assets, leverage, etc.)
- **`hyperliquid_get_all_mids`** - Get current mid prices for all assets
- **`hyperliquid_get_order_book`** - Get order book depth
- **`hyperliquid_get_recent_trades`** - Get recent trades
- **`hyperliquid_get_historical_funding`** - Get funding rate history
- **`hyperliquid_get_candles`** - Get OHLCV candle data (1m, 5m, 15m, 1h, 4h, 1d)

### Vault Management

- **`hyperliquid_vault_details`** - Get vault details
- **`hyperliquid_vault_performance`** - Get vault performance metrics

### Utility

- **`hyperliquid_get_server_time`** - Get server timestamp

## Usage Examples

### Check Account Balance

```
Show me my Hyperliquid account balance
```

### Place a Bracket Order

```
Place a bracket order on Hyperliquid:
- Pair: SOL-USD
- Side: BUY (LONG)
- Size: 4.12 SOL
- Entry: $218.00
- Target: $219.50
- Stop Loss: $216.80
```

This places 3 orders atomically: entry at $218.00, TP trigger at $219.50, SL trigger at $216.80.

### Close a Position

```
Show me my open positions. If I have a SOL position, close it at market price.
```

## Order Types

### Limit Order (Good-Till-Cancel)

```python
order_type = {"limit": {"tif": "Gtc"}}
```

### Market Order (Immediate or Cancel)

```python
price = "0"
order_type = {"limit": {"tif": "Ioc"}}
```

### Trigger Order (Stop Loss / Take Profit)

```python
order_type = {
    "trigger": {
        "triggerPx": "100.5",
        "isMarket": False,
        "tpsl": "tp"  # "tp" or "sl"
    }
}
```

## Code Structure

```
hyperliquid-mcp/
├── src/hyperliquid_mcp/
│   ├── __init__.py
│   ├── server.py          # FastMCP server, 21 tool definitions
│   ├── handlers.py        # Trading logic, SDK interaction
│   ├── config.py          # Environment-based config
│   ├── auth.py            # Auth0 OAuth provider
│   └── validation.py      # Input validation, error sanitization
├── .github/workflows/
│   └── deploy.yml         # CI/CD pipeline
├── Dockerfile             # Multi-stage build, non-root user
├── docker-compose.yml     # Local development
├── docker-compose.prod.yml # Production (ghcr.io image)
├── Caddyfile              # Reverse proxy config
└── pyproject.toml         # Project metadata
```

## Error Handling

### "User or API Wallet does not exist"

Your wallet isn't registered on Hyperliquid. Go to app.hyperliquid.xyz, connect your wallet, and deposit any amount.

### "Order value must be at least $10"

Ensure `size * price >= $10`.

### "Invalid signature"

Check your `HYPERLIQUID_PRIVATE_KEY` matches the registered wallet. If using agent mode, verify `HYPERLIQUID_ACCOUNT_ADDRESS`.

## Agent Mode (Advanced)

Agent mode allows an API wallet to sign transactions for a different trading account.

```bash
HYPERLIQUID_PRIVATE_KEY=0xApiWalletPrivateKey...
HYPERLIQUID_ACCOUNT_ADDRESS=0xMainTradingAccountAddress...
```

Both wallets must be registered, and the main account must approve the API wallet as an agent via the Hyperliquid UI.

## Security Best Practices

1. **Never commit private keys** - Always use environment variables
2. **Use testnet first** - Test strategies before going live
3. **Set up stop losses** - Use bracket orders for risk management
4. **Use agent mode** - For production, keep main account key offline
5. **Enable Auth0** - Protect your HTTP endpoint with OAuth 2.0 authentication
6. **Start small** - Test with minimum order sizes first

## Community

- **[Telegram Group](https://t.me/+fC8GWO3zBe04NTY0)** - Get help, share strategies, and connect with other traders

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Resources

- [Hyperliquid Official Docs](https://hyperliquid.gitbook.io/)
- [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)

## Disclaimer

This software is provided "as is" without warranty. Trading cryptocurrencies carries significant risk. Only trade with funds you can afford to lose. The authors are not responsible for any trading losses.
