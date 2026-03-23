# Setup and local development

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2) with Linux containers
- For native frontend dev without Docker: **Node.js 20+** and **npm**

## Start the full stack

From the repository root:

```bash
docker compose up --build
```

Services:

| Service | Port | Role |
|---------|------|------|
| postgres | 5432 | Database |
| redis | 6379 | Broker + pub/sub |
| api | 8000 | FastAPI + Alembic migrate + seed |
| worker | — | Celery worker (**requires Docker socket**) |
| beat | — | Celery beat |
| web | 5173 | Static UI (`serve`) |

## First login

After the API container starts, the seed script creates (if missing):

- Email: `admin@example.com`
- Password: `admin123!`

Override with environment variables `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` on the `api` service.

## Docker socket on Windows

Mounting `/var/run/docker.sock` works with **Docker Desktop WSL2 backend**. Native Windows Docker paths differ; if the worker cannot run `docker`, scans will fail with a clear error when `DOCKER_AVAILABLE` is true but the daemon is unreachable.

The **worker image** installs Docker’s **static CLI** into `/usr/local/bin/docker` (not the Debian `docker.io` package), so `docker run …` works reliably inside the container when the socket is mounted.

If **Docker from PowerShell fails** (e.g. `dockerDesktopLinuxEngine` pipe error) but Linux Docker works, run Compose from **WSL** instead:

```bash
wsl -e bash -lc "cd /mnt/f/cloudsecurity && docker compose up --build"
```

Adjust the path if your repo is not on drive `F:` (for example `/mnt/c/Users/you/projects/cloudsecurity`).

## Run API tests / migrations only

With Python 3.12+ and Postgres/Redis running:

```bash
cd services/api
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://prowler:prowler@localhost:5432/cloudaudit
alembic upgrade head
```

## Run frontend against local API

```bash
cd web
npm install
# Optional: create .env with VITE_API_URL=http://localhost:8000
npm run dev
```

## Port already in use (`address already in use` on 8000)

Another process on the host is bound to port **8000** (uvicorn, another API, etc.). Either stop that process or map the API to a different host port and rebuild the web image so the SPA points at the same URL:

```bash
API_PORT=8001 docker compose up --build
```

Then open the API at `http://localhost:8001` and the UI at `http://localhost:5173` (or set `WEB_PORT` if 5173 is taken).

## OpenAPI

Browse `http://localhost:8000/docs` (or `http://localhost:<API_PORT>/docs` if overridden) for interactive API documentation.
