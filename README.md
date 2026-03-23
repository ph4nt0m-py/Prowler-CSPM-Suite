# Prowler CSPM Suite

Production-oriented monorepo for running **Prowler**-backed cloud security posture management: **FastAPI** API, **Celery** workers, **PostgreSQL**, **Redis**, and a **React** (Vite + Tailwind) UI. Designed local-first via Docker Compose; logical boundaries support splitting services later.

## Quick start

```bash
docker compose up --build
```

- API: [http://localhost:8000](http://localhost:8000) — OpenAPI: `/docs`  
  If **port 8000 is already in use**, run `API_PORT=8001 docker compose up --build` and use `http://localhost:8001`.
- UI: [http://localhost:5173](http://localhost:5173)
- Default admin (after seed): `admin@example.com` / `admin123!` (override with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`)

The worker container needs access to the **Docker socket** to run Prowler in sibling containers (see [docs/SETUP.md](docs/SETUP.md)). On Windows, if the Docker CLI fails from PowerShell, use **WSL** and `docker compose` from your repo path under `/mnt/...` (details in SETUP).

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Index of all reference docs |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, components, flows |
| [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) | Repository layout |
| [docs/DATABASE.md](docs/DATABASE.md) | PostgreSQL schema and conventions |
| [docs/API.md](docs/API.md) | REST + WebSocket reference and samples |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | Environment variables |
| [docs/SECURITY.md](docs/SECURITY.md) | Encryption, RBAC, audit logs, Prowler sandbox |
| [docs/WORKER_AND_PROWLER.md](docs/WORKER_AND_PROWLER.md) | Celery tasks, queues, runner, diff pipeline |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Web app, env, proxy, user flows |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Prowler image updates, production notes |
| [docs/CORE_IMPLEMENTATION.md](docs/CORE_IMPLEMENTATION.md) | Code map: scans, diff, triage |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Spec traceability (incl. bonus gaps) |
| [Prowler official docs](https://docs.prowler.com/) | Upstream reference for scan CLI, output modes (e.g. JSON-OCSF), and compliance concepts used by our worker and findings UI |

Copy [.env.example](.env.example) to `.env` if you want to override compose defaults.

## License
