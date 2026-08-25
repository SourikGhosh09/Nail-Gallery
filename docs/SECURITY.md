# Security Overview

Security was a first-class requirement for this project. This document explains
what protections are built in, and gives you a short checklist for going live.

---

## What’s built in

### Authentication & sessions
- **Passwords are never stored in plaintext.** They’re hashed with
  **PBKDF2-HMAC-SHA256** (600,000 iterations), an OWASP-recommended, NIST-approved
  algorithm from the Python standard library (no fragile native dependencies).
  Verification is constant-time.
- **Sessions use a signed JWT in an `httpOnly` cookie** (`access_token`), so the
  token can’t be read or stolen by JavaScript (mitigates XSS session theft).
  Cookies are `SameSite=Lax` and marked `Secure` in production.
- The **first admin is created from environment variables** (`ADMIN_EMAIL` /
  `ADMIN_PASSWORD`), never hard-coded in source.

### The admin API is genuinely protected
- Every `/api/admin/*` route requires a valid admin session. Admin status is
  decided **on the server** from the session — never trusted from the browser.
- Unauthenticated reads return **401**; unauthenticated writes are blocked by the
  CSRF check and return **403**. Either way, they never execute.

### CSRF protection
- State-changing admin requests use the **double-submit cookie** pattern: a
  signed `csrf_token` must be sent in the `X-CSRF-Token` header and match the
  cookie. Tokens are signed and time-limited (`itsdangerous`).

### Brute-force protection
- Logins are **rate-limited** per client+email using a sliding window
  (`LOGIN_RATE_LIMIT_ATTEMPTS` / `LOGIN_RATE_LIMIT_WINDOW_SECONDS`). Exceeding it
  returns **429** with a `Retry-After`.
- Login failures return a **deliberately vague** message (“Invalid e-mail or
  password.”) so they don’t reveal which field was wrong.

### Input validation
- All input is validated with **Pydantic** schemas (types, lengths, ranges,
  email format). Invalid input returns a clean **422** — it never reaches the
  database.

### Safe file uploads
- Uploaded images are validated by **extension, size, and by actually decoding
  them with Pillow** (a disguised or corrupt file is rejected).
- Files are **re-encoded and stripped of metadata**, downscaled if very large,
  and stored under **random names** inside the upload directory — preventing
  path traversal and filename collisions. Deletion is likewise confined to the
  upload directory.

### Output & headers
- Templates **auto-escape** output (Jinja2), and the client-side rendering path
  escapes values too — defending against XSS.
- Every response carries **security headers**: a strict **Content-Security-Policy
  with a per-request nonce** (no inline scripts), `X-Content-Type-Options:
  nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`,
  and **HSTS** in production.
- The server’s exception handler returns generic messages and **never leaks
  internal details or stack traces** to clients.

### No secrets in the frontend
- Database URLs, the secret key, and admin credentials live only in `.env` /
  environment variables on the server. **Nothing secret is embedded in HTML,
  JavaScript, or the repository.** `.env` is git-ignored; only `.env.example`
  (with placeholders) is committed.

### Data safety
- Designs and categories support **soft delete** (deactivate) so nothing is lost
  by accident, and **categories with designs can’t be deleted** without first
  reassigning or deactivating — designs are never orphaned.

---

## Your go-live checklist

- [ ] **Change the admin credentials.** Set a real `ADMIN_EMAIL` and a strong
      `ADMIN_PASSWORD` in `.env`, then run `python backend/manage.py reset-admin`.
- [ ] **Set a strong, unique `SECRET_KEY`** (the setup script generates one; keep
      it secret and don’t reuse it elsewhere).
- [ ] **Set `ENV=production`** and serve the site over **HTTPS** (required for the
      secure login cookie). See [DEPLOYMENT.md](DEPLOYMENT.md).
- [ ] **Never commit your `.env`.** It’s already in `.gitignore`.
- [ ] **Back up** the database and the `storage/uploads/` folder.
- [ ] Consider lowering `MAX_UPLOAD_MB` and tightening
      `ALLOWED_IMAGE_EXTENSIONS` if you only need JPEG/PNG.
- [ ] Keep dependencies updated (`pip install -U -r backend/requirements.txt`) and re-run
      `python backend/manage.py test`.

---

## Reporting a concern

If you discover a security issue, avoid filing it publicly. Contact the site
owner/administrator directly so it can be addressed before disclosure.
