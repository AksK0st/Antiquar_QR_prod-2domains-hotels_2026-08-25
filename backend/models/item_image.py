from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

if TYPE_CHECKING:
    from models.item import Item


class ItemImage(Base):
    __tablename__ = "item_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="ck_item_images_sort_order_nonnegative"),
        CheckConstraint("size IS NULL OR size >= 0", name="ck_item_images_size_nonnegative"),
        CheckConstraint("width IS NULL OR width > 0", name="ck_item_images_width_positive"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_item_images_height_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    item: Mapped["Item"] = relationship(back_populates="images")


Index(
    "uq_item_one_primary_image",
    ItemImage.item_id,
    unique=True,
    postgresql_where=ItemImage.is_primary.is_(True),
)
