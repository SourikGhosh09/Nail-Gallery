# Miss Universe Nail Art Studio 💅

**Elegance at Your Fingertips** — a complete, ready-to-run online catalogue for a
nail-art studio, with a beautiful public website and a secure admin panel for
managing your designs.

- **Customers** browse your designs, search and filter them, view prices and
  photos, and tap to enquire on **WhatsApp**. No sign-up needed.
- **You (the owner)** log in at `/admin` to add, edit, hide or delete designs
  and categories, and upload photos — all from your browser, no coding.

Everything is configured in one place (a file called `.env`) so you can rebrand
it for any studio in minutes.

---

## Table of contents

1. [Quick start (Windows — easiest)](#quick-start-windows--easiest)
2. [Quick start (Mac / Linux)](#quick-start-mac--linux)
3. [First login](#first-login)
4. [“How do I change…?” — the cheat sheet](#how-do-i-change--the-cheat-sheet)
5. [Using the admin panel](#using-the-admin-panel)
6. [Running with Docker (optional)](#running-with-docker-optional)
7. [Running the tests](#running-the-tests)
8. [How it’s built](#how-its-built)
9. [Troubleshooting](#troubleshooting)
10. [More documentation](#more-documentation)

---

## Quick start (Windows — easiest)

You need **Python 3.11 or newer** installed
([download here](https://www.python.org/downloads/) — tick **“Add Python to
PATH”** during install).

1. **Double-click `setup.bat`.**
   It creates an isolated environment, installs everything, creates your
   settings file, and fills the catalogue with tasteful demo designs.
2. **Double-click `dev.bat`.**
   Your site starts up.
3. Open **http://localhost:8000** in your browser. The admin panel is at
   **http://localhost:8000/admin**.

That’s it. To stop the site, close the black window (or press `Ctrl+C` in it).

## Quick start (Mac / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py setup      # creates .env (+ a secret key) and demo data
python backend/manage.py dev        # starts the site at http://localhost:8000
```

---

## First login

The setup step creates your administrator account from the settings file.
The **default** login is:

- **URL:** http://localhost:8000/admin
- **Email:** `admin@missuniverse.local`
- **Password:** `ChangeMe!123`

> ⚠️ **Change these before you go live.** Open the `.env` file, edit
> `ADMIN_EMAIL` and `ADMIN_PASSWORD`, then run:
>
> ```bash
> python backend/manage.py reset-admin
> ```
>
> (On Windows you can run this from a terminal in the project folder as
> `.venv\Scripts\python.exe backend\manage.py reset-admin`.)

---

## “How do I change…?” — the cheat sheet

Almost everything lives in the **`.env`** file in the project folder. Open it in
any text editor (Notepad is fine), change the value after the `=`, **save**, and
**restart** the site (close and re-run `dev.bat`).

| I want to change…                     | Where                                                                 |
|--------------------------------------|-----------------------------------------------------------------------|
| Studio **name / subtitle / tagline** | `.env` → `STUDIO_NAME`, `STUDIO_SUBTITLE`, `STUDIO_TAGLINE`            |
| Studio **description** (for Google)  | `.env` → `STUDIO_DESCRIPTION`                                         |
| **WhatsApp** number for enquiries    | `.env` → `WHATSAPP_NUMBER` (digits only, e.g. `919876543210`)          |
| **Contact** email / phone / address  | `.env` → `CONTACT_EMAIL`, `CONTACT_PHONE`, `CONTACT_ADDRESS`           |
| **Instagram / Facebook** links       | `.env` → `INSTAGRAM_URL`, `FACEBOOK_URL`                              |
| **Currency** (₹, $, €, …)            | `.env` → `CURRENCY_SYMBOL` and `CURRENCY_CODE`                        |
| **Admin** email / password           | `.env` → `ADMIN_EMAIL`, `ADMIN_PASSWORD`, then `python backend/manage.py reset-admin` |
| Website **address** (for SEO/links)  | `.env` → `BASE_URL` (e.g. `https://www.yourstudio.com`)               |
| Max upload size / allowed image types| `.env` → `MAX_UPLOAD_MB`, `ALLOWED_IMAGE_EXTENSIONS`                  |
| **On-page logo** (header/footer/admin) | Replace `frontend/static/img/logo.png` (a square image works best)          |
| **Browser-tab icon** (favicon)       | Replace `frontend/static/img/favicon.png`, `favicon.ico` and `apple-touch-icon.png` |
| Social **share image**               | Replace `frontend/static/img/og-default.svg`                                  |
| **Colours / fonts** (the theme)      | `frontend/static/css/styles.css` (public) and `frontend/static/css/admin.css` (admin) — edit the `:root { … }` block at the top |
| **Designs & categories**             | No code — use the **admin panel** (see below)                        |

> The categories are **not** hard-coded — you create them in the admin panel and
> they appear on the public site automatically.

### Changing the colours

Open `frontend/static/css/styles.css`. Right at the top you’ll find:

```css
:root {
  --rose: #b76e79;       /* main accent */
  --rose-deep: #9d5763;  /* darker accent */
  --gold: #c6a15b;       /* highlights */
  /* … */
}
```

Change the hex colour codes to your palette and refresh the page. (Do the same
in `frontend/static/css/admin.css` if you want the admin panel to match.)

---

## Using the admin panel

Go to **/admin** and log in. You’ll see:

- **Dashboard** — totals at a glance, your most recent designs, and quick links.
- **Nail Arts** — your designs. You can:
  - **Add** a design (name, description, price, category, photo).
  - **Edit** any detail or **replace the photo**.
  - **Activate / Deactivate** — deactivated designs are hidden from customers but
    kept safely in your records (this is the recommended “soft delete”).
  - **Delete permanently** if you’re sure.
  - **Search, filter and sort** to find a design quickly.
- **Categories** — e.g. Bridal, Chrome, French. You can add, rename, hide or
  delete them. **Deleting a category that still has designs is prevented** — the
  app will ask you to either:
  - **Move** the designs to another category and then delete, or
  - **Deactivate** (hide) the category instead, or
  - **Cancel**.

  This means you can never accidentally “lose” designs.

Photos are checked to be real images, stripped of hidden metadata, and
automatically resized for fast loading.

### What customers see

- A polished home page, a full **catalogue** with **live search**, **category
  filters** and **sorting**, and a detail page for each design.
- An **“Enquire on WhatsApp”** button that opens WhatsApp with a friendly
  pre-filled message, e.g. *“Hello Miss Universe Nail Art Studio, I am interested
  in Royal Pink Chrome.”*

---

## Running with Docker (optional)

If you prefer containers:

```bash
cp .env.example .env     # then edit ADMIN_EMAIL / ADMIN_PASSWORD
docker compose up --build
```

Open http://localhost:8000. Your database and uploaded photos are stored in
named volumes so they survive restarts. See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production notes (including
PostgreSQL).

---

## Running the tests

The project ships with an automated test suite (59 tests) covering login,
security, catalogue search/filtering, validation, image-upload rejection and the
“never orphan a design” category rules.

```bash
pip install -r requirements-dev.txt
python backend/manage.py test
```

---

## How it’s built

A single, self-contained **Python** application — no Node.js, no build step.

| Layer      | Choice                          | Why                                              |
|------------|---------------------------------|--------------------------------------------------|
| Web        | **FastAPI** + **Uvicorn**       | Fast, modern, automatic input validation & docs  |
| Templates  | **Jinja2** (server-rendered)    | Works without JavaScript; JS only enhances it     |
| Database   | **SQLite** (default) via **SQLAlchemy** | Zero setup; switch to PostgreSQL/MySQL by editing one line |
| Auth       | **JWT** in an httpOnly cookie   | Sessions can’t be read by JavaScript              |
| Passwords  | **PBKDF2-HMAC-SHA256** (stdlib) | OWASP-recommended; no compiler needed to install  |
| Images     | **Pillow**                      | Validates & optimises uploads                     |

```
Nail Catalog/
├─ backend/             # Python server and its tests
│  ├─ app/              # application code
│  │  ├─ main.py        # app setup, security headers, error pages, startup
│  │  ├─ config.py      # every setting (reads .env)
│  │  ├─ models.py      # database tables
│  │  └─ routers/       # public pages, public API, admin pages, admin API, auth
│  ├─ tests/            # automated tests
│  ├─ manage.py         # setup / seed / dev / serve / test / reset-admin
│  └─ requirements.txt  # Python packages
├─ frontend/            # browser-facing files
│  ├─ templates/        # HTML (public + admin)
│  └─ static/           # CSS, JavaScript, images (edit theme here)
├─ storage/uploads/     # uploaded photos (created automatically)
├─ .env.example         # copy to .env and edit
├─ setup.bat / dev.bat  # Windows one-click scripts
└─ Dockerfile, docker-compose.yml
```

Useful commands (all via `python backend/manage.py …`):

| Command         | What it does                                        |
|-----------------|-----------------------------------------------------|
| `setup`         | Create `.env` (with a secret key) and seed demo data |
| `dev`           | Start the site with auto-reload (development)        |
| `serve`         | Start the site for production                        |
| `seed`          | Re-add demo content (only if the catalogue is empty) |
| `reset-admin`   | Reset the admin login to match `.env`                |
| `test`          | Run the automated tests                              |

---

## Troubleshooting

**“Python was not found.”**
Install Python 3.11+ from python.org and tick *“Add Python to PATH”*, then run
`setup.bat` again.

**Port 8000 is already in use.**
Start on another port: `python backend/manage.py dev --port 8080`, then open
http://localhost:8080.

**I forgot the admin password.**
Edit `ADMIN_PASSWORD` in `.env`, save, then run `python backend/manage.py reset-admin`.

**I want to start the catalogue from scratch.**
Stop the site, delete the database file (`nailstudio.db` in the project folder),
then run `python backend/manage.py setup` again. *(This erases all designs — be sure.)*

**My changes to `.env` didn’t take effect.**
Save the file and **restart** the site (close and re-run `dev.bat`).

**The WhatsApp button opens the wrong number.**
`WHATSAPP_NUMBER` must be digits only, in full international format (no `+`,
spaces or dashes), e.g. India `+91 98765 43210` → `919876543210`.

---

## More documentation

- **[docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) — see your site live in ~15 min on Render's FREE plan (great for a quick test drive).** 🚀
- **[docs/DEPLOY_ORACLE.md](docs/DEPLOY_ORACLE.md) — put your site online for FREE, permanently, on your own domain (step-by-step, no coding).** ⭐
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — other/production hosting options (generic VPS, PostgreSQL, etc.).
- [docs/SECURITY.md](docs/SECURITY.md) — how the app keeps things safe, and your checklist.
- [docs/API.md](docs/API.md) — the REST API reference (for developers).
- Interactive API docs are available while the site runs at `/api/docs`.

---

*Built to be handed over: sensible defaults everywhere, nothing secret in the
code, and every visible feature works.*
#   N a i l - G a l l e r y  
 