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


class TestSameNameInAnotherProvince:
    """ "Wonosobo" is a kecamatan in Lampung and a kabupaten seat in Jawa Tengah."""

    def _wonosobo(self, latitude=None, longitude=None) -> Location:
        location = _location("Wonosobo")
        location.latitude, location.longitude = latitude, longitude
        return location

    def test_far_away_namesake_is_not_matched(self):
        jawa_tengah = self._wonosobo(-7.36, 109.90)
        assert match_locations(_warning(), [jawa_tengah]) == []

    def test_location_inside_the_warned_region_is_matched(self):
        lampung = self._wonosobo(-5.48, 104.72)
        assert len(match_locations(_warning(), [lampung])) == 1

    def test_unknown_coordinates_never_suppress_a_warning(self):
        assert len(match_locations(_warning(), [self._wonosobo()])) == 1


class TestWarningsClient:
    ENTRY = {
        "code": "CLG20261011001",
        "province": "Lampung",
        "published_at": "2026-10-11T21:00:00+07:00",
        "warning": json.loads(_warning().model_dump_json()),
    }

    def _client(self, handler):
        import httpx

        from app.engine.bmkg_client import HttpBMKGClient

        client = HttpBMKGClient("https://api.test")
        client._client = httpx.AsyncClient(base_url="https://api.test", transport=httpx.MockTransport(handler))
        return client

    @pytest.mark.asyncio
    async def test_all_warnings_come_from_one_request(self):
        import httpx

        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, json={"data": [self.ENTRY], "meta": {"count": 1, "missing": []}})

        warnings = await self._client(handler).get_warnings()
        assert seen == ["/v1/nowcast/warnings"]
        assert warnings[0].code == "CLG20261011001" and warnings[0].warning.event == "Hujan Lebat dan Petir"

    @pytest.mark.asyncio
    async def test_older_api_without_the_endpoint_still_works(self):
        import httpx

        def handler(request):
            path = request.url.path
            if path == "/v1/nowcast/warnings":
                return httpx.Response(404, json={"detail": "Not Found"})
            if path == "/v1/nowcast":
                feed = {k: self.ENTRY[k] for k in ("code", "province", "published_at")}
                feed.update(description="...", detail_url="/v1/nowcast/CLG20261011001")
                return httpx.Response(200, json={"data": [feed], "meta": {"count": 1}})
            return httpx.Response(200, json={"data": {"province": "Lampung", "warnings": [self.ENTRY["warning"]]}})

        warnings = await self._client(handler).get_warnings()
        assert [w.code for w in warnings] == ["CLG20261011001"]


class TestQuietHoursClock:
    def test_minutes_are_kept(self):
        from app.notifications.dispatcher import _parse_clock

        assert _parse_clock("22:30") == 22 * 60 + 30
        assert _parse_clock("06:00") == 360
        assert _parse_clock("bukan jam") is None and _parse_clock("25:00") is None


