FROM python:3.12-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

FROM python:3.12-slim

WORKDIR /app

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

RUN useradd --create-home --shell /bin/bash mcp
USER mcp

EXPOSE 8000

CMD ["uvicorn", "hyperliquid_mcp.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
