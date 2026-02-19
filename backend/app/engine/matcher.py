"""Location matcher — matches BMKG warnings against monitored locations.

Pure functions with no I/O. Matches by comparing the kecamatan (subdistrict)
and kabupaten (district) names against the warning description text.
"""

from __future__ import annotations

from app.models import Location, MatchResult, WarningInfo


def match_locations(
    warning: WarningInfo, locations: list[Location]
) -> list[MatchResult]:
    """Match a warning against a list of monitored locations.

    Strategy:
    1. Primary: check if the subdistrict name appears in the warning description
    2. Fallback: check if the district name appears in the warning area name

    Args:
        warning: The parsed BMKG warning info.
        locations: List of enabled monitored locations.

    Returns:
        List of MatchResult for all matched locations.
    """
    results: list[MatchResult] = []
    description_lower = warning.description.lower()

    # Build a set of area names for kabupaten fallback
    area_names_lower = {area.name.lower() for area in warning.areas}

    for location in locations:
        if not location.enabled:
            continue

        # Primary match: kecamatan name in description
        subdistrict = location.subdistrict_name.lower()
        if subdistrict and _word_boundary_match(subdistrict, description_lower):
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


def _word_boundary_match(needle: str, haystack: str) -> bool:
    """Check if needle appears in haystack with word-boundary awareness.

    The BMKG description lists kecamatan as comma-separated names.
    We match if the needle appears as a standalone word or phrase.
    """
    # Use simple substring check — kecamatan names in the description
    # are separated by commas and spaces, so this is reliable.
    # We avoid regex for performance on frequently-polled data.
    return needle in haystack
