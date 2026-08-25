"""add hotel tenancy

Revision ID: f4a9c2d7e1b3
Revises: 8f24a1d7c9e3
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a9c2d7e1b3"
down_revision: Union[str, Sequence[str], None] = "8f24a1d7c9e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("hotel_name", sa.String(length=255), server_default="Галерея", nullable=False),
    )
    op.add_column(
        "items",
        sa.Column("hotel_name", sa.String(length=255), server_default="Галерея", nullable=False),
    )

    # Existing production data belongs to the first hotel.
    op.execute(sa.text("UPDATE collections SET hotel_name = 'Галерея'"))
    op.execute(sa.text("UPDATE items SET hotel_name = 'Галерея'"))

    op.drop_index("ix_collections_slug", table_name="collections")
    op.drop_index("ix_items_slug", table_name="items")

    op.create_index("ix_collections_slug", "collections", ["slug"], unique=False)
    op.create_index("ix_items_slug", "items", ["slug"], unique=False)
    op.create_index("ix_collections_hotel_name", "collections", ["hotel_name"], unique=False)
    op.create_index("ix_items_hotel_name", "items", ["hotel_name"], unique=False)
    op.create_index(
        "ix_collections_hotel_slug",
        "collections",
        ["hotel_name", "slug"],
        unique=True,
    )
    op.create_index(
        "ix_items_hotel_slug",
        "items",
        ["hotel_name", "slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_items_hotel_slug", table_name="items")
    op.drop_index("ix_collections_hotel_slug", table_name="collections")
    op.drop_index("ix_items_hotel_name", table_name="items")
    op.drop_index("ix_collections_hotel_name", table_name="collections")
    op.drop_index("ix_items_slug", table_name="items")
    op.drop_index("ix_collections_slug", table_name="collections")

    op.create_index("ix_items_slug", "items", ["slug"], unique=True)
    op.create_index("ix_collections_slug", "collections", ["slug"], unique=True)

    op.drop_column("items", "hotel_name")
    op.drop_column("collections", "hotel_name")
