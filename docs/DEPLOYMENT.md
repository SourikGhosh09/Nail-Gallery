# Deployment Guide

This app is a standard ASGI (FastAPI) application. It runs anywhere Python runs:
a VPS, a container platform, or a PaaS. This guide covers a straightforward,
secure production setup.

> **In a hurry?** The fastest safe path is Docker: set `.env`, then
> `docker compose up --build -d`. Skip to [Docker](#option-b-docker).

---

## 1. Production settings (`.env`)

Create a `.env` (copy from `.env.example`) and set at least:

```ini
ENV=production
# A long, unique random string. Generate one, e.g.:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=<paste-a-long-random-string>

# Your real admin login
ADMIN_EMAIL=you@yourstudio.com
ADMIN_PASSWORD=<a-strong-password>

# Your public address (used for SEO, sitemap, Open Graph, and CORS)
BASE_URL=https://www.yourstudio.com

# Branding / contact / currency (see .env.example for the full list)
STUDIO_NAME=...
WHATSAPP_NUMBER=919876543210
```

> **Why `ENV=production` matters:** it turns on `Secure` cookies and HSTS, so the
> site **must** be served over **HTTPS** (see step 4). Over plain HTTP the login
> cookie won’t be sent and you won’t be able to log in.

After first deploy, if you change `ADMIN_PASSWORD` later, run
`python backend/manage.py reset-admin` to apply it.

---

## 2. Choose a database

- **SQLite (default):** zero setup, great for a single small site. Keep the
  database file and the `storage/uploads/` folder on **persistent** storage and
  **back them up**.
- **PostgreSQL (recommended for production):**
  ```ini
  DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/nailstudio
  ```
  Install the driver: `pip install "psycopg[binary]"`.
- **MySQL/MariaDB:**
  ```ini
  DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/nailstudio
  ```
  Install the driver: `pip install pymysql`.

Tables are created automatically on startup (`create_all`), so no manual
migration step is required to get running. (If you later evolve the schema,
introduce Alembic; it isn’t needed for initial deployment.)

---

## Option A: Run directly with Uvicorn

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
# one-off: create .env + admin + demo data (or just python backend/manage.py ensure-admin)
python backend/manage.py setup

# start (2 workers shown; tune to your CPU)
python backend/manage.py serve --host 0.0.0.0 --port 8000 --workers 2
# equivalent to:
# uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 2
```

Keep it running with a process manager. Example **systemd** unit
(`/etc/systemd/system/nailstudio.service`):

```ini
[Unit]
Description=Miss Universe Nail Art Studio
After=network.target

[Service]
WorkingDirectory=/srv/nailstudio
Environment=PATH=/srv/nailstudio/.venv/bin
ExecStart=/srv/nailstudio/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 2
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now nailstudio
```

---

## Option B: Docker

```bash
cp .env.example .env      # then edit ENV, SECRET_KEY, ADMIN_*, BASE_URL …
docker compose up --build -d
```

- The database (SQLite) and uploaded images are stored in named volumes
  (`data`, `uploads`) so they persist across restarts and image rebuilds.
- Health is reported via `/healthz` (Compose healthcheck already configured).
- To use PostgreSQL, uncomment the `db:` service in `docker-compose.yml` and set
  `DATABASE_URL` in `.env` (the compose file shows the exact value). Add
  `psycopg[binary]` to `backend/requirements.txt` before building.

---

## 4. Put it behind HTTPS (reverse proxy)

Terminate TLS at a reverse proxy and forward to the app. **Caddy** does HTTPS
automatically:

```
www.yourstudio.com {
    reverse_proxy 127.0.0.1:8000
}
```

**Nginx** equivalent (use Certbot for the certificate):

```nginx
server {
    server_name www.yourstudio.com;
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        client_max_body_size 10m;   # allow image uploads
    }
    listen 443 ssl;
    # ssl_certificate / ssl_certificate_key managed by Certbot
}
```

The app already sends strong security headers (CSP, HSTS in production,
`X-Content-Type-Options`, `X-Frame-Options`, etc.) — see
[SECURITY.md](SECURITY.md).

---

## 5. Static files & uploads

- App assets in `frontend/static/` and uploaded photos under `/media` are served by the
  app out of the box. For higher traffic you can let Nginx serve `/static` and
  the uploads directory directly, but it’s optional.
- **Uploads live on disk** (`UPLOAD_DIR`, default `storage/uploads`). Ensure that
  path is writable and included in backups. In Docker it’s the `uploads` volume.

---

## 6. Backups

Back up two things regularly:

1. The **database** (the SQLite file, or your Postgres/MySQL dump).
2. The **uploads** directory.

That’s your entire catalogue.

---

## 7. Go-live checklist

- [ ] `ENV=production` and a strong unique `SECRET_KEY`
- [ ] Real `ADMIN_EMAIL` / `ADMIN_PASSWORD` set (then `reset-admin` if changed)
- [ ] `BASE_URL` set to your real HTTPS domain
- [ ] Served over HTTPS via a reverse proxy
- [ ] Database + uploads on persistent storage and backed up
- [ ] `WHATSAPP_NUMBER`, contact details, branding and currency set
- [ ] `python backend/manage.py test` passes
- [ ] Logged in at `/admin`, added a real design, confirmed it shows publicly
