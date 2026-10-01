"""
SQLAlchemy ORM models.

Tables
------
* users      — admin accounts (customers never have accounts)
* categories — nail-art categories (managed entirely from the admin panel)
* nail_arts  — individual nail-art designs
* audit_logs — lightweight record of admin actions (future-ready)

Design notes
------------
* Soft delete: records carry a ``status`` of ACTIVE / INACTIVE rather than
  being physically removed.  Inactive records never appear on the public site.
* Every design belongs to exactly one category (a real foreign key), and
  categories cannot be orphaned — deletion logic lives in the admin API.
* Indexes are added on the columns the catalog filters/sorts by: category_id,
  name, status and slug.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Status(str, enum.Enum):
    """Soft-delete / visibility status shared by categories and designs."""

    ACTIVE = "active"
    INACTIVE = "inactive"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.email}>"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[Status] = mapped_column(
        Enum(Status, values_callable=lambda e: [m.value for m in e]),
        default=Status.ACTIVE,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    nail_arts: Mapped[list["NailArt"]] = relationship(
        back_populates="category", cascade="save-update, merge"
    )

    @property
    def design_count(self) -> int:
        return len(self.nail_arts)

    @property
    def active_design_count(self) -> int:
        return sum(1 for n in self.nail_arts if n.status == Status.ACTIVE)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Category {self.name}>"


class NailArt(Base):
    __tablename__ = "nail_arts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # Relative path (under the upload dir) to the stored image, or None.
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_alt: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[Status] = mapped_column(
        Enum(Status, values_callable=lambda e: [m.value for m in e]),
        default=Status.ACTIVE,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    category: Mapped["Category"] = relationship(back_populates="nail_arts")
    photos: Mapped[list["NailArtPhoto"]] = relationship(
        cascade="all, delete-orphan", order_by="NailArtPhoto.id", lazy="selectin"
    )

    @property
    def image_paths(self) -> list[str]:
        return ([self.image_path] if self.image_path else []) + [p.image_path for p in self.photos]

    __table_args__ = (
        # Composite index that matches the most common catalog query:
        # "active designs in a category, newest first".
        Index("ix_nail_status_category", "status", "category_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<NailArt {self.name}>"


class NailArtPhoto(Base):
    __tablename__ = "nail_art_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nail_art_id: Mapped[int] = mapped_column(ForeignKey("nail_arts.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)


class AuditLog(Base):
    """Lightweight audit trail of admin actions (extensible, non-critical)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
