"""Integration tests using TestClient."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "cache" in data
    
    def test_ready(self, client):
        """Test ready endpoint returns 200."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True


class TestEarthquakeEndpoints:
    """Test earthquake endpoints (requires internet)."""
    
    @pytest.mark.parametrize("endpoint", [
        "/v1/earthquake/latest",
        "/v1/earthquake/recent",
        "/v1/earthquake/felt",
    ])
    def test_earthquake_endpoints(self, client, endpoint):
        """Test earthquake endpoints return valid data."""
        response = client.get(endpoint)
        
        # Should return 200 or 502 (if BMKG is down)
        assert response.status_code in [200, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "meta" in data
            assert "attribution" in data
            assert "BMKG" in data["attribution"]
            
            # Check cache headers
            assert "X-Cache" in response.headers
            assert response.headers["X-Cache"] in ["HIT", "MISS"]
    
    def test_earthquake_latest_structure(self, client):
        """Test latest earthquake has required fields."""
        response = client.get("/v1/earthquake/latest")
        
        if response.status_code != 200:
            pytest.skip("BMKG API unavailable")
        
        data = response.json()["data"]
        
        # Check required fields
        assert "datetime" in data
        assert "magnitude" in data
        assert "depth_km" in data
        assert "lat" in data
        assert "lon" in data
        assert "region" in data
        
        # Check types
        assert isinstance(data["magnitude"], (int, float))
        assert isinstance(data["lat"], (int, float))
        assert isinstance(data["lon"], (int, float))
    
    def test_earthquake_nearby(self, client):
        """Test nearby earthquake search."""
        response = client.get("/v1/earthquake/nearby?lat=-6.2&lon=106.8&radius_km=500")
        
        assert response.status_code in [200, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "meta" in data
            assert "center" in data["meta"]
            assert "radius_km" in data["meta"]


class TestAPIFeatures:
    """Test API features like CORS and rate limiting."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/v1/earthquake/latest",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        assert "access-control-allow-origin" in response.headers
        # Starlette returns the origin for credentialed requests
        assert response.headers["access-control-allow-origin"] in ["*", "http://example.com"]
    
    def test_docs_accessible(self, client):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "fastapi" in response.text.lower()
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "BMKG API"
