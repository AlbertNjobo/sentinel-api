# 🛡️ Sentinel API

> Real-time server health monitoring REST API — FastAPI + SQLite, deployed on any Ubuntu VPS.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite)](https://sqlite.org)
[![Ubuntu](https://img.shields.io/badge/OS-Ubuntu_22.04+-E95420?logo=ubuntu)](https://ubuntu.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Live API:** `http://<YOUR_SERVER_IP>/docs`

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | — | API info & endpoint map |
| `GET` | `/health` | — | Liveness probe — CPU, memory, disk snapshot |
| `GET` | `/metrics` | — | Full system metrics (CPU per-core, memory, swap, disk, network) |
| `GET` | `/processes?limit=N` | — | Top N processes by CPU usage |
| `GET` | `/alerts` | — | List alerts (filterable by `severity` & `resolved`) |
| `POST` | `/alerts` | ✅ Required | Create a new alert (persisted to SQLite) |
| `GET` | `/alerts/{id}` | — | Get single alert |
| `PATCH` | `/alerts/{id}/resolve` | ✅ Required | Mark alert resolved (stamps `resolved_at`) |
| `DELETE` | `/alerts/{id}` | ✅ Required | Delete alert |

Interactive docs: `/docs` (Swagger UI) · `/redoc` (ReDoc)

---

## Project structure

```
sentinel-api/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI app, route handlers, lifespan
│   ├── database.py   # async SQLite engine, session factory, init_db
│   ├── models.py     # SQLAlchemy ORM table + Pydantic schemas
│   ├── crud.py       # database operations (create/read/update/delete)
│   ├── metrics.py    # psutil wrappers for system metrics
│   └── auth.py       # API key authentication dependency
├── tests/
│   ├── conftest.py   # pytest fixtures, in-memory test database setup
│   └── test_api.py   # integration tests for all endpoints
├── scripts/
│   ├── deploy.sh                # one-shot Ubuntu 22.04+ deploy
│   ├── sentinel-api.service     # systemd unit
│   └── nginx-sentinel.conf      # Nginx reverse proxy
├── Dockerfile         # multi-stage Docker build
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Architecture

Sentinel API follows a layered architecture. Each layer has a single responsibility and communicates only with the layer directly below it:

```
  HTTP Request
       │
       ▼
┌─────────────────┐
│   main.py       │  Route handlers — parse requests, call dependencies,
│   (Routes)      │  delegate to CRUD or metrics, return responses
└────────┬────────┘
         │ depends on
    ┌────┴──────────────┐
    │                   │
    ▼                   ▼
┌─────────┐     ┌──────────────┐
│ auth.py │     │  metrics.py  │  System metrics (psutil) — no DB access
│ (Auth)  │     │  (Metrics)   │
└─────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│   crud.py       │  Database operations — all alert CRUD logic
│   (Data Access) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  database.py    │  SQLAlchemy async engine, session factory, schema init
│  (DB Setup)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   models.py     │  ORM table (AlertModel) + Pydantic schemas
│   (Models)      │  (AlertCreate, AlertRead, AlertListResponse)
└─────────────────┘
```

### Module guide

| Module | Purpose |
|--------|---------|
| `app/main.py` | Defines the `FastAPI` app instance, registers all routes, configures CORS middleware, and runs `init_db()` on startup via the lifespan context manager. |
| `app/database.py` | Creates the async SQLAlchemy engine from `DATABASE_URL`, exposes the `get_db()` session dependency used by route handlers, and provides `init_db()` to create tables on first run. |
| `app/models.py` | Contains the `AlertModel` SQLAlchemy ORM class (mapped to the `alerts` table) and the Pydantic schemas (`AlertCreate`, `AlertRead`, `AlertListResponse`) used for request validation and response serialisation. |
| `app/crud.py` | Pure database functions (`create_alert`, `get_alert`, `list_alerts`, `resolve_alert`, `delete_alert`) that accept an `AsyncSession` and return ORM objects. Contains no HTTP or business logic. |
| `app/metrics.py` | Wraps `psutil` calls into three plain functions: `health_snapshot()` (quick liveness check), `full_metrics()` (detailed host/CPU/memory/disk/network data), and `top_processes()`. No database access. |
| `app/auth.py` | Provides the `require_api_key()` FastAPI dependency. When `SENTINEL_API_KEY` is set it validates the `X-API-Key` request header; when unset (development) it allows all requests through automatically. |

---

## Configuration

All configuration is provided via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./sentinel.db` | SQLAlchemy async database URL. Override to use a custom path or in-memory DB. |
| `SENTINEL_API_KEY` | _(unset)_ | API key for write endpoints. If **not set**, authentication is disabled and all requests are accepted (development mode only — **never leave this unset in production**). |

Set variables before starting the server:

```bash
export DATABASE_URL="sqlite+aiosqlite:///./data/sentinel.db"
export SENTINEL_API_KEY="your-secret-key"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Authentication

Write endpoints (`POST`, `PATCH`, `DELETE` on `/alerts`) require a valid API key passed in the `X-API-Key` header. Read-only endpoints (`/health`, `/metrics`, `/processes`, `GET /alerts`) are always open.

```
X-API-Key: your-secret-key
```

**Development mode:** If `SENTINEL_API_KEY` is not set, the `require_api_key` dependency returns immediately without checking the header — useful for local development without environment setup. **Do not run in production without setting this variable**, as write endpoints will be completely unprotected.

---

## Run locally

```bash
git clone https://github.com/AlbertNjobo/sentinel-api
cd sentinel-api

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

`sentinel.db` is created automatically on first run.

---

## Testing

Install development dependencies, then run the test suite:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests use an **in-memory SQLite database** (`:memory:`) so they are fully isolated and leave no files on disk. The `conftest.py` fixtures create and drop all tables around each individual test.

Coverage includes:
- Health and metrics endpoints (no auth required)
- Authentication enforcement on write endpoints
- Full alert lifecycle: create → fetch → resolve → delete
- Alert filtering by `severity` and `resolved` status

---

## Example: Create an alert

```bash
curl -X POST http://<YOUR_SERVER_IP>/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SENTINEL_API_KEY" \
  -d '{
    "title": "High CPU Usage",
    "message": "CPU exceeded 90% for 5 consecutive minutes",
    "severity": "critical",
    "source": "sentinel-agent"
  }'
```

Alert severity levels: `info` · `warning` · `critical`

---

## Deploy to a Cloud Server

### 1. Create instance

- **Any Cloud Provider** (AWS, DigitalOcean, Linode, etc.) → Create instance
- Image: **Ubuntu 22.04+ LTS**
- Note the public IP

### 2. SSH and deploy

```bash
ssh root@<YOUR_SERVER_IP>

git clone https://github.com/AlbertNjobo/sentinel-api /opt/sentinel-api

# Then run:
bash /opt/sentinel-api/scripts/deploy.sh
```

The script handles everything end-to-end:
1. System update
2. Python 3 + Nginx + ufw installation
3. Dedicated `sentinel` system user (no root)
4. Python virtualenv + dependencies
5. **systemd** service (auto-restart on crash/reboot)
6. **Nginx** reverse proxy on port 80
7. **ufw** firewall (SSH + HTTP only)

### 3. Verify

```bash
curl http://<YOUR_SERVER_IP>/health
curl http://<YOUR_SERVER_IP>/metrics
```

### 4. Add HTTPS (optional but recommended)

```bash
apt install certbot python3-certbot-nginx -y
# Update server_name in /etc/nginx/sites-available/sentinel first
certbot --nginx -d yourdomain.com
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 |
| Server | Uvicorn (ASGI) |
| Database | SQLite via SQLAlchemy 2.0 async + aiosqlite |
| System metrics | psutil |
| Reverse proxy | Nginx |
| Process manager | systemd |
| OS | Ubuntu 22.04 LTS+ |

---

*Part of the [Sentinel](https://github.com/AlbertNjobo/sentinel) server monitoring ecosystem.*
