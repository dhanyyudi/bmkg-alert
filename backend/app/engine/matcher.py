"""Location matcher — matches BMKG warnings against monitored locations.

Pure functions with no I/O. Matches by comparing the kecamatan (subdistrict)
and kabupaten (district) names against the warning description text.
"""

from __future__ import annotations

import re

from app.engine.geo import is_near_warning
from app.models import Location, MatchResult, WarningInfo

# BMKG lists kecamatan as "..., khususnya di A, B, C." and, in some warnings,
# "... dan dapat meluas ke wilayah D, E."; these words introduce a name.
_LEAD_INS = (" di ", " wilayah ", " ke ")
_SEGMENT_SPLIT = re.compile(r"[,.;\n]|\sdan\s")


def is_district_level(location: Location) -> bool:
    """A location that stands for a whole kabupaten/kota (code like "34.04")."""
    return location.subdistrict_code.count(".") == 1


def match_locations(
    warning: WarningInfo,
    locations: list[Location],
    district_members: dict[str, set[str]] | None = None,
) -> list[MatchResult]:
    """Match a warning against a list of monitored locations.

    BMKG lists the affected kecamatan by name in the description, so:
    1. A kecamatan location matches when its name is listed.
    2. A kabupaten/kota location matches when any of its kecamatan is listed;
       `district_members` maps its code to those (lower-cased) names.
    3. Fallback: the district name appears in a warning area name.

    Name matches also need the location, when its coordinates are known, to lie
    near the warning polygon: the same name exists in other provinces.

    Args:
        warning: The parsed BMKG warning info.
        locations: List of enabled monitored locations.
        district_members: Kecamatan names per monitored kabupaten/kota code.

    Returns:
        List of MatchResult for all matched locations.
    """
    results: list[MatchResult] = []
    listed_names = _listed_names(warning.description)
    district_members = district_members or {}

    # Build a set of area names for kabupaten fallback
    area_names_lower = {area.name.lower() for area in warning.areas}

    for location in locations:
        if not location.enabled:
            continue

        near = is_near_warning(location.latitude, location.longitude, warning.areas)

        if is_district_level(location):
            hits = sorted(district_members.get(location.subdistrict_code, set()) & listed_names)
            if hits and near:
                results.append(
                    MatchResult(
                        location=location,
                        match_type="kabupaten",
                        matched_text=hits[0].title(),
                    )
                )
                continue
        else:
            subdistrict = _normalize(location.subdistrict_name)
            if subdistrict and subdistrict in listed_names:
                if near:
                    results.append(
                        MatchResult(
                            location=location,
                            match_type="kecamatan",
                            matched_text=location.subdistrict_name,
                        )
                    )
                continue

        # Fallback: district name in area names
        district = location.district_name.lower()
        if district and any(district in area_name for area_name in area_names_lower):
            results.append(
                MatchResult(
                    location=location,
                    match_type="kabupaten",
                    matched_text=location.district_name,
                )
            )

    return results


def name_listed(name: str, description: str) -> bool:
    """True when `name` is one of the place names the description lists."""
    needle = _normalize(name)
    return bool(needle) and needle in _listed_names(description)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _listed_names(description: str) -> set[str]:
    """Extract the place names a BMKG description lists.

    A plain substring test is not enough: "Kota Agung" is a substring of
    "KOTA AGUNG BARAT". Each segment between commas, periods or "dan" is a
    whole name, optionally behind a lead-in such as "khususnya di".
    """
    names: set[str] = set()
    for raw in _SEGMENT_SPLIT.split(description or ""):
        segment = _normalize(raw)
        if not segment:
            continue
        if segment.startswith("dan "):
            segment = segment[4:]
        names.add(segment)
        padded = f" {segment}"
        for lead_in in _LEAD_INS:
            idx = padded.rfind(lead_in)
            if idx != -1:
                names.add(padded[idx + len(lead_in):])
    return names
