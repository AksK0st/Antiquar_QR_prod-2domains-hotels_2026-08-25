from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

if TYPE_CHECKING:
    from models.collection import Collection
    from models.item_image import ItemImage


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_hotel_slug", "hotel_name", "slug", unique=True),
        CheckConstraint("sort_order >= 0", name="ck_items_sort_order_nonnegative"),
        CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_items_period_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
        default=uuid4,
    )
    hotel_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Галерея", server_default="Галерея", index=True
    )
    slug: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_from: Mapped[int | None] = mapped_column(nullable=True)
    period_to: Mapped[int | None] = mapped_column(nullable=True)
    period_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
    )
    collection: Mapped["Collection | None"] = relationship(back_populates="items")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    images: Mapped[list["ItemImage"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    @property
    def primary_image(self) -> "ItemImage | None":
        if not self.images:
            return None
        return min(
            self.images,
            key=lambda image: (not image.is_primary, image.sort_order, image.id),
        )
