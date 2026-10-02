# API Reference

The application exposes a JSON REST API. The **public** endpoints need no
authentication; the **admin** endpoints require an admin session cookie and, for
anything that changes data, a CSRF token.

Interactive, always-up-to-date docs are served at **`/api/docs`** (Swagger UI)
while the app is running.

Base URL in development: `http://localhost:8000`

---

## Conventions

- All request/response bodies are JSON, **except** creating/updating a nail art
  or category, which use `multipart/form-data` (because they can include an
  image upload).
- Prices are numbers; `price_display` is a pre-formatted string with your
  currency symbol.
- Timestamps are ISO-8601 strings.
- **Statuses** are `"active"` or `"inactive"`. Inactive items (and items in an
  inactive category) are hidden from all public endpoints.

### Error shape

Validation and conflict errors return a structured body:

```json
{ "detail": { "message": "Validation failed.", "errors": { "price": "Input should be greater than or equal to 0" } } }
```

Simple errors return `{ "detail": "Human-readable message." }`.

| Status | Meaning                                             |
|--------|-----------------------------------------------------|
| 401    | Not authenticated (no/invalid admin session)        |
| 403    | Missing/invalid CSRF token on a state-changing call |
| 404    | Not found                                           |
| 409    | Conflict (duplicate name; category still has designs)|
| 422    | Validation failed                                   |
| 429    | Too many login attempts (rate limited)              |

---

## Authentication

Sessions use a JWT stored in an **httpOnly** cookie (`access_token`), so it is
not readable by JavaScript. State-changing admin requests use the
**double-submit CSRF** pattern:

1. `POST /api/auth/login` returns a `csrf_token` (also set as a readable
   `csrf_token` cookie).
2. For every `POST`/`PUT`/`PATCH`/`DELETE` to the admin API, send that value in
   the `X-CSRF-Token` header. It must match the cookie.

### `POST /api/auth/login`
Body: `{ "email": "...", "password": "..." }`

```json
// 200 OK
{ "user": { "id": 1, "name": "Studio Admin", "email": "admin@…", "role": "admin" },
  "csrf_token": "…" }
```
`401` on bad credentials, `422` on a malformed email, `429` if rate-limited.

### `POST /api/auth/logout`
Clears the session and CSRF cookies. `200 OK`.

### `GET /api/auth/me`
`200` with `{ "user": {…} }` when logged in, otherwise `401`.

---

## Public catalogue API

### `GET /api/categories`
Active categories with design counts.
```json
{ "items": [ { "id": 1, "name": "Bridal", "slug": "bridal", "status": "active",
               "design_count": 3, "active_design_count": 3, … } ] }
```

### `GET /api/nail-arts`
Paginated, searchable, filterable listing of **active** designs.

Query parameters:

| Param       | Default  | Notes                                                        |
|-------------|----------|--------------------------------------------------------------|
| `search`    | –        | Case-insensitive, partial match on **name and description**. Multiple words all must match. |
| `category`  | –        | Category **slug** or numeric id. Omit or `all` for everything.|
| `sort`      | `newest` | `newest`, `oldest`, `price_asc`, `price_desc`, `name_asc`, `name_desc` |
| `page`      | `1`      | 1-based                                                      |
| `page_size` | `12`     | 1–60                                                         |

```json
{ "items": [ { "id": 1, "name": "Royal Pink Chrome", "slug": "royal-pink-chrome",
               "price": 799.0, "price_display": "₹799", "image_url": "/media/ab12.jpg",
               "image_alt": "…", "status": "active",
               "category": { "id": 3, "name": "Chrome", "slug": "chrome" } } ],
  "total": 16, "page": 1, "page_size": 12, "pages": 2,
  "has_next": true, "has_prev": false }
```

### `GET /api/nail-arts/{slug-or-id}`
A single active design plus related designs from the same category.
```json
{ "item": { … }, "related": [ { … } ] }
```
`404` if not found or not publicly visible.

