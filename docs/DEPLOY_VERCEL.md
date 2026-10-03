# Move Nail Gallery from Render to Vercel

The app runs as a FastAPI Vercel Function from the repository root (`index.py`).
Use a managed PostgreSQL database and a **private** Vercel Blob store. Local
SQLite and local uploads are rejected when `VERCEL=1` because they cannot persist
across instances and redeployments. Render stays available until verification.

## Back up before changing Render

Do not restart or redeploy a free Render service before taking this backup.
Pause catalog edits while exporting and during the final switch.

```powershell
python backend/migrate_catalog.py backup ../render-catalog-backup.zip
```

Enter the existing admin email and password at the prompts. The archive contains
all active and inactive categories/products, ordered photos, alt text, timestamps,
and photo checksums. It does not contain login passwords, users, or audit logs.
Keep the archive outside Git. If admin verification confirms every record is
public, `--public-counts PRODUCTS CATEGORIES` permits a backup without credentials
and requires the returned counts to match the verified totals.

## Configure Vercel

Create a FastAPI project with the repository root as its root directory. Connect
an empty Neon PostgreSQL database using Vercel Marketplace's free plan, and attach
a private Blob store. Keep preview data separate from production before ongoing
development; attaching one store/database to both environments shares data.

Set the following environment variables through Vercel's dashboard:

| Variable | Value |
| --- | --- |
| `ENV` | `production` |
| `DATABASE_URL` | Neon PostgreSQL connection string, with SSL required |
| `STORAGE_BACKEND` | `vercel_blob` |
| `BLOB_READ_WRITE_TOKEN` | Added by the connected private Blob store |
| `SKIP_DB_INIT` | `true` |
| `SECRET_KEY` | A new long random secret |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Initial admin credentials |
| `BASE_URL` | Final Vercel/custom domain URL |
| `MAX_UPLOAD_MB` | `3` |

Copy studio branding, WhatsApp/contact details, currency, and social URLs from
the old environment. Existing accounts are not exported by the catalog API, so
the importer creates the initial admin using the destination configuration.

## Restore and verify

Load destination environment variables into your shell securely (never commit
or print their values), then run:

```powershell
python backend/migrate_catalog.py restore ../render-catalog-backup.zip
```

The destination catalog must be empty. The importer checks photo hashes, uploads
all images, preserves IDs/order/visibility, updates PostgreSQL ID sequences,
and commits the catalog together. On failure it rolls back records and removes
newly uploaded files. Keep the dedicated destination Blob store empty until
restoring. Run the importer once, outside a Vercel request/build: runtime startup
does not create tables or insert demo products.

Deploy the migration branch as a preview. Verify counts, each photo, category
filters, admin login, creation, photo append/removal, crop/rotation, ordering,
cover selection, and that hidden photos require admin login. Promote the verified
deployment to production and update `BASE_URL` to its final URL. Keep the old
Render service and backup for rollback until the new deployment is confirmed.

Vercel limits multipart request bodies to 4.5 MB. The admin form checks a 4 MB
total photo/form budget; save additional photos in subsequent batches. Original
image validation, optimization, and cropping run on the server. Images are stored
privately and served from `/media/` so browser crop previews remain same-origin.

Official documentation:
- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/vercel-blob/server-upload
- https://vercel.com/docs/storage
