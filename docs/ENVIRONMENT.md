# Environment variables

Values below mirror [.env.example](../.env.example) and [docker-compose.yml](../docker-compose.yml). Compose injects sensible defaults so a `.env` file is optional for local dev.

## API and worker (shared)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pass@host:5432/cloudaudit` |
| `REDIS_URL` | Celery broker/result and Redis pub/sub, e.g. `redis://redis:6379/0` |
| `JWT_SECRET` | HMAC secret for JWT signing (change in production) |
| `JWT_ALGORITHM` | Default `HS256` (see `app/config.py`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 1440 |
| `ENCRYPTION_KEY` | Optional Fernet key (base64). If empty, dev derives from `JWT_SECRET` (not for production) |
| `CORS_ORIGINS` | Comma-separated browser origins for the SPA |
| `SCAN_OUTPUT_DIR` | Directory for Prowler JSON output (mounted volume in Compose) |
| `PROWLER_IMAGE` | Docker image for Prowler (worker), e.g. `prowlercloud/prowler:stable` ([Docker Hub](https://hub.docker.com/r/prowlercloud/prowler)) |
| `PROWLER_AUTO_PULL` | If `true`, Celery beat enqueues a periodic `docker pull` for `PROWLER_IMAGE` on the worker (requires `DOCKER_AVAILABLE` and mounted Docker socket). Default `false`. |
| `DOCKER_AVAILABLE` | Worker: `true` when Docker socket is mounted and `docker run` is allowed |
| `GITHUB_TOKEN` | Optional PAT for higher GitHub API rate limits on release checks |

## Frontend build (Vite)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Absolute API origin as seen by the **browser**, e.g. `http://localhost:8000`. Empty string uses same-origin + dev proxy. Set at **build time** for the `web` Docker image (`Dockerfile.web` `ARG`). |

## Seed script (API container)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEED_ADMIN_EMAIL` | `admin@example.com` | First admin user |
| `SEED_ADMIN_PASSWORD` | `admin123!` | Initial password |

## Docker Compose host ports

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_PORT` | `8000` | Host port published for the API (`API_PORT:8000` in container). |
| `WEB_PORT` | `5173` | Host port for the static UI container. |

The `web` image build arg `VITE_API_URL` is set to `http://localhost:${API_PORT}` so the browser calls the correct API origin. **Change `API_PORT` only with `docker compose up --build`** (or `docker compose build web`) so the SPA is rebuilt.

## Compose-only overrides

`docker-compose.yml` can be extended with `JWT_SECRET` and `PROWLER_IMAGE` from the host environment:

```bash
set JWT_SECRET=your-secret
set PROWLER_IMAGE=prowlercloud/prowler:stable
docker compose up --build
```

## Production checklist

- Set a strong `JWT_SECRET` and a dedicated `ENCRYPTION_KEY` (Fernet).
- Restrict `CORS_ORIGINS` to real UI origins.
- Do not mount Docker socket into long-lived workers; use a job runner pattern.
- Store `DATABASE_URL` and secrets in a managed secret store.
