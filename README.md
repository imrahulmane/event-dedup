# Event Dedup

A backend service that receives events via HTTP, detects duplicates using a composite key, and stores only unique events.

## Stack

- FastAPI
- Redis (atomic dedup via `SET NX EX`)
- Postgres (durable storage with unique constraint as safety net)
- Prometheus + Grafana (metrics and dashboards)

## Run

```bash
# Bring up postgres, redis, prometheus, grafana
docker compose up -d

# Install deps
uv sync

# Run the app
uvicorn main:app --host 0.0.0.0
```

## Endpoints

- `POST /events` — submit an event
- `GET /events` — list accepted events (paginated)
- `GET /health` — Redis and Postgres status
- `GET /metrics` — Prometheus metrics

## Config

Set in `.env`:

```
DATABASE_URL=postgresql+asyncpg://myuser:mypassword@localhost:5433/mydb
REDIS_URL=redis://localhost:6380
DEDUP_STRICT_MODE=true
DEDUP_TTL_SECONDS=86400
```

## Dashboards

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / admin)
