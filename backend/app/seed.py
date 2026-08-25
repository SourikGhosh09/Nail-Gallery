"""
Database seeding.

Run automatically by the setup script (and available via ``python manage.py
seed``).  It:

1. Creates all tables.
2. Creates the first admin account from ``ADMIN_EMAIL`` / ``ADMIN_PASSWORD``
   in ``.env`` — but only if no admin exists yet.
3. Populates a tasteful demo catalogue (categories + designs with generated
   placeholder images) — but only if the catalogue is currently empty, so it
   never overwrites your real data.

Everything is idempotent: running it repeatedly is safe.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Category, NailArt, Status, User
from app.security import hash_password
from app.utils import slugify, unique_slug

# --- Demo content ----------------------------------------------------------
_CATEGORIES = [
    ("Bridal", "Timeless, elegant designs for your most special day."),
    ("French", "Classic and reinvented French tips with a modern touch."),
    ("Chrome", "High-shine mirror and metallic chrome finishes."),
    ("Party", "Bold, glamorous looks that love the spotlight."),
    ("Minimal", "Understated, refined art for the quietly confident."),
    ("3D", "Sculpted, textured and embellished statement nails."),
    ("Gel", "Long-lasting, glossy gel designs in every shade."),
    ("Custom", "Bespoke designs created just for you."),
]

# (name, category, price, description)
_DESIGNS = [
    ("Royal Pink Chrome", "Chrome", 799,
     "Elegant pink chrome nail design with a premium glossy mirror finish."),
    ("Soft Pink Bridal", "Bridal", 1299,
     "Delicate blush tones with subtle pearl accents — made for the aisle."),
    ("Pink French Elegance", "French", 899,
     "A romantic take on the French tip with a soft pink smile line."),
    ("Rose Gold Glitter", "Party", 999,
     "Sparkling rose-gold glitter ombré that catches every light."),
    ("Ivory Lace Bridal", "Bridal", 1499,
     "Hand-painted ivory lace detailing with delicate crystal work."),
    ("Classic White French", "French", 749,
     "The timeless white-tip French manicure, flawlessly clean."),
    ("Midnight Chrome", "Chrome", 849,
     "Deep graphite chrome with a liquid-metal mirror shine."),
    ("Champagne Shimmer", "Party", 899,
     "Warm champagne shimmer for effortless everyday glamour."),
    ("Nude Minimalist", "Minimal", 599,
     "A barely-there nude with a single fine gold line. Quiet luxury."),
    ("Matte Mocha", "Minimal", 649,
     "Sophisticated matte mocha for a modern, understated look."),
    ("Crystal Bloom 3D", "3D", 1699,
     "Sculpted 3D floral accents finished with hand-set crystals."),
    ("Velvet Rouge Gel", "Gel", 799,
     "Rich rouge gel polish with a deep, glassy, long-lasting shine."),
    ("Pearl Drop Gel", "Gel", 849,
     "Milky pearl gel with an iridescent drop-of-light finish."),
    ("Golden Hour", "Party", 1099,
     "Molten gold foil streaks over a warm bronze base."),
    ("Blush Ombré", "Minimal", 699,
     "A whisper-soft blush-to-clear ombré for natural elegance."),
    ("Bespoke Bridal Set", "Custom", 1999,
     "A fully custom bridal set designed around your dress and theme."),
]


def _generate_placeholder(index: int, filename: str) -> None:
    """Create an elegant two-tone gradient placeholder image."""
    from PIL import Image, ImageDraw

    palettes = [
        ((247, 231, 226), (183, 110, 121)),  # blush -> rose gold
        ((245, 238, 224), (198, 161, 91)),   # cream -> gold
        ((238, 226, 232), (150, 120, 140)),  # mauve
        ((235, 224, 219), (120, 90, 95)),    # deep rose
        ((243, 240, 245), (170, 150, 190)),  # lilac
        ((250, 244, 238), (205, 175, 150)),  # nude
    ]
    top, bottom = palettes[index % len(palettes)]
    size = 1000
    img = Image.new("RGB", (size, size), top)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    # Soft diagonal sheen.
    sheen = Image.new("RGB", (size, size), (255, 255, 255))
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, size), (size, size * 2 // 3), (size, size), (0, size)], fill=28)
    img = Image.composite(sheen, img, mask)
    img.save(settings.upload_path / filename, format="JPEG", quality=85, optimize=True)


def seed(db: Session) -> None:
    init_db()

    # 1) Ensure an admin exists.
    admin = db.scalar(select(User).where(User.role == "admin"))
    if admin is None:
        admin = User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL.lower().strip(),
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"  [OK] Created admin account: {admin.email}")
    else:
        print(f"  - Admin already exists: {admin.email}")

    # 2) Seed demo catalogue only if empty.
    existing = db.scalar(select(func.count()).select_from(Category))
    if existing:
        print(f"  - Catalogue already has {existing} categories - skipping demo data.")
        return

    cats: dict[str, Category] = {}
    for name, desc in _CATEGORIES:
        c = Category(name=name, slug=slugify(name), description=desc, status=Status.ACTIVE)
        db.add(c)
        cats[name] = c
    db.commit()

    used_slugs: set[str] = set()

    def _exists(slug: str) -> bool:
        return slug in used_slugs

    for i, (name, cat_name, price, desc) in enumerate(_DESIGNS):
        filename = f"seed_{i:02d}.jpg"
        _generate_placeholder(i, filename)
        slug = unique_slug(name, _exists)
        used_slugs.add(slug)
        db.add(
            NailArt(
                name=name,
                slug=slug,
                description=desc,
                price=price,
                category_id=cats[cat_name].id,
                image_path=filename,
                image_alt=f"{name} nail art design",
                status=Status.ACTIVE,
            )
        )
    db.commit()
    print(f"  [OK] Seeded {len(_CATEGORIES)} categories and {len(_DESIGNS)} designs.")


def main() -> None:
    print("Seeding database...")
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    print("Done.")


if __name__ == "__main__":
    main()
