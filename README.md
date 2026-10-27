# InfraWatch

![Tests](https://github.com/tur4aaaa/Infra-Watch/actions/workflows/tests.yml/badge.svg)

Linux server monitoring system built with Python.

A lightweight agent collects system metrics on each server and sends them to a central backend, so you can monitor all your machines from one dashboard without connecting to each server manually...

## Features

**Agent**
* CPU usage via `/proc/stat` (all CPU time fields, iowait counted as idle)
* Memory usage via `/proc/meminfo`
* Disk usage (calculated the same way as `df`)
* Network throughput via `/proc/net/dev` (all interfaces except loopback)
* Sends metrics every 10 seconds with exponential backoff on failures

**Backend & dashboard**
* REST API on FastAPI with request validation via Pydantic
* Metrics history stored in ClickHouse with 30-day TTL and automatic downsampling for charts
* Web dashboard: server list with online/offline status and per-server charts (1h / 24h / 7d)

**Users & security**
* User registration and login
* Passwords hashed with **Argon2** (memory-hard, salted; never stored in plain text)
* Server-side sessions in Redis with `HttpOnly` / `SameSite` cookies and instant logout
* Timing-attack protection on login (constant-time path for unknown emails)
* Per-server API tokens for agents (shown once, stored as SHA-256 hash)
* Parameterized SQL queries (SQL injection protection) and HTML escaping (XSS protection)

## Architecture

```
Linux server ──► Python agent ──► FastAPI backend ──► ClickHouse  (metrics, time series)
                                         │       ├──► PostgreSQL  (users, servers)
                                         │       └──► Redis       (sessions)
                                         ▼
                                  Web dashboard (HTML/CSS/JS + Chart.js)
```

Each storage is used for what it does best: ClickHouse for large volumes of time-series data, PostgreSQL for relational data with strict constraints, Redis for short-lived sessions with TTL.

## Tech Stack

* **Python**: FastAPI, Pydantic, SQLAlchemy, httpx
* **Databases**: ClickHouse, PostgreSQL, Redis
* **Security**: Argon2 (argon2-cffi), server-side sessions
* **Frontend**: HTML, CSS, JavaScript, Chart.js
* **Infrastructure**: Docker, Docker Compose, Linux (`/proc`)
* **Testing & CI**: pytest, GitHub Actions

## Quick Start

```bash
cp .env.example .env   # then set CLICKHOUSE_PASSWORD and POSTGRES_PASSWORD
docker compose up -d --build
```

Open http://127.0.0.1:8000 (API docs: http://127.0.0.1:8000/docs)

Useful commands:

```bash
docker compose ps              # status of all services
docker compose logs -f agent   # follow agent logs
docker compose down            # stop everything (data is kept)
```

## Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -v
```

Tests run automatically on every push via GitHub Actions. Databases are replaced with fakes, so tests need no running services.

## Project Status

🚧 Work in progress.

- [x] Linux monitoring agent
- [x] FastAPI backend and ClickHouse storage
- [x] Web dashboard with charts
- [x] Docker Compose setup
- [x] Unit/API tests and CI
- [x] User registration and login (Argon2, Redis sessions)
- [ ] Agent authentication with per-server tokens
- [ ] Per-user data isolation and login pages
- [ ] One-line agent installer (systemd service)
- [ ] Deployment with HTTPS (nginx, Let's Encrypt)
- [ ] End-to-end tests (Playwright)
- [ ] Kubernetes
