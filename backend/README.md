# BMKG Alert backend

FastAPI service behind BMKG Alert: it stores monitored locations and notification
channels, polls BMKG nowcast warnings, matches them against the locations and
sends notifications.

BMKG data (warnings, earthquakes, forecasts, regions) is read from the BMKG REST
API set in `BMKG_API_URL`, by default https://bmkg-api.dhanypedia.com
([source](https://github.com/dhanyyudi/bmkg-api)). This service keeps no copy of
that API.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API reference is served at `http://localhost:8000/docs`. Environment
variables are documented in the repository's `.env.example`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Layout

| Path | Contents |
|------|----------|
| `app/engine/` | BMKG API client, poll cycle, location matching, alert state |
| `app/notifications/` | Per-channel senders for matched alerts |
| `app/routes/` | HTTP routes under `/api/v1` |
| `app/services/` | Earthquake announcements to environment-configured channels |
| `app/schema.sql` | SQLite schema |
