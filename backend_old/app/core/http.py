"""Shared httpx AsyncClient with keep-alive connection pooling."""
import httpx

http_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0,
    ),
    follow_redirects=True,
)
