"""Parser for BMKG RSS feed (list of active weather warnings)."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from app.models.nowcast import ActiveProvince


def parse_rss_date(date_str: str) -> datetime:
    """Parse RSS pubDate format to datetime.
    
    RSS date format examples:
    - "Mon, 16 Feb 2026 22:50:00 +0700"
    - "Mon, 16 Feb 2026 16:17:19 +0000"
    
    Returns timezone-aware datetime in UTC.
    """
    # Remove day name prefix if present
    date_str = date_str.strip()
    if ',' in date_str:
        date_str = date_str.split(',', 1)[1].strip()
    
    # Parse the date components
    # Format: "16 Feb 2026 22:50:00 +0700"
    parts = date_str.rsplit(' ', 1)  # Split timezone separately
    date_time_part = parts[0]
    tz_part = parts[1] if len(parts) > 1 else "+0000"
    
    # Parse date and time
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    dt_parts = date_time_part.split()
    day = int(dt_parts[0])
    month = months.get(dt_parts[1], 1)
    year = int(dt_parts[2])
    time_parts = dt_parts[3].split(':')
    hour = int(time_parts[0])
    minute = int(time_parts[1])
    second = int(time_parts[2])
    
    # Create datetime in local timezone
    dt = datetime(year, month, day, hour, minute, second)
    
    # Parse timezone offset
    if tz_part.startswith('+') or tz_part.startswith('-'):
        sign = 1 if tz_part[0] == '+' else -1
        tz_hours = int(tz_part[1:3])
        tz_minutes = int(tz_part[3:5])
        
        # Import timezone and timedelta to make it timezone-aware
        from datetime import timezone as dt_timezone, timedelta
        offset = timedelta(seconds=sign * (tz_hours * 3600 + tz_minutes * 60))
        tz = dt_timezone(offset)
        dt = dt.replace(tzinfo=tz)
    
    return dt


def extract_alert_code_from_link(link: str) -> str:
    """Extract alert code from RSS item link.
    
    Example link: https://www.bmkg.go.id/alerts/nowcast/id/CBT20260216004_alert.xml
    Returns: CBT20260216004
    """
    # Get the last part of the URL
    filename = link.split('/')[-1]
    # Remove _alert.xml suffix
    if '_alert.xml' in filename:
        return filename.replace('_alert.xml', '')
    return filename


def parse_rss_feed(xml_content: str, language: str = "id") -> list[ActiveProvince]:
    """Parse BMKG RSS feed XML content.
    
    Args:
        xml_content: Raw RSS XML content
        language: Language code (id/en)
        
    Returns:
        List of ActiveProvince objects
    """
    root = ET.fromstring(xml_content)
    
    # RSS namespace
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    provinces = []
    
    # Find channel and items
    channel = root.find('channel')
    if channel is None:
        return provinces
    
    for item in channel.findall('item'):
        title_elem = item.find('title')
        link_elem = item.find('link')
        desc_elem = item.find('description')
        pub_date_elem = item.find('pubDate')
        
        if title_elem is None or link_elem is None:
            continue
        
        title = title_elem.text or ""
        link = link_elem.text or ""
        description = desc_elem.text or "" if desc_elem is not None else ""
        
        # Parse publication date
        published_at = datetime.utcnow()
        if pub_date_elem is not None and pub_date_elem.text:
            try:
                published_at = parse_rss_date(pub_date_elem.text)
            except (ValueError, IndexError):
                pass
        
        # Extract alert code from link
        alert_code = extract_alert_code_from_link(link)
        
        # Extract province name from title
        # Format: "Hujan Lebat disertai Petir di Banten"
        province_name = title.split(' di ')[-1] if ' di ' in title else title
        
        # Build detail URL
        detail_url = f"/v1/nowcast/{alert_code}"
        
        province = ActiveProvince(
            code=alert_code,
            province=province_name,
            description=description[:200] + "..." if len(description) > 200 else description,
            published_at=published_at,
            detail_url=detail_url,
        )
        provinces.append(province)
    
    return provinces
