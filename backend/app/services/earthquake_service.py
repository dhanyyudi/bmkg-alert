"""Earthquake service for fetching and caching earthquake data."""

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any

from app.cache import cache
from app.config import settings
from app.http_client import get_http_client
from app.models.earthquake import Earthquake, EarthquakeWithDistance
from app.parsers.earthquake_parser import parse_earthquake, parse_earthquake_list
from app.services.notification_service import notification_service


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate (decimal degrees)
        lat2, lon2: Second coordinate (decimal degrees)
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


class EarthquakeService:
    """Service for earthquake data operations."""
    
    def __init__(self):
        """Initialize earthquake service."""
        self.base_url = settings.bmkg_earthquake_base_url
    
    def _make_cache_key(self, endpoint: str, params: dict | None = None) -> str:
        """Generate cache key for endpoint."""
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"earthquake:{endpoint}:{params_hash}"
        return f"earthquake:{endpoint}"
    
    async def _fetch_from_bmkg(self, endpoint: str) -> dict[str, Any]:
        """Fetch data from BMKG API.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Parsed JSON response
            
        Raises:
            Exception: On fetch or parse errors
        """
        url = f"{self.base_url}/{endpoint}"
        client = await get_http_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to fetch from BMKG: {str(e)}")
    
    async def _get_cached_or_fetch(
        self,
        endpoint: str,
        ttl: int,
    ) -> tuple[dict[str, Any], bool]:
        """Get data from cache or fetch from BMKG.
        
        Args:
            endpoint: API endpoint
            ttl: Cache TTL in seconds
            
        Returns:
            Tuple of (data, from_cache)
        """
        cache_key = self._make_cache_key(endpoint)
        
        # Try cache first
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached, True
        
        # Fetch from BMKG
        data = await self._fetch_from_bmkg(endpoint)
        
        # Store in cache
        await cache.set(cache_key, data, ttl)
        
        return data, False
    
    async def get_latest(self) -> tuple[Earthquake, bool, int]:
        """Get latest earthquake.
        
        Returns:
            Tuple of (earthquake, from_cache, ttl)
        """
        data, from_cache = await self._get_cached_or_fetch(
            "autogempa.json",
            settings.cache_ttl_earthquake_latest,
        )
        
        earthquakes = parse_earthquake_list(data)
        
        # Check for injected simulation
        simulated_data = await cache.get("simulation:earthquakes")
        if simulated_data:
            # If simulation exists, prepend it (making it the "latest")
            for eq_data in simulated_data:
                 try:
                    sim_eq = Earthquake(**eq_data)
                    earthquakes.insert(0, sim_eq)
                 except Exception:
                    pass

        if not earthquakes:
            raise Exception("No earthquake data found")
        
        # Get remaining TTL
        cache_key = self._make_cache_key("autogempa.json")
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_earthquake_latest
        
        return earthquakes[0], from_cache, ttl
    
    async def get_recent(self) -> tuple[list[Earthquake], bool, int]:
        """Get recent earthquakes (M 5.0+).
        
        Returns:
            Tuple of (earthquakes, from_cache, ttl)
        """
        data, from_cache = await self._get_cached_or_fetch(
            "gempaterkini.json",
            settings.cache_ttl_earthquake_list,
        )
        
        earthquakes = parse_earthquake_list(data)

        # Check for injected simulation
        simulated_data = await cache.get("simulation:earthquakes")
        if simulated_data:
             for eq_data in simulated_data:
                 try:
                    sim_eq = Earthquake(**eq_data)
                    earthquakes.insert(0, sim_eq)
                 except Exception:
                    pass
        
        # Get remaining TTL
        cache_key = self._make_cache_key("gempaterkini.json")
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_earthquake_list
        
        return earthquakes, from_cache, ttl
    
    async def get_felt(self) -> tuple[list[Earthquake], bool, int]:
        """Get felt earthquakes.
        
        Returns:
            Tuple of (earthquakes, from_cache, ttl)
        """
        data, from_cache = await self._get_cached_or_fetch(
            "gempadirasakan.json",
            settings.cache_ttl_earthquake_list,
        )
        
        earthquakes = parse_earthquake_list(data)
        
        # Get remaining TTL
        cache_key = self._make_cache_key("gempadirasakan.json")
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_earthquake_list
        
        return earthquakes, from_cache, ttl
    
    async def get_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: float = 200,
    ) -> tuple[list[EarthquakeWithDistance], dict[str, Any]]:
        """Get earthquakes near a coordinate.
        
        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Search radius in km
            
        Returns:
            Tuple of (earthquakes with distance, metadata)
        """
        # Fetch both recent and felt earthquakes
        recent_data, _ = await self._get_cached_or_fetch(
            "gempaterkini.json",
            settings.cache_ttl_earthquake_list,
        )
        felt_data, _ = await self._get_cached_or_fetch(
            "gempadirasakan.json",
            settings.cache_ttl_earthquake_list,
        )
        
        # Parse all earthquakes
        recent_eqs = parse_earthquake_list(recent_data)
        felt_eqs = parse_earthquake_list(felt_data)
        
        # Combine and remove duplicates (by datetime and magnitude)
        seen = set()
        all_eqs = []
        for eq in recent_eqs + felt_eqs:
            key = (eq.occurred_at.isoformat(), eq.magnitude)
            if key not in seen:
                seen.add(key)
                all_eqs.append(eq)
        
        # Calculate distances and filter
        nearby = []
        for eq in all_eqs:
            distance = haversine_distance(lat, lon, eq.lat, eq.lon)
            if distance <= radius_km:
                # Create EarthquakeWithDistance using model_dump and then create new instance
                eq_data = eq.model_dump()
                eq_data["distance_km"] = round(distance, 2)
                eq_with_dist = EarthquakeWithDistance.model_validate(eq_data)
                nearby.append(eq_with_dist)
        
        # Sort by distance
        nearby.sort(key=lambda x: x.distance_km)
        
        meta = {
            "center": {"lat": lat, "lon": lon},
            "radius_km": radius_km,
            "count": len(nearby),
            "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
            "cache_ttl": settings.cache_ttl_earthquake_list,
        }
        
        return nearby, meta


    async def inject_earthquake(self, earthquake: Earthquake):
        """Inject a simulated earthquake."""
        key = "simulation:earthquakes"
        current = await cache.get(key)
        if not current:
            current = []
        
        # Serialize and append
        current.append(earthquake.model_dump(mode='json'))
        # Set 5 minute TTL for simulations
        await cache.set(key, current, ttl=300) 
        
        # Dispatch notification
        await notification_service.dispatch(earthquake)
        
    async def clear_simulations(self):
        """Clear all active simulations."""
        await cache.delete("simulation:earthquakes")


# Global service instance
earthquake_service = EarthquakeService()
