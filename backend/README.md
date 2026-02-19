# BMKG API

[![Docker](https://github.com/dhanyyudi/bmkg-api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/dhanyyudi/bmkg-api/actions/workflows/docker-publish.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](#english) | [Bahasa Indonesia](#bahasa-indonesia)

---

<a name="english"></a>
## 🇬🇧 English

Free REST API for Indonesian weather forecasts, earthquake data, weather warnings, and region lookup from BMKG.

**🌐 Demo:** [https://bmkg-restapi.vercel.app](https://bmkg-restapi.vercel.app)

### ⚠️ Important Notice

This is a **demo/public instance** with rate limits (30 requests/minute) to ensure fair usage.

**For production use with unlimited requests, please [self-host](#self-hosting).**

### Features

- 🌍 **Earthquake Data** — Latest, recent (M 5.0+), felt earthquakes, nearby search by coordinates
- 🌤️ **Weather Forecast** — 3-day forecasts & current weather for any kelurahan/desa in Indonesia
- ⚠️ **Weather Warnings (Nowcast)** — Real-time severe weather alerts with affected area polygons
- 📢 **Multi-Channel Notifications** — Telegram, Discord, Slack, Email, and Webhooks
- 🎮 **Simulation Mode** — Built-in tools to simulate Earthquakes and Weather events for testing
- 📍 **Region Lookup** — Indonesian provinces, districts, subdistricts, villages, plus search
- 📊 **Auto-generated Docs** — Interactive API documentation at `/docs`
- ⚡ **Caching** — Fast responses with in-memory cache (configurable TTL)
- 🌐 **CORS Enabled** — Use from any frontend
- 🔓 **No API Key Required** — Simple, anonymous access
- 📈 **Rate Limit Headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on every response
- 🐳 **Docker & GHCR** — Automated multi-arch Docker images published to GitHub Container Registry

### Quick Start

```bash
# Latest earthquake
curl https://bmkg-restapi.vercel.app/v1/earthquake/latest

# Weather forecast for Tebet Timur, Jakarta
curl https://bmkg-restapi.vercel.app/v1/weather/31.74.01.1001

# Current weather
curl https://bmkg-restapi.vercel.app/v1/weather/31.74.01.1001/current

# Active weather warnings
curl https://bmkg-restapi.vercel.app/v1/nowcast

# Search regions
curl https://bmkg-restapi.vercel.app/v1/wilayah/search?q=tebet
```

```

### ⚙️ Configuration

Configure the application via `.env` file:

```ini
# Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# BMKG Data Sources
BMKG_EARTHQUAKE_BASE_URL=https://data.bmkg.go.id/DataMKG/TEWS
```

### API Endpoints

#### 🌍 Earthquake
| Endpoint | Description |
|----------|-------------|
| `GET /v1/earthquake/latest` | Latest earthquake |
| `GET /v1/earthquake/recent` | Recent earthquakes (M 5.0+) |
| `GET /v1/earthquake/felt` | Felt earthquakes |
| `GET /v1/earthquake/nearby?lat=&lon=&radius_km=` | Nearby earthquakes |

#### 🌤️ Weather
| Endpoint | Description |
|----------|-------------|
| `GET /v1/weather/{adm4_code}` | 3-day forecast for a kelurahan/desa |
| `GET /v1/weather/{adm4_code}/current` | Current weather for a kelurahan/desa |

#### ⚠️ Nowcast (Weather Warnings)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/nowcast` | Active weather warnings by province |
| `GET /v1/nowcast/{alert_code}` | Warning detail with affected area polygons |
| `GET /v1/nowcast/check?location=` | Check warnings for a specific location |

#### 📍 Wilayah (Region)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/wilayah/provinces` | List provinces |
| `GET /v1/wilayah/districts?province_code=` | List districts |
| `GET /v1/wilayah/subdistricts?district_code=` | List subdistricts |
| `GET /v1/wilayah/villages?subdistrict_code=` | List villages |
| `GET /v1/wilayah/search?q={query}` | Search regions |

**Full documentation:** [https://bmkg-restapi.vercel.app/docs](https://bmkg-restapi.vercel.app/docs)

### Self-Hosting

#### Option 1: Docker (Recommended)

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/dhanyyudi/bmkg-api:latest

# Or build and run with Docker Compose
git clone https://github.com/dhanyyudi/bmkg-api.git
cd bmkg-api
docker-compose up -d
```

#### Option 2: Local Development

```bash
git clone https://github.com/dhanyyudi/bmkg-api.git
cd bmkg-api
make setup
source venv/bin/activate
make dev     # starts server on http://localhost:8099
```

#### Option 3: Vercel (Serverless)

Deploy to Vercel with one click — the `api/index.py` and `vercel.json` are pre-configured.

See [Self-Hosting Guide](https://bmkg-restapi.vercel.app/self-host.html) for detailed instructions.

### Code Examples

Available on the [landing page](https://bmkg-restapi.vercel.app) for: **cURL**, **JavaScript**, **Python**, **Go**, **PHP**, **Ruby**, and **Dart (Flutter)**.

---

<a name="bahasa-indonesia"></a>
## 🇮🇩 Bahasa Indonesia

API REST gratis untuk prakiraan cuaca, data gempa bumi, peringatan cuaca, dan pencarian wilayah Indonesia dari BMKG.

**🌐 Demo:** [https://bmkg-restapi.vercel.app](https://bmkg-restapi.vercel.app)

### ⚠️ Pemberitahuan Penting

Ini adalah **instance demo/publik** dengan batasan rate limit (30 request/menit).

**Untuk penggunaan produksi dengan request tanpa batas, silakan [self-host](#self-hosting-1).**

### Fitur

- 🌍 **Data Gempa** — Gempa terbaru, terkini (M 5.0+), dirasakan, pencarian radius
- 🌤️ **Prakiraan Cuaca** — 3 hari & cuaca saat ini untuk lokasi mana pun di Indonesia
- ⚠️ **Peringatan Cuaca (Nowcast)** — Peringatan dini real-time dengan poligon area terdampak
- 📍 **Pencarian Wilayah** — Provinsi, kabupaten, kecamatan, desa, plus pencarian
- 📊 **Dokumentasi Auto** — Dokumentasi API interaktif di `/docs`
- ⚡ **Caching** — Response cepat dengan cache lokal (TTL bisa dikonfigurasi)
- 🌐 **CORS Enabled** — Bisa dipakai dari frontend mana saja
- 🔓 **Tanpa API Key** — Akses sederhana dan anonim
- 📈 **Rate Limit Headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` di setiap response
- 🐳 **Docker & GHCR** — Image Docker multi-arsitektur otomatis di GitHub Container Registry

### Cepat Mulai

```bash
# Gempa terbaru
curl https://bmkg-restapi.vercel.app/v1/earthquake/latest

# Prakiraan cuaca Tebet Timur, Jakarta
curl https://bmkg-restapi.vercel.app/v1/weather/31.74.01.1001

# Cuaca saat ini
curl https://bmkg-restapi.vercel.app/v1/weather/31.74.01.1001/current

# Peringatan cuaca aktif
curl https://bmkg-restapi.vercel.app/v1/nowcast

# Cari wilayah
curl https://bmkg-restapi.vercel.app/v1/wilayah/search?q=wiradesa
```

### Endpoint API

#### 🌍 Gempa Bumi
| Endpoint | Deskripsi |
|----------|-----------|
| `GET /v1/earthquake/latest` | Gempa terbaru |
| `GET /v1/earthquake/recent` | Gempa terkini (M 5.0+) |
| `GET /v1/earthquake/felt` | Gempa dirasakan |
| `GET /v1/earthquake/nearby?lat=&lon=&radius_km=` | Gempa terdekat |

#### 🌤️ Cuaca
| Endpoint | Deskripsi |
|----------|-----------|
| `GET /v1/weather/{adm4_code}` | Prakiraan 3 hari |
| `GET /v1/weather/{adm4_code}/current` | Cuaca saat ini |

#### ⚠️ Nowcast (Peringatan Cuaca)
| Endpoint | Deskripsi |
|----------|-----------|
| `GET /v1/nowcast` | Peringatan cuaca aktif per provinsi |
| `GET /v1/nowcast/{alert_code}` | Detail peringatan dengan poligon area |
| `GET /v1/nowcast/check?location=` | Cek peringatan untuk lokasi tertentu |

#### 📍 Wilayah
| Endpoint | Deskripsi |
|----------|-----------|
| `GET /v1/wilayah/provinces` | Daftar provinsi |
| `GET /v1/wilayah/districts?province_code=` | Daftar kabupaten/kota |
| `GET /v1/wilayah/subdistricts?district_code=` | Daftar kecamatan |
| `GET /v1/wilayah/villages?subdistrict_code=` | Daftar desa/kelurahan |
| `GET /v1/wilayah/search?q={query}` | Cari wilayah |

**Dokumentasi lengkap:** [https://bmkg-restapi.vercel.app/docs](https://bmkg-restapi.vercel.app/docs)

### Self-Hosting

#### Opsi 1: Docker (Direkomendasikan)

```bash
# Pull dari GitHub Container Registry
docker pull ghcr.io/dhanyyudi/bmkg-api:latest

# Atau build dan jalankan dengan Docker Compose
git clone https://github.com/dhanyyudi/bmkg-api.git
cd bmkg-api
docker-compose up -d
```

#### Opsi 2: Lokal

```bash
git clone https://github.com/dhanyyudi/bmkg-api.git
cd bmkg-api
make setup
source venv/bin/activate
make dev     # jalankan server di http://localhost:8099
```

#### Opsi 3: Vercel (Serverless)

Deploy ke Vercel — `api/index.py` dan `vercel.json` sudah dikonfigurasi.

Lihat [Panduan Self-Hosting](https://bmkg-restapi.vercel.app/self-host.html) untuk detail.

### Contoh Kode

Tersedia di [halaman utama](https://bmkg-restapi.vercel.app) untuk: **cURL**, **JavaScript**, **Python**, **Go**, **PHP**, **Ruby**, dan **Dart (Flutter)**.

---

## Data Source

All data is sourced from [BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)](https://data.bmkg.go.id).

## Attribution

This API is **not affiliated with BMKG**. All data belongs to BMKG.

## License

MIT License — see [LICENSE](LICENSE)

---

**Built with ❤️ by [dhanypedia](https://github.com/dhanyyudi)**
