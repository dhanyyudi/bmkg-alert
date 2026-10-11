# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- BMKG data source moved to `https://bmkg-api.dhanypedia.com`; the old Vercel host no longer responds
- Weather forecasts are served through `BMKG_API_URL` instead of the bundled parser
- Interface text is Indonesian throughout; navigation has a labelled menu bar on phones
- Channel credentials are masked in API responses, and config export needs admin rights in demo mode

### Fixed
- Alerts were marked expired by string comparison, often in the same poll that created them
- "Berpotensi tsunami" badge appeared on every earthquake, including "Tidak berpotensi tsunami"
- Telegram, Slack and email messages showed `Severity.MODERATE` instead of the level
- Discord and webhook notifications failed for every real alert
- Trial subscribers received the same warning on every poll cycle
- A kecamatan name matched as a fragment of a longer name (for example "Agung" in "Kota Agung")
- Locations and channels with history could not be deleted
- Weather page failed for monitored locations (kecamatan codes) and for every forecast request
- Bot tokens were written to the container log by the HTTP client
- The latest earthquake was announced again after every restart
- `severity_threshold` had no effect; trial and expiry handling was skipped when no location was configured

## [1.0.0] - 2026-02-19

Initial public release.

### Added

**Core Engine**
- Alert engine that polls BMKG Nowcast data on a configurable interval
- Location matching at kecamatan (subdistrict) level with kabupaten fallback
- Deduplication — each alert is only sent once per location per event
- Auto-expiry — mark alerts as expired and send "all clear" notification
- Configurable polling interval, quiet hours, and severity threshold

**Dashboard**
- Real-time engine status panel (running/stopped, last poll result)
- Active warnings list with severity badges, timestamps, and infographic links
- Interactive warning map with BMKG polygon visualization (MapLibre GL)
- Recent activity feed
- Manual "Check Now" trigger
- Next poll countdown

**Notifications**
- Telegram Bot API
- Discord incoming webhook
- Slack incoming webhook
- Email via SMTP
- Generic JSON webhook (POST)
- Per-channel test button

**Settings**
- Location management — search and add locations by kecamatan name
- Channel management — add, edit, toggle, delete notification channels
- Configuration — polling interval, severity threshold, quiet hours
- Export / Import full configuration as JSON
- System tab — app version, engine status, alert statistics

**Setup Wizard**
- 5-step guided first-time configuration
- Steps: Welcome → Telegram Setup → Location → Severity → Done

**Try Mode**
- 24-hour Telegram trial subscription for demo visitors
- Location search at kecamatan level
- Severity filter selection
- Auto-expiry with Telegram notification
- IP-based rate limiting (5 registrations per hour)

**Demo Mode**
- Read-only public demo (`DEMO_MODE=true`)
- Write operations blocked with 403 for non-admin users
- Admin bypass via password (`ADMIN_PASSWORD`) — entered in browser, stored in sessionStorage

**Alert History**
- Full alert log with status (active/expired)
- Alert detail page with polygon map, delivery log, and all CAP fields

**Weather Forecast**
- 3-day BMKG prakiraan cuaca per kecamatan
- Location search integrated into settings

**Deployment**
- Multi-stage Docker build for backend (Python 3.12) and frontend (Node 20)
- Production `docker-compose.yml` — GHCR images, no host ports, external `private_network`
- Development `docker-compose.dev.yml` — local build, ports exposed
- GitHub Actions CI (lint + build on every PR)
- GitHub Actions Docker publish (GHCR on push to main)
- Astro middleware for frontend → backend API proxy (single-origin deployment)
