import httpx
from contextlib import asynccontextmanager

class AsyncHttpClient:
    client: httpx.AsyncClient = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls.client is None or cls.client.is_closed:
            cls.client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
        return cls.client

    @classmethod
    async def close_client(cls):
        if cls.client is not None:
            await cls.client.aclose()
            cls.client = None

async_http_client = AsyncHttpClient()
