"""add image content version for cache invalidation

Revision ID: 8f24a1d7c9e3
Revises: 6c8f4f1a2b70
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f24a1d7c9e3"
down_revision: Union[str, Sequence[str], None] = "6c8f4f1a2b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item_images",
        sa.Column("content_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_item_images_content_version_positive",
        "item_images",
        "content_version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_item_images_content_version_positive",
        "item_images",
        type_="check",
    )
    op.drop_column("item_images", "content_version")