---

## Admin API

All routes below are prefixed `/api/admin` and require an admin session.
Mutations also require the `X-CSRF-Token` header (see Authentication).

### `GET /api/admin/dashboard`
```json
{ "total_nail_arts": 16, "active_nail_arts": 16, "inactive_nail_arts": 0,
  "total_categories": 8, "active_categories": 8, "recent_nail_arts": [ … ] }
```

### Nail arts

| Method & path                                   | Purpose                                   |
|-------------------------------------------------|-------------------------------------------|
| `GET /api/admin/nail-arts`                      | List all (supports `search`,`category`,`status`,`sort`,`page`) |
| `GET /api/admin/nail-arts/{id}`                 | Fetch one                                 |
| `POST /api/admin/nail-arts`                     | Create (multipart)                        |
| `PUT /api/admin/nail-arts/{id}`                 | Update (multipart)                        |
| `PATCH /api/admin/nail-arts/{id}/status?status=active|inactive` | Activate / deactivate     |
| `DELETE /api/admin/nail-arts/{id}`              | Deactivate (soft delete)                  |
| `DELETE /api/admin/nail-arts/{id}?hard=true`    | Permanently delete (also removes image)   |

**Create/Update fields** (`multipart/form-data`): `name`, `description`,
`price`, `category_id`, `status` (default `active`), `image_alt` (optional),
`images` (optional repeated file field) adds multiple photos in selection order.
Responses include an ordered `images` array with `image_path`, `image_url`, and
`image_alt`; the existing singular image fields identify the cover photo.
Update appends photos and accepts repeated `remove_images` path fields to remove
individual photos belonging to that product. The first remaining photo becomes
the cover. Existing photos remain unless explicitly removed.
Update also accepts repeated `image_order` fields containing every retained
photo path exactly once; the first becomes the cover. `photo_edits` is a JSON
object keyed by retained photo path, with normalized `x`, `y`, `width`, `height`
crop coordinates and optional clockwise `rotation` (0, 90, 180, 270). Coordinates
refer to the rotated image. Crops create new files and replace the old files
only after a successful database save. Uploads append after the ordered photos.
The legacy `image` (optional file) field is still supported. Update also accepts `remove_image=true` to clear the
current photo. Uploaded files must be a real `.jpg/.jpeg/.png/.webp` within the
size limit, or you get a `422` with `errors.image`.

### Categories

| Method & path                                    | Purpose                                  |
|--------------------------------------------------|------------------------------------------|
| `GET /api/admin/categories`                      | List all                                 |
| `GET /api/admin/categories/{id}`                 | Fetch one                                |
| `POST /api/admin/categories`                     | Create (`name`, `description`, `status`) |
| `PUT /api/admin/categories/{id}`                 | Update                                   |
| `PATCH /api/admin/categories/{id}/status?status=…` | Activate / deactivate                  |
| `DELETE /api/admin/categories/{id}`              | Delete — **orphan-safe** (see below)     |

Duplicate names (case-insensitive) return `409` with `errors.name`.

#### Orphan-safe category deletion

- Category has **no designs** → deleted immediately (`200`).
- Category **has designs** and no `action` given → **`409`**:
  ```json
  { "detail": { "message": "This category contains 3 design(s).",
                "requires_action": true, "design_count": 3,
                "options": ["deactivate", "reassign"] } }
  ```
- `DELETE …?action=deactivate` → category hidden, designs kept (`200`).
- `DELETE …?action=reassign&target_category_id=<other>` → designs moved, then the
  empty category deleted (`200`). Requires a **different** target, else `422`.

---

## SEO & operational endpoints

| Path            | Purpose                                  |
|-----------------|------------------------------------------|
| `GET /robots.txt` | Allows crawling; disallows `/admin`     |
| `GET /sitemap.xml`| Lists all public pages + active designs |
| `GET /healthz`    | Liveness check → `{ "status": "ok" }`   |
