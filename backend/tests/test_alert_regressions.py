"""Regression tests for bugs found in the alert pipeline."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.database import DatabaseManager
from app.engine.matcher import match_locations, name_listed
from app.engine.state import StateManager
from app.models import Area, Location, MatchResult, WarningInfo
from app.notifications.discord import DiscordSender
from app.notifications.formatter import format_telegram_message
from app.notifications.webhook import WebhookSender
from app.routes.channels import _public_view

LAMPUNG = (
    "Hujan lebat disertai petir akan terjadi pada 11 October 2026, 21:05 WIB di sebagian "
    "wilayah Lampung, khususnya di KOTA AGUNG, KOTA AGUNG BARAT, KOTA AGUNG TIMUR, LIMAU, "
    "PESISIR SELATAN, WONOSOBO.\n Kondisi ini berpotensi menimbulkan dampak berupa jarak "
    "pandang berkurang, angin kencang, dan banjir lokal."
)


def _warning(description: str = LAMPUNG, expires: datetime | None = None) -> WarningInfo:
    return WarningInfo(
        identifier="test-warning",
        event="Hujan Lebat dan Petir",
        severity="Moderate",
        urgency="Immediate",
        certainty="Observed",
        effective="2026-10-11T21:05:00+07:00",
        expires=expires or datetime(2026, 10, 11, 23, 0, tzinfo=timezone(timedelta(hours=7))),
        headline="Hujan Lebat disertai Petir di Lampung",
        description=description,
        sender="BMKG",
        infographic_url="https://example.test/infografis.jpg",
        areas=[Area(name="Lampung", polygon=[[-5.5, 104.6], [-5.4, 104.7], [-5.5, 104.8]])],
        is_expired=False,
    )


def _location(name: str, id: int = 1) -> Location:
    return Location(
        id=id,
        province_name="Lampung",
        district_name="KAB. Tanggamus",
        subdistrict_code="18.06.01",
        subdistrict_name=name,
    )


def _match(name: str = "Kota Agung") -> MatchResult:
    return MatchResult(location=_location(name), match_type="kecamatan", matched_text=name)


class TestWholeNameMatching:
    def test_listed_names_match(self):
        for name in ("Kota Agung", "Kota Agung Barat", "Limau", "Wonosobo"):
            assert len(match_locations(_warning(), [_location(name)])) == 1, name

    def test_partial_names_do_not_match(self):
        # "Agung" and "Pesisir" are only fragments of listed names
        for name in ("Agung", "Pesisir", "Kota", "Barat"):
            assert match_locations(_warning(), [_location(name)]) == [], name

    def test_words_from_the_boilerplate_do_not_match(self):
        assert not name_listed("Banjir", LAMPUNG)
        assert not name_listed("Kondisi", LAMPUNG)


class TestMessageFormatting:
    def test_severity_is_rendered_as_a_label_not_an_enum_repr(self):
        msg = format_telegram_message(_warning(), _match())
        assert "Severity." not in msg
        assert "Tingkat:</b> Sedang" in msg

    def test_html_in_bmkg_or_user_text_is_escaped(self):
        match = _match()
        match.location.label = "<b>Rumah & Kantor</b>"
        msg = format_telegram_message(_warning(description="Angin > 40 km/jam & hujan"), match)
        assert "&lt;b&gt;Rumah &amp; Kantor&lt;/b&gt;" in msg
        assert "Angin &gt; 40 km/jam &amp; hujan" in msg

    def test_webhook_payload_is_json_serialisable(self):
        payload = WebhookSender()._build_payload(_warning(), _match(), False)
        encoded = json.loads(json.dumps(payload))
        assert encoded["location"]["code"] == "18.06.01"
        assert encoded["warning"]["severity"] == "Moderate"
        assert encoded["warning"]["expires"] == "2026-10-11T23:00:00+07:00"

    def test_discord_payload_is_json_serialisable(self):
        json.dumps(DiscordSender()._build_embed(_warning(), _match(), False))


class TestChannelSecrets:
    def test_credentials_are_masked(self):
        row = {
            "id": 1,
            "channel_type": "telegram",
            "config": json.dumps({"bot_token": "1234567890:secret", "chat_id": "42", "name": "Rumah"}),
        }
        config = _public_view(row)["config"]
        assert "secret" not in json.dumps(config)
        assert config["chat_id"] == "42" and config["name"] == "Rumah"

    def test_personal_identifiers_are_hidden_from_demo_visitors(self):
        row = {
            "id": 1,
            "channel_type": "telegram",
            "config": json.dumps({"bot_token": "1234567890:secret", "chat_id": "822700000", "name": "Rumah"}),
        }
        config = _public_view(row, show_personal=False)["config"]
        assert "822700000" not in json.dumps(config)
        assert config["name"] == "Rumah"

    @pytest.mark.asyncio
    async def test_demo_visitor_and_admin_views(self, state, monkeypatch):
        import httpx

        from app import database
        from app.config import settings
        from app.main import app

        monkeypatch.setattr(database, "_DB_INSTANCE", state._db)
        monkeypatch.setattr(settings, "demo_mode", True)
        monkeypatch.setattr(settings, "admin_password", "test-admin-password")
        await state._db.execute(
            "INSERT INTO notification_channels (channel_type, enabled, config) VALUES ('telegram', 1, ?)",
            (json.dumps({"bot_token": "1234567890:secret", "chat_id": "822700000", "name": "Rumah"}),),
        )
        await state.log_activity("trial_registered", "Trial registered for chat 391047285: Wiradesa")

        admin = {"X-Admin-Token": "test-admin-password"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            visitor_channels = (await client.get("/api/v1/channels")).text
            visitor_one = (await client.get("/api/v1/channels/1")).text
            visitor_activity = (await client.get("/api/v1/activity")).text
            admin_channels = (await client.get("/api/v1/channels", headers=admin)).text
            admin_activity = (await client.get("/api/v1/activity", headers=admin)).text

        for body in (visitor_channels, visitor_one):
            assert "822700000" not in body and "1234567890:secret" not in body
        assert "391047285" not in visitor_activity and "Wiradesa" in visitor_activity
        assert "822700000" in admin_channels and "1234567890:secret" not in admin_channels
        assert "391047285" in admin_activity


@pytest.fixture
async def state(tmp_path):
    db = DatabaseManager(str(tmp_path / "test.db"))
    await db.connect()
    await db.init_schema()
    await db.execute(
        """
        INSERT INTO locations (id, province_code, province_name, district_code, district_name,
                               subdistrict_code, subdistrict_name)
        VALUES (1, '18', 'Lampung', '18.06', 'KAB. Tanggamus', '18.06.01', 'Kota Agung')
        """
    )
    for trial_id in (7, 8):
        await db.execute(
            """
            INSERT INTO trial_subscriptions (id, telegram_chat_id, subdistrict_code, subdistrict_name,
                                             district_name, province_name, expires_at)
            VALUES (?, '42', '18.06.01', 'Kota Agung', 'KAB. Tanggamus', 'Lampung', datetime('now', '+1 day'))
            """,
            (trial_id,),
        )
    yield StateManager(db)
    await db.close()


class TestExpiry:
    @pytest.mark.asyncio
    async def test_alert_expires_at_its_instant_not_by_string_order(self, state):
        now = datetime.now(timezone.utc)
        wib = timezone(timedelta(hours=7))
        future = (now + timedelta(hours=3)).astimezone(wib)
        past = (now - timedelta(minutes=5)).astimezone(wib)

        still_active = await state.store_alert(_warning(expires=future), _match(), "CODE-FUTURE")
        over = await state.store_alert(_warning(expires=past), _match(), "CODE-PAST")

        expired_ids = {a.id for a in await state.mark_expired_alerts()}
        assert expired_ids == {over}
        assert still_active in {a.id for a in await state.get_active_alerts()}

    @pytest.mark.asyncio
    async def test_legacy_space_separated_rows_still_expire(self, state):
        await state._db.execute(
            "INSERT INTO alerts (bmkg_alert_code, expires, status) VALUES ('OLD', '2026-06-25 13:48:00+07:00', 'active')"
        )
        assert [a.bmkg_alert_code for a in await state.mark_expired_alerts()] == ["OLD"]


class TestTrialDedup:
    @pytest.mark.asyncio
    async def test_a_trial_is_notified_once_per_warning(self, state):
        assert await state.claim_trial_notification(7, "CLG20261011001") is True
        assert await state.claim_trial_notification(7, "CLG20261011001") is False
        assert await state.claim_trial_notification(7, "CLG20261011002") is True
        assert await state.claim_trial_notification(8, "CLG20261011001") is True


class TestDeleteKeepsHistory:
    @pytest.mark.asyncio
    async def test_location_with_alert_history_can_be_deleted(self, state, monkeypatch):
        from app import database
        from app.routes.locations import delete_location

        monkeypatch.setattr(database, "_DB_INSTANCE", state._db)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        alert_id = await state.store_alert(_warning(expires=future), _match(), "CODE-KEEP")

        assert await delete_location(1) == {"status": "deleted", "id": 1}
        row = await state._db.fetch_one("SELECT matched_location_id FROM alerts WHERE id = ?", (alert_id,))
        assert row["matched_location_id"] is None
