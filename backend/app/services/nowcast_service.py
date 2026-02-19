"""Nowcast service for fetching and caching weather warnings."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.cache import cache
from app.services.notification_service import notification_service
from app.config import settings
from app.http_client import get_http_client
from app.models.nowcast import ActiveProvince, Warning, LocationCheckResult, NowcastDetailResponse
from app.parsers.rss_parser import parse_rss_feed
from app.parsers.cap_parser import parse_cap_xml


class NowcastService:
    """Service for nowcast (weather warning) data operations."""
    
    def __init__(self):
        """Initialize nowcast service."""
        self.base_url = settings.bmkg_nowcast_base_url
    
    def _make_cache_key(self, endpoint: str, params: dict | None = None) -> str:
        """Generate cache key for endpoint."""
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"nowcast:{endpoint}:{params_hash}"
        return f"nowcast:{endpoint}"
    
    async def _fetch_rss_feed(self, language: str) -> str:
        """Fetch RSS feed from BMKG.
        
        Args:
            language: Language code (id/en)
            
        Returns:
            Raw RSS XML content
            
        Raises:
            Exception: On fetch errors
        """
        url = f"{self.base_url}/{language}"
        client = await get_http_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to fetch RSS feed: {str(e)}")
    
    async def _fetch_cap_xml(self, alert_code: str, language: str) -> str:
        """Fetch CAP XML for a specific alert.
        
        Args:
            alert_code: Alert code/ID (e.g., 'CBT20260216004')
            language: Language code (id/en)
            
        Returns:
            Raw CAP XML content
            
        Raises:
            Exception: On fetch errors
        """
        url = f"{self.base_url}/{language}/{alert_code}_alert.xml"
        client = await get_http_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to fetch CAP XML for {alert_code}: {str(e)}")
    
    async def _get_cached_or_fetch_rss(
        self,
        language: str,
        ttl: int,
    ) -> tuple[list[ActiveProvince], bool]:
        """Get RSS data from cache or fetch from BMKG.
        
        Args:
            language: Language code
            ttl: Cache TTL in seconds
            
        Returns:
            Tuple of (provinces, from_cache)
        """
        cache_key = self._make_cache_key("rss", {"lang": language})
        
        # Try cache first
        cached = await cache.get(cache_key)
        if cached is not None:
            # Parse cached data back to models
            provinces = [ActiveProvince(**p) for p in cached]
            return provinces, True
        
        # Fetch from BMKG
        xml_content = await self._fetch_rss_feed(language)
        provinces = parse_rss_feed(xml_content, language)
        
        # Store in cache (serialize to dict)
        cache_data = [p.model_dump(mode='json') for p in provinces]
        await cache.set(cache_key, cache_data, ttl)
        
        return provinces, False
    
    async def _get_cached_or_fetch_cap(
        self,
        alert_code: str,
        language: str,
        ttl: int,
    ) -> tuple[Warning | None, bool]:
        """Get CAP data from cache or fetch from BMKG.
        
        Args:
            alert_code: Alert code/ID
            language: Language code
            ttl: Cache TTL in seconds
            
        Returns:
            Tuple of (warning, from_cache)
        """
        cache_key = self._make_cache_key("cap", {"code": alert_code, "lang": language})
        
        # Try cache first
        cached = await cache.get(cache_key)
        if cached is not None:
            warning = Warning(**cached)
            return warning, True
        
        # Fetch from BMKG
        xml_content = await self._fetch_cap_xml(alert_code, language)
        warning = parse_cap_xml(xml_content)
        
        if warning:
            # Store in cache (serialize to dict)
            await cache.set(cache_key, warning.model_dump(mode='json'), ttl)
        
        return warning, False
    
    async def get_active_provinces(
        self,
        language: str = "id",
    ) -> tuple[list[ActiveProvince], bool, int]:
        """Get list of provinces with active warnings.
        
        Args:
            language: Language code (id/en)
            
        Returns:
            Tuple of (provinces, from_cache, ttl)
        """
        provinces, from_cache = await self._get_cached_or_fetch_rss(
            language,
            settings.cache_ttl_nowcast,
        )
        
        # Get remaining TTL
        cache_key = self._make_cache_key("rss", {"lang": language})
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_nowcast
        
        return provinces, from_cache, ttl
    
    async def get_warning_detail(
        self,
        alert_code: str,
        language: str = "id",
    ) -> tuple[Warning | None, str, bool, int]:
        """Get detailed warning for an alert code.
        
        Args:
            alert_code: Alert code/ID (e.g., 'CBT20260216004')
            language: Language code (id/en)
            
        Returns:
            Tuple of (warning, region_name, from_cache, ttl)
        """
        warning, from_cache = await self._get_cached_or_fetch_cap(
            alert_code,
            language,
            settings.cache_ttl_nowcast,
        )
        
        # Get remaining TTL
        cache_key = self._make_cache_key("cap", {"code": alert_code, "lang": language})
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_nowcast
        
        # Extract region name from warning areas or headline
        region_name = "Unknown"
        if warning:
            if warning.areas and warning.areas[0].name:
                region_name = warning.areas[0].name
            elif warning.headline:
                # Try to extract from headline: "Hujan Lebat di Banten"
                if ' di ' in warning.headline:
                    region_name = warning.headline.split(' di ')[-1]
        
        return warning, region_name, from_cache, ttl
    
    async def check_location(
        self,
        location: str,
        language: str = "id",
    ) -> tuple[LocationCheckResult, bool, int]:
        """Check warnings for a specific location.
        
        Args:
            location: Location/kecamatan name to search for
            language: Language code (id/en)
            
        Returns:
            Tuple of (result, from_cache, ttl)
        """
        # First, get all active provinces
        provinces, _ = await self._get_cached_or_fetch_rss(
            language,
            settings.cache_ttl_nowcast,
        )
        
        matching_warnings = []
        
        # Check each province's CAP for location match
        for province in provinces:
            try:
                warning, _ = await self._get_cached_or_fetch_cap(
                    province.code,
                    language,
                    settings.cache_ttl_nowcast,
                )
                
                if warning and warning.description:
                    # Check if location is mentioned in description
                    # Case-insensitive search
                    location_lower = location.lower()
                    desc_lower = warning.description.lower()
                    headline_lower = warning.headline.lower() if warning.headline else ""
                    
                    if location_lower in desc_lower or location_lower in headline_lower:
                        # Location found in this warning
                        matching_warnings.append(warning)
            except Exception:
                # Skip failed fetches
                continue
        
        result = LocationCheckResult(
            location=location,
            has_warnings=len(matching_warnings) > 0,
            warnings=matching_warnings,
        )
        
        # TTL for location check is same as nowcast
        ttl = settings.cache_ttl_nowcast
        
        return result, False, ttl


    async def get_all_warnings(
        self,
        language: str = "id",
    ) -> tuple[list[Warning], bool, int]:
        """Get all active warnings from all provinces + injected simulations.
        
        Args:
            language: Language code (id/en)
            
        Returns:
            Tuple of (warnings, from_cache, ttl)
        """
        # First get list of active provinces
        provinces, from_cache = await self._get_cached_or_fetch_rss(
            language,
            settings.cache_ttl_nowcast,
        )
        
        all_warnings = []
        
        # Fetch CAP data for each province
        for province in provinces:
            try:
                warning, _ = await self._get_cached_or_fetch_cap(
                    province.code,
                    language,
                    settings.cache_ttl_nowcast,
                )
                if warning:
                    all_warnings.append(warning)
            except Exception:
                continue
                
        # Add injected warnings (Simulation Mode)
        injected = await cache.get("simulation:warnings")
        if injected:
            for w_data in injected:
                try:
                    all_warnings.append(Warning(**w_data))
                except Exception:
                    pass
        
        # Use RSS TTL
        cache_key = self._make_cache_key("rss", {"lang": language})
        ttl = await cache.ttl(cache_key)
        if ttl < 0:
            ttl = settings.cache_ttl_nowcast
            
        return all_warnings, from_cache, ttl

    async def inject_warning(self, warning: Warning):
        """Inject a simulated warning."""
        key = "simulation:warnings"
        current = await cache.get(key)
        if not current:
            current = []
        
        # Serialize and append
        current.append(warning.model_dump(mode='json'))
        # Set 5 minute TTL for simulations
        await cache.set(key, current, ttl=300) 
        
        # Dispatch notification
        await notification_service.dispatch(warning) 
        
    async def clear_simulations(self):
        """Clear all active simulations."""
        await cache.delete("simulation:warnings")

# Global service instance
nowcast_service = NowcastService()
