"""Parser for BMKG CAP (Common Alerting Protocol) XML data."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from app.models.nowcast import Warning, Area


def parse_cap_datetime(dt_str: str | None) -> datetime | None:
    """Parse CAP datetime format.
    
    CAP format: "2026-02-16T22:50:00+07:00"
    Returns timezone-aware datetime.
    """
    if not dt_str:
        return None
    
    try:
        # Try ISO format with timezone
        if '+' in dt_str or dt_str.count('-') > 2:
            # Handle +07:00 format
            if dt_str[-3] == ':' and dt_str[-6] in '+-':
                # Remove colon in timezone for fromisoformat compatibility
                dt_str = dt_str[:-3] + dt_str[-2:]
        return datetime.fromisoformat(dt_str)
    except (ValueError, IndexError):
        return None


def parse_polygon(polygon_str: str) -> list[list[float]]:
    """Parse CAP polygon string to list of coordinates.
    
    CAP format: "-5.981,105.994 -6.004,106.022 -6.010,106.029 ..."
    Returns: [[-5.981, 105.994], [-6.004, 106.022], ...]
    """
    points = []
    for point_str in polygon_str.strip().split():
        coords = point_str.split(',')
        if len(coords) >= 2:
            try:
                lat = float(coords[0])
                lon = float(coords[1])
                points.append([lat, lon])
            except ValueError:
                continue
    return points


def parse_cap_xml(xml_content: str) -> Warning | None:
    """Parse BMKG CAP XML content.
    
    Args:
        xml_content: Raw CAP XML content
        
    Returns:
        Warning object or None if parsing fails
    """
    root = ET.fromstring(xml_content)
    
    # CAP namespace
    ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
    
    # Check for namespace
    has_ns = root.tag.startswith('{')
    
    def find_text(path: str, default: str = "") -> str:
        """Helper to find text in element."""
        if has_ns:
            elem = root.find(f'cap:{path}', ns)
        else:
            elem = root.find(path)
        return elem.text if elem is not None else default
    
    def find_info_text(path: str, default: str = "") -> str:
        """Helper to find text in info element."""
        if has_ns:
            info = root.find('cap:info', ns)
            if info is not None:
                elem = info.find(f'cap:{path}', ns)
                return elem.text if elem is not None else default
        else:
            info = root.find('info')
            if info is not None:
                elem = info.find(path)
                return elem.text if elem is not None else default
        return default
    
    # Extract basic fields
    identifier = find_text('identifier')
    sender = find_text('sender')
    
    # Parse dates
    sent_str = find_text('sent')
    effective_str = find_info_text('effective')
    expires_str = find_info_text('expires')
    
    effective = parse_cap_datetime(effective_str) if effective_str else None
    expires = parse_cap_datetime(expires_str) if expires_str else None
    
    # Check if expired
    now = datetime.now(timezone.utc)
    is_expired = False
    if expires and expires.tzinfo:
        is_expired = expires < now
    
    # Extract info fields
    event = find_info_text('event')
    urgency = find_info_text('urgency')
    severity = find_info_text('severity')
    certainty = find_info_text('certainty')
    headline = find_info_text('headline')
    description = find_info_text('description')
    sender_name = find_info_text('senderName')
    infographic_url = find_info_text('web')
    
    # Parse areas — iterate ALL <area> elements, not just the first one
    areas = []
    if has_ns:
        info = root.find('cap:info', ns)
        if info is not None:
            for area_elem in info.findall('cap:area', ns):
                area_desc = area_elem.find('cap:areaDesc', ns)
                area_name = area_desc.text if area_desc is not None else ""

                # Collect all polygon coordinates from every <polygon> child
                polygons: list[list[float]] = []
                for poly in area_elem.findall('cap:polygon', ns):
                    if poly.text and poly.text.strip():
                        points = parse_polygon(poly.text)
                        if points:
                            polygons.extend(points)

                if area_name or polygons:
                    areas.append(Area(name=area_name, polygon=polygons if polygons else None))
    else:
        info = root.find('info')
        if info is not None:
            for area_elem in info.findall('area'):
                area_desc = area_elem.find('areaDesc')
                area_name = area_desc.text if area_desc is not None else ""

                # Collect all polygon coordinates from every <polygon> child
                polygons: list[list[float]] = []
                for poly in area_elem.findall('polygon'):
                    if poly.text and poly.text.strip():
                        points = parse_polygon(poly.text)
                        if points:
                            polygons.extend(points)

                if area_name or polygons:
                    areas.append(Area(name=area_name, polygon=polygons if polygons else None))
    
    return Warning(
        identifier=identifier,
        event=event,
        severity=severity,
        urgency=urgency,
        certainty=certainty,
        effective=effective,
        expires=expires,
        headline=headline,
        description=description,
        sender=sender_name or sender,
        infographic_url=infographic_url if infographic_url else None,
        areas=areas,
        is_expired=is_expired,
    )


def parse_cap_xml_with_region(xml_content: str, region_name: str = "") -> Warning | None:
    """Parse CAP XML and add region name.
    
    Args:
        xml_content: Raw CAP XML content
        region_name: Name of the region/province
        
    Returns:
        Warning object or None if parsing fails
    """
    warning = parse_cap_xml(xml_content)
    if warning and region_name:
        # Override the headline to include region if needed
        if not warning.headline and region_name:
            warning.headline = f"Weather Warning for {region_name}"
    return warning
