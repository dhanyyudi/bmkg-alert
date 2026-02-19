"""Tests for the location matcher — pure functions, no I/O."""

from app.engine.matcher import match_locations
from app.models import Location, WarningArea, WarningInfo


def _make_location(
    id: int = 1,
    subdistrict_name: str = "Alian",
    district_name: str = "Kebumen",
    province_name: str = "Jawa Tengah",
    enabled: bool = True,
) -> Location:
    return Location(
        id=id,
        label=f"Lokasi {id}",
        province_code="33",
        province_name=province_name,
        district_code="3305",
        district_name=district_name,
        subdistrict_code="330501",
        subdistrict_name=subdistrict_name,
        enabled=enabled,
    )


def _make_warning(
    description: str = "",
    area_names: list[str] | None = None,
) -> WarningInfo:
    areas = [WarningArea(name=name) for name in (area_names or ["Jawa Tengah"])]
    return WarningInfo(
        event="Hujan Lebat dan Petir",
        severity="Moderate",
        description=description,
        areas=areas,
    )


class TestKecamatanMatch:
    """Primary matching: subdistrict name in warning description."""

    def test_exact_match(self):
        """Kecamatan name found in description text."""
        warning = _make_warning(
            description="Hujan di Alian, Bonorowo, Bruno, Butuh."
        )
        location = _make_location(subdistrict_name="Alian")
        results = match_locations(warning, [location])
        assert len(results) == 1
        assert results[0].match_type == "kecamatan"
        assert results[0].matched_text == "Alian"

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        warning = _make_warning(description="hujan di alian dan sekitarnya")
        location = _make_location(subdistrict_name="Alian")
        results = match_locations(warning, [location])
        assert len(results) == 1
        assert results[0].match_type == "kecamatan"

    def test_no_match(self):
        """No match when kecamatan not in description."""
        warning = _make_warning(description="Hujan di Jakarta Selatan")
        location = _make_location(subdistrict_name="Alian")
        results = match_locations(warning, [location])
        assert len(results) == 0

    def test_disabled_location_skipped(self):
        """Disabled locations are not matched."""
        warning = _make_warning(description="Hujan di Alian")
        location = _make_location(subdistrict_name="Alian", enabled=False)
        results = match_locations(warning, [location])
        assert len(results) == 0


class TestKabupatenFallback:
    """Fallback matching: district name in warning area names."""

    def test_kabupaten_match(self):
        """District name found in area names when kecamatan doesn't match."""
        warning = _make_warning(
            description="Hujan di wilayah lain",
            area_names=["Kebumen"],
        )
        location = _make_location(
            subdistrict_name="SomeOtherKecamatan",
            district_name="Kebumen",
        )
        results = match_locations(warning, [location])
        assert len(results) == 1
        assert results[0].match_type == "kabupaten"
        assert results[0].matched_text == "Kebumen"

    def test_kecamatan_takes_priority(self):
        """When kecamatan matches, kabupaten fallback is not used."""
        warning = _make_warning(
            description="Hujan di Alian",
            area_names=["Kebumen"],
        )
        location = _make_location(
            subdistrict_name="Alian",
            district_name="Kebumen",
        )
        results = match_locations(warning, [location])
        assert len(results) == 1
        assert results[0].match_type == "kecamatan"


class TestMultipleLocations:
    """Multiple locations against a single warning."""

    def test_multiple_matches(self):
        """Multiple locations match the same warning."""
        warning = _make_warning(description="Hujan di Alian, Bonorowo, Bruno")
        locations = [
            _make_location(id=1, subdistrict_name="Alian"),
            _make_location(id=2, subdistrict_name="Bonorowo"),
            _make_location(id=3, subdistrict_name="UnknownPlace"),
        ]
        results = match_locations(warning, locations)
        assert len(results) == 2
        matched_names = {r.matched_text for r in results}
        assert matched_names == {"Alian", "Bonorowo"}

    def test_empty_locations(self):
        """No locations to match against."""
        warning = _make_warning(description="Hujan di Alian")
        results = match_locations(warning, [])
        assert len(results) == 0

    def test_real_bmkg_description(self):
        """Test with a real BMKG API description string."""
        description = (
            "Hujan lebat disertai petir akan terjadi pada 17 February 2026, "
            "19:55 WIB di sebagian wilayah Jawa Tengah, khususnya di "
            "Alian, Bonorowo, Bruno, Butuh, Gebang, Grabag, Jatilawang, "
            "Kalibawang, Kalibening, Karanganyar, Karanggayam, Karangsambung, "
            "Kebasen, Kemiri, Kesugihan, Kutoarjo, Kutowinangun, Mirit, "
            "Ngombol, Padureso, Pejagoan, Pituruh, Poncowarno, Prembun, "
            "Purwodadi, Rawalo, Sruweng."
        )
        warning = _make_warning(description=description)
        locations = [
            _make_location(id=1, subdistrict_name="Kalibening"),
            _make_location(id=2, subdistrict_name="Sruweng"),
            _make_location(id=3, subdistrict_name="Tangerang"),
        ]
        results = match_locations(warning, locations)
        assert len(results) == 2
        matched_names = {r.matched_text for r in results}
        assert matched_names == {"Kalibening", "Sruweng"}
