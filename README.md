# 🛡️ Sentinel API

> Real-time server health monitoring REST API — FastAPI + SQLite, deployed on Vultr.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite)](https://sqlite.org)
[![Vultr](https://img.shields.io/badge/Deployed-Vultr-007BFC)](https://vultr.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Live API:** `http://66.42.82.73/docs`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info & endpoint map |
| `GET` | `/health` | Liveness probe — CPU, memory, disk snapshot |
| `GET` | `/metrics` | Full system metrics (CPU per-core, memory, swap, disk, network) |
| `GET` | `/processes?limit=N` | Top N processes by CPU usage |
| `GET` | `/alerts` | List alerts (filterable by `severity` & `resolved`) |
| `POST` | `/alerts` | Create a new alert (persisted to SQLite) |
| `GET` | `/alerts/{id}` | Get single alert |
| `PATCH` | `/alerts/{id}/resolve` | Mark alert resolved (stamps `resolved_at`) |
| `DELETE` | `/alerts/{id}` | Delete alert |

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
│   └── metrics.py    # psutil wrappers for system metrics
├── scripts/
│   ├── deploy.sh                # one-shot Vultr deploy
│   ├── sentinel-api.service     # systemd unit
│   └── nginx-sentinel.conf      # Nginx reverse proxy
├── requirements.txt
└── README.md
```

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

## Deploy to Vultr

### 1. Create instance

- **Vultr dashboard** → Create → Cloud Compute → Shared CPU
- Image: **Ubuntu 22.04 LTS**
- Plan: **$6/mo (1 vCPU · 1 GB RAM)**
- Note the public IP

### 2. SSH and deploy

```bash
ssh root@66.42.82.73

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
curl http://66.42.82.73/health
curl http://66.42.82.73/metrics
```

### 4. Add HTTPS (optional but recommended)

```bash
apt install certbot python3-certbot-nginx -y
# Update server_name in /etc/nginx/sites-available/sentinel first
certbot --nginx -d yourdomain.com
```

---

## Example: Create an alert

```bash
curl -X POST http://66.42.82.73/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SENTINEL_API_KEY" \
  -d '{
    "title": "High CPU Usage",
    "message": "CPU exceeded 90% for 5 consecutive minutes",
    "severity": "critical",
    "source": "sentinel-agent"
  }'
```

> **Note:** Write endpoints (POST, PATCH, DELETE) require a valid API key.
> Set it on the server: `export SENTINEL_API_KEY="your-secret-key"`
> Read-only endpoints (`/health`, `/metrics`, `/processes`, `GET /alerts`) remain open.

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
| Cloud | Vultr Cloud Compute |

---

## Devpost Description

> Copy-paste this into the Devpost submission form.

### Inspiration

Managing servers in resource-constrained environments — like those common across Zimbabwe and Southern Africa — means you often can't afford heavyweight monitoring stacks like Datadog or New Relic. Sentinel API is a lightweight, self-hostable alternative that gives you real-time visibility into server health without the SaaS price tag.

### What it does

Sentinel API is a RESTful server health monitor with two core capabilities:

1. **Live system metrics** — query CPU (per-core), memory, swap, disk, and network I/O from any HTTP client. The `/health` endpoint returns a `healthy`/`degraded` status suitable for load balancers and uptime monitors.

2. **Persistent alert management** — create, filter, resolve, and delete alerts via a full CRUD API. Alerts are stored in SQLite and survive server restarts, making it a real operational tool rather than a toy demo.

### How I built it

- **FastAPI** for the async HTTP layer — chosen for its automatic OpenAPI docs, Pydantic validation, and async-native design
- **SQLAlchemy 2.0 async + aiosqlite** for non-blocking SQLite persistence
- **psutil** for cross-platform system metric collection
- **Uvicorn** as the ASGI server, managed by **systemd** for auto-restart
- **Nginx** as a reverse proxy, **ufw** for firewall rules
- Deployed to a **Vultr Cloud Compute** $6/mo Ubuntu 22.04 instance

### Challenges

Getting SQLAlchemy's async session lifecycle to integrate cleanly with FastAPI's dependency injection system required careful attention — particularly ensuring the lifespan context manager initialised the database before the first request hit.

### What I learned

FastAPI's `lifespan` pattern is the right way to handle startup/shutdown logic in modern async apps — much cleaner than the deprecated `@app.on_event` approach. I also deepened my understanding of systemd hardening options (`NoNewPrivileges`, `PrivateTmp`).

### What's next

- API key authentication middleware
- Prometheus `/metrics` endpoint for Grafana integration
- Alert webhooks (Slack/email notifications)
- Multi-server agent that pushes metrics to a central Sentinel instance

---

*Part of the [Sentinel](https://github.com/AlbertNjobo/sentinel) server monitoring ecosystem.*
