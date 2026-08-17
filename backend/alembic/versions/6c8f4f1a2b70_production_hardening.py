"""production hardening

Revision ID: 6c8f4f1a2b70
Revises: 2f3be0f4339a
Create Date: 2026-08-17
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "6c8f4f1a2b70"
down_revision: Union[str, Sequence[str], None] = "2f3be0f4339a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("public_id", sa.Uuid(), nullable=True))
    op.add_column("items", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column(
        "items",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "items",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    connection = op.get_bind()
    item_ids = connection.execute(sa.text("SELECT id FROM items WHERE public_id IS NULL")).scalars().all()
    for item_id in item_ids:
        connection.execute(
            sa.text("UPDATE items SET public_id = :public_id WHERE id = :item_id"),
            {"public_id": uuid4(), "item_id": item_id},
        )

    op.alter_column("items", "public_id", nullable=False)
    op.create_index("ix_items_public_id", "items", ["public_id"], unique=True)
    op.create_check_constraint("ck_items_sort_order_nonnegative", "items", "sort_order >= 0")
    op.create_check_constraint(
        "ck_items_period_order",
        "items",
        "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
    )

    op.add_column("collections", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column(
        "collections",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "collections",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.add_column("item_images", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("item_images", sa.Column("height", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_item_images_sort_order_nonnegative", "item_images", "sort_order >= 0"
    )
    op.create_check_constraint(
        "ck_item_images_size_nonnegative", "item_images", "size IS NULL OR size >= 0"
    )
    op.create_check_constraint(
        "ck_item_images_width_positive", "item_images", "width IS NULL OR width > 0"
    )
    op.create_check_constraint(
        "ck_item_images_height_positive", "item_images", "height IS NULL OR height > 0"
    )

    # Preserve exactly one existing primary per item before creating the partial unique index.
    connection.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY item_id
                           ORDER BY sort_order, id
                       ) AS rn
                FROM item_images
                WHERE is_primary = true
            )
            UPDATE item_images
            SET is_primary = false
            WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
            """
        )
    )
    op.create_index(
        "uq_item_one_primary_image",
        "item_images",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )

    op.create_table(
        "storage_cleanup_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("object_name", sa.String(length=500), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_name"),
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"], unique=False)
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"], unique=False)
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_table("storage_cleanup_jobs")

    op.drop_index("uq_item_one_primary_image", table_name="item_images")
    op.drop_constraint("ck_item_images_height_positive", "item_images", type_="check")
    op.drop_constraint("ck_item_images_width_positive", "item_images", type_="check")
    op.drop_constraint("ck_item_images_size_nonnegative", "item_images", type_="check")
    op.drop_constraint("ck_item_images_sort_order_nonnegative", "item_images", type_="check")
    op.drop_column("item_images", "height")
    op.drop_column("item_images", "width")

    op.drop_column("collections", "updated_at")
    op.drop_column("collections", "created_at")
    op.drop_column("collections", "version")

    op.drop_constraint("ck_items_period_order", "items", type_="check")
    op.drop_constraint("ck_items_sort_order_nonnegative", "items", type_="check")
    op.drop_index("ix_items_public_id", table_name="items")
    op.drop_column("items", "updated_at")
    op.drop_column("items", "created_at")
    op.drop_column("items", "version")
    op.drop_column("items", "public_id")
