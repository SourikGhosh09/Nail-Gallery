#!/usr/bin/env python
"""
Miss Universe Nail Art Studio — project management CLI.

A single, friendly entry point for the common tasks, so you never have to
remember long commands.  Run it with the project's Python:

    python manage.py setup     Create .env (with a fresh secret key) + seed data
    python manage.py seed      (Re)seed the database with demo content
    python manage.py dev       Start the website with auto-reload (development)
    python manage.py serve     Start the website for production
    python manage.py test      Run the automated test suite
    python manage.py ensure-admin   Make sure the admin account exists

Everything is designed to "just work" with sensible defaults.
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

# manage.py lives in backend/. Operate from here so the "app" package imports
# cleanly (e.g. `uvicorn app.main:app`). The app anchors its own data and
# frontend paths absolutely (see app/config.py), so the .env file, the database
# and the storage/ folder all still live at the project root.
BASE_DIR = Path(__file__).resolve().parent        # .../backend
PROJECT_ROOT = BASE_DIR.parent                     # the project root
os.chdir(BASE_DIR)

# Make console output UTF-8 safe (Windows terminals default to a legacy codec).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _create_env_if_missing() -> bool:
    """Create .env from .env.example with a freshly generated SECRET_KEY."""
    if ENV_FILE.exists():
        _say("  - .env already exists (leaving it untouched).")
        return False
    if not ENV_EXAMPLE.exists():
        _say("  ! .env.example is missing; cannot create .env automatically.")
        return False

    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    new_key = secrets.token_urlsafe(48)
    text, n = re.subn(r"^SECRET_KEY=.*$", f"SECRET_KEY={new_key}", text, flags=re.MULTILINE)
    if n == 0:
        text += f"\nSECRET_KEY={new_key}\n"
    ENV_FILE.write_text(text, encoding="utf-8")
    _say("  [OK] Created .env with a freshly generated SECRET_KEY.")
    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_setup(_args: argparse.Namespace) -> int:
    _say("Setting up Miss Universe Nail Art Studio...")
    _say("")
    _say("1) Environment configuration")
    created = _create_env_if_missing()

    _say("")
    _say("2) Database + demo content")
    # Import lazily so settings read the .env we may have just written.
    from app.seed import main as seed_main

    seed_main()

    _say("")
    _say("Setup complete.")
    if created:
        _say("")
        _say("IMPORTANT: open .env and change ADMIN_EMAIL / ADMIN_PASSWORD")
        _say("before you go live. The default login is:")
        from app.config import settings

        _say(f"    email:    {settings.ADMIN_EMAIL}")
        _say(f"    password: (as set in .env)")
    _say("")
    _say("Next: run  python manage.py dev   and open http://localhost:8000")
    return 0


def cmd_seed(_args: argparse.Namespace) -> int:
    from app.seed import main as seed_main

    seed_main()
    return 0


def cmd_ensure_admin(_args: argparse.Namespace) -> int:
    from app.main import ensure_admin

    ensure_admin()
    from app.config import settings

    _say(f"[OK] Admin account ensured for: {settings.ADMIN_EMAIL}")
    return 0


def cmd_reset_admin(_args: argparse.Namespace) -> int:
    """Force the admin account to match ADMIN_* in .env (use if you forgot the
    password: edit .env, then run this)."""
    from sqlalchemy import select

    from app.config import settings
    from app.database import SessionLocal, init_db
    from app.models import User
    from app.security import hash_password

    init_db()
    db = SessionLocal()
    try:
        email = settings.ADMIN_EMAIL.lower().strip()
        admin = db.scalar(select(User).where(User.role == "admin"))
        if admin is None:
            db.add(User(
                name=settings.ADMIN_NAME, email=email,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin", is_active=True,
            ))
            _say(f"[OK] Created admin account: {email}")
        else:
            admin.name = settings.ADMIN_NAME
            admin.email = email
            admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
            admin.is_active = True
            _say(f"[OK] Reset admin credentials for: {email}")
        db.commit()
    finally:
        db.close()
    return 0


def cmd_dev(args: argparse.Namespace) -> int:
    _say(f"Starting development server on http://{args.host}:{args.port} (auto-reload)...")
    _say("Public site:  http://localhost:%s/" % args.port)
    _say("Admin panel:  http://localhost:%s/admin" % args.port)
    _say("Press CTRL+C to stop.")
    return subprocess.call(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--reload", "--host", args.host, "--port", str(args.port)]
    )


def cmd_serve(args: argparse.Namespace) -> int:
    _say(f"Starting production server on http://{args.host}:{args.port} ...")
    return subprocess.call(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", args.host, "--port", str(args.port), "--workers", str(args.workers)]
    )


def cmd_test(args: argparse.Namespace) -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.call([sys.executable, "-m", "pytest", *args.pytest_args], env=env)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Management commands for Miss Universe Nail Art Studio.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Create .env + seed the database (run this first).").set_defaults(func=cmd_setup)
    sub.add_parser("seed", help="(Re)seed the database with demo content.").set_defaults(func=cmd_seed)
    sub.add_parser("ensure-admin", help="Create the admin account if it does not exist.").set_defaults(func=cmd_ensure_admin)
    sub.add_parser("reset-admin", help="Reset the admin login to match .env (forgot password?).").set_defaults(func=cmd_reset_admin)

    p_dev = sub.add_parser("dev", help="Start the site with auto-reload (development).")
    p_dev.add_argument("--host", default="127.0.0.1")
    p_dev.add_argument("--port", type=int, default=8000)
    p_dev.set_defaults(func=cmd_dev)

    p_serve = sub.add_parser("serve", help="Start the site for production.")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--workers", type=int, default=2)
    p_serve.set_defaults(func=cmd_serve)

    p_test = sub.add_parser("test", help="Run the automated test suite.")
    p_test.add_argument("pytest_args", nargs=argparse.REMAINDER,
                        help="Extra arguments passed straight to pytest.")
    p_test.set_defaults(func=cmd_test)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
