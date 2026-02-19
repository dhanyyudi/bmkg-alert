"""Tests for the notification formatter."""

from app.models import Location, MatchResult, WarningArea, WarningInfo
from app.notifications.formatter import _format_time, format_expiry_message, format_telegram_message


def _make_warning() -> WarningInfo:
    return WarningInfo(
        event="Hujan Lebat dan Petir",
        severity="Moderate",
        urgency="Immediate",
        certainty="Observed",
        effective="2026-02-17T19:55:00+07:00",
        expires="2026-02-17T23:00:00+07:00",
        headline="Hujan Lebat disertai Petir di Jawa Tengah",
        description="Hujan lebat disertai petir akan terjadi di wilayah Alian.",
        infographic_url="https://example.com/infografis.jpg",
        areas=[WarningArea(name="Jawa Tengah", polygon=[])],
    )


def _make_match() -> MatchResult:
    return MatchResult(
        location=Location(
            id=1,
            label="Rumah",
            province_code="33",
            province_name="Jawa Tengah",
            district_code="3305",
            district_name="Kebumen",
            subdistrict_code="330501",
            subdistrict_name="Alian",
        ),
        match_type="kecamatan",
        matched_text="Alian",
    )


class TestTelegramFormatter:
    """Test message formatting for Telegram."""

    def test_basic_format(self):
        """Message contains all required fields."""
        msg = format_telegram_message(_make_warning(), _make_match())
        assert "Hujan Lebat dan Petir" in msg
        assert "Rumah" in msg  # location label
        assert "Alian" in msg
        assert "Kebumen" in msg
        assert "Jawa Tengah" in msg
        assert "Moderate" in msg
        assert "🟡" in msg  # Moderate severity emoji

    def test_severity_emojis(self):
        """Each severity level maps to correct emoji."""
        for severity, emoji in [
            ("Minor", "🔵"),
            ("Moderate", "🟡"),
            ("Severe", "🔴"),
            ("Extreme", "⚫"),
        ]:
            warning = _make_warning()
            warning.severity = severity
            msg = format_telegram_message(warning, _make_match())
            assert emoji in msg

    def test_trial_mode_footer(self):
        """Trial mode adds expiry notice."""
        msg = format_telegram_message(_make_warning(), _make_match(), is_trial=True)
        assert "Mode Trial" in msg

    def test_no_trial_footer_by_default(self):
        """Normal mode doesn't show trial footer."""
        msg = format_telegram_message(_make_warning(), _make_match(), is_trial=False)
        assert "Mode Trial" not in msg

    def test_infographic_link(self):
        """Infographic URL is included."""
        msg = format_telegram_message(_make_warning(), _make_match())
        assert "infografis.jpg" in msg

    def test_html_format(self):
        """Output uses HTML tags for Telegram."""
        msg = format_telegram_message(_make_warning(), _make_match())
        assert "<b>" in msg
        assert "</b>" in msg


class TestExpiryMessage:
    """Test 'all clear' message formatting."""

    def test_expiry_message(self):
        """Expiry message contains event and location."""
        msg = format_expiry_message("Hujan Lebat", "Rumah")
        assert "Berakhir" in msg
        assert "Hujan Lebat" in msg
        assert "Rumah" in msg


class TestTimeFormatter:
    """Test time formatting helper."""

    def test_wib_timezone(self):
        """WIB timezone label for +07."""
        result = _format_time("2026-02-17T19:55:00+07:00")
        assert "WIB" in result
        assert "19:55" in result

    def test_wita_timezone(self):
        """WITA timezone label for +08."""
        result = _format_time("2026-02-17T21:30:00+08:00")
        assert "WITA" in result

    def test_wit_timezone(self):
        """WIT timezone label for +09."""
        result = _format_time("2026-02-17T22:00:00+09:00")
        assert "WIT" in result

    def test_empty_time(self):
        """Empty string returns dash."""
        assert _format_time("") == "-"
