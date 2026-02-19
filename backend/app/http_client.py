"""HTTP client with retry and timeout configuration."""

import httpx
from typing import Any


class HTTPClient:
    """Async HTTP client wrapper with retry and timeout."""
    
    def __init__(
        self,
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        retries: int = 1,
    ):
        """Initialize HTTP client with custom transport.
        
        Args:
            timeout: Default timeout for all operations
            connect_timeout: Timeout for establishing connection
            retries: Number of retries for failed requests
        """
        timeout_config = httpx.Timeout(
            timeout,
            connect=connect_timeout,
            read=timeout,
            write=timeout,
            pool=connect_timeout,
        )
        
        # Use AsyncHTTPTransport for retry configuration
        transport = httpx.AsyncHTTPTransport(retries=retries)
        
        self.client = httpx.AsyncClient(
            timeout=timeout_config,
            transport=transport,
            follow_redirects=True,
        )
    
    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a GET request.
        
        Args:
            url: URL to fetch
            params: Query parameters
            headers: Additional headers
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: On HTTP errors
            httpx.TimeoutException: On timeout
        """
        return await self.client.get(url, params=params, headers=headers)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Global client instance (initialized on demand)
_http_client: HTTPClient | None = None


async def get_http_client() -> HTTPClient:
    """Get or create global HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClient()
    return _http_client


async def close_http_client() -> None:
    """Close global HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.close()
        _http_client = None
