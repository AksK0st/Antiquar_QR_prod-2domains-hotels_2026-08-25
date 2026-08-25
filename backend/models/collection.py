from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

if TYPE_CHECKING:
    from models.item import Item


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (
        Index("ix_collections_hotel_slug", "hotel_name", "slug", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Галерея", server_default="Галерея", index=True
    )
    slug: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["Item"]] = relationship(back_populates="collection")