class TestClientAddress:
    def _request(self, headers: dict):
        from starlette.requests import Request

        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        return Request({"type": "http", "headers": raw, "client": ("10.0.0.5", 1234)})

    def test_forwarding_headers_are_ignored_unless_configured(self, monkeypatch):
        from app.config import settings
        from app.dependencies import client_ip

        monkeypatch.setattr(settings, "client_ip_header", "")
        assert client_ip(self._request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.5"

    def test_configured_header_is_used(self, monkeypatch):
        from app.config import settings
        from app.dependencies import client_ip

        monkeypatch.setattr(settings, "client_ip_header", "CF-Connecting-IP")
        assert client_ip(self._request({"CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "1.2.3.4"})) == "203.0.113.9"


@pytest.fixture
async def api(state, monkeypatch):
    """HTTP client against the app, backed by the temporary database."""
    import httpx

    from app import database
    from app.config import settings
    from app.main import app

    monkeypatch.setattr(database, "_DB_INSTANCE", state._db)
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "admin_password", "changeme")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


class TestWriteLock:
    ADMIN = {"X-Admin-Token": "kata-sandi-pemilik"}
    BODY = {"settings": {"poll_interval": "600"}}

    @pytest.mark.asyncio
    async def test_default_password_leaves_a_private_instance_open(self, api):
        assert (await api.put("/api/v1/config", json=self.BODY)).status_code == 200
        status = (await api.get("/api/v1/engine/status")).json()
        assert status["write_locked"] is False and status["admin_login_available"] is False

    @pytest.mark.asyncio
    async def test_default_password_cannot_log_in(self, api):
        assert (await api.post("/api/v1/auth/login", json={"password": "changeme"})).status_code == 403

    @pytest.mark.asyncio
    async def test_configured_password_locks_writes(self, api, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "admin_password", "kata-sandi-pemilik")
        assert (await api.put("/api/v1/config", json=self.BODY)).status_code == 403
        assert (await api.put("/api/v1/config", json=self.BODY, headers={"X-Admin-Token": "salah"})).status_code == 403
        assert (await api.put("/api/v1/config", json=self.BODY, headers=self.ADMIN)).status_code == 200
        assert (await api.post("/api/v1/auth/login", json={"password": "kata-sandi-pemilik"})).status_code == 200
        assert (await api.get("/api/v1/engine/status")).json()["write_locked"] is True


class TestConfigImport:
    @pytest.mark.asyncio
    async def test_locations_and_channels_are_restored(self, api, state):
        export = {
            "config": {"poll_interval": "600"},
            "locations": [
                {"id": 1, "subdistrict_code": "18.06.01", "subdistrict_name": "Kota Agung"},
                {
                    "id": 9, "label": "Rumah", "province_code": "33", "province_name": "Jawa Tengah",
                    "district_code": "33.26", "district_name": "Kabupaten Pekalongan",
                    "subdistrict_code": "33.26.16", "subdistrict_name": "Wiradesa",
                    "latitude": -6.9, "longitude": 109.6, "enabled": 1, "created_at": "2026-01-01 00:00:00",
                },
            ],
            "channels": [
                {"channel_type": "telegram", "enabled": 1, "config": {"bot_token": "1234567890:real", "chat_id": "42"}},
                {"channel_type": "telegram", "enabled": 1, "config": {"bot_token": "••••••••", "chat_id": "42"}},
            ],
        }
        result = (await api.post("/api/v1/config/import", json=export)).json()["imported"]
        assert result == {"config": 1, "locations": 1, "channels": 1, "channels_skipped": 1}

        again = (await api.post("/api/v1/config/import", json=export)).json()["imported"]
        assert again["locations"] == 0 and again["channels"] == 0

        codes = {row["subdistrict_code"] for row in await state._db.fetch_all("SELECT subdistrict_code FROM locations")}
        assert codes == {"18.06.01", "33.26.16"}


class TestBmkgRoutes:
    @pytest.mark.asyncio
    async def test_active_warnings_are_fetched_once_and_reused(self, api, monkeypatch):
        from unittest.mock import AsyncMock

        from app import dependencies
        from app.cache import cache
        from app.models import ActiveWarning

        await cache.delete("alert:nowcast:active")
        client = AsyncMock()
        client.get_warnings.return_value = [ActiveWarning(code="CLG20261011001", province="Lampung", warning=_warning())]
        monkeypatch.setattr(dependencies, "_bmkg_client_instance", client)

        first = (await api.get("/api/v1/nowcast/active")).json()
        second = (await api.get("/api/v1/nowcast/active")).json()
        await cache.delete("alert:nowcast:active")

        assert first == second and first["data"][0]["event"] == "Hujan Lebat dan Petir"
        assert client.get_warnings.await_count == 1

    @pytest.mark.asyncio
    async def test_weather_rejects_codes_that_are_not_villages(self, api):
        assert (await api.get("/api/v1/weather/33.26.16")).status_code == 400
        assert (await api.get("/api/v1/wilayah/villages?subdistrict=33.26")).status_code == 400


class TestActivityLogPruning:
    @pytest.mark.asyncio
    async def test_old_entries_are_dropped(self, state):
        await state._db.execute(
            "INSERT INTO activity_log (event_type, message, created_at) VALUES ('poll_completed', 'lama', datetime('now', '-45 days'))"
        )
        await state.log_activity("poll_completed", "baru")
        await state.prune_activity_log(keep_days=30)
        rows = await state._db.fetch_all("SELECT message FROM activity_log")
        assert [row["message"] for row in rows] == ["baru"]


class TestKabupatenLocation:
    """A location that stands for a whole kabupaten/kota matches through its kecamatan."""

    def _tanggamus(self) -> Location:
        return Location(
            id=5,
            province_name="Lampung",
            district_code="18.06",
            district_name="Kabupaten Tanggamus",
            subdistrict_code="18.06",
            subdistrict_name="Kabupaten Tanggamus",
        )

    def test_matches_when_one_of_its_kecamatan_is_listed(self):
        members = {"18.06": {"kota agung", "semaka", "limau"}}
        results = match_locations(_warning(), [self._tanggamus()], members)
        assert [(r.match_type, r.matched_text) for r in results] == [("kabupaten", "Kota Agung")]

    def test_no_match_without_a_listed_kecamatan(self):
        members = {"18.06": {"semaka", "pulau panggung"}}
        assert match_locations(_warning(), [self._tanggamus()], members) == []

    def test_unknown_members_do_not_match_by_the_kabupaten_name(self):
        assert match_locations(_warning(), [self._tanggamus()]) == []


class TestRegionPoint:
    @pytest.mark.asyncio
    async def test_kabupaten_code_resolves_through_a_kecamatan_and_village(self):
        from unittest.mock import AsyncMock

        from app.engine.geo import resolve_point

        calls = []

        async def get_json(path, params=None):
            calls.append((path, params))
            if path == "/v1/wilayah/subdistricts":
                return {"data": [{"code": "34.04.01", "name": "Gamping"}]}
            if path == "/v1/wilayah/villages":
                return {"data": [{"code": "34.04.01.2001", "name": "Balecatur"}]}
            return {"data": {"location": {"lat": -7.79, "lon": 110.30}}}

        client = AsyncMock()
        client.get_json.side_effect = get_json
        assert await resolve_point(client, "34.04") == (-7.79, 110.30)
        assert [path for path, _ in calls] == ["/v1/wilayah/subdistricts", "/v1/wilayah/villages", "/v1/weather/34.04.01.2001"]

    @pytest.mark.asyncio
    async def test_upstream_failure_yields_no_point(self):
        import httpx
        from unittest.mock import AsyncMock

        from app.engine.geo import resolve_point

        client = AsyncMock()
        client.get_json.side_effect = httpx.ConnectError("down")
        assert await resolve_point(client, "34.04.01") is None


class TestSchemaUpgrade:
    @pytest.mark.asyncio
    async def test_database_from_the_first_release_gains_the_new_columns(self, tmp_path):
        import sqlite3

        path = tmp_path / "old.db"
        old = sqlite3.connect(path)
        old.executescript(
            """
            CREATE TABLE trial_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_chat_id TEXT NOT NULL,
                subdistrict_code TEXT NOT NULL,
                subdistrict_name TEXT NOT NULL,
                district_name TEXT NOT NULL,
                province_name TEXT NOT NULL,
                severity_threshold TEXT DEFAULT 'all',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                expired_notified BOOLEAN DEFAULT 0,
                ip_address TEXT
            );
            INSERT INTO trial_subscriptions (telegram_chat_id, subdistrict_code, subdistrict_name, district_name, province_name, expires_at)
            VALUES ('42', '33.26.16', 'Wiradesa', 'KAB. Pekalongan', 'Jawa Tengah', '2099-01-01 00:00:00');
            """
        )
        old.commit()
        old.close()

        db = DatabaseManager(str(path))
        await db.connect()
        await db.init_schema()
        await db.init_schema()  # running it again must be harmless
        trials = await StateManager(db).get_active_trials()
        await db.close()

        assert trials[0]["subdistrict_name"] == "Wiradesa"
        assert trials[0]["latitude"] is None and "longitude" in trials[0]
