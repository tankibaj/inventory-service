"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # products table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_products_tenant_name"),
    )
    op.create_index("idx_products_tenant_active", "products", ["tenant_id", "is_active"])

    # skus table
    op.create_table(
        "skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("price_minor", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("product_id", "label", name="uq_skus_product_label"),
        sa.CheckConstraint("price_minor >= 0", name="ck_skus_price_minor_non_negative"),
    )
    op.create_index("idx_skus_product", "skus", ["product_id"])

    # stock_levels table
    op.create_table(
        "stock_levels",
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skus.id"),
            primary_key=True,
        ),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reserved", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("total >= 0", name="ck_stock_levels_total_non_negative"),
        sa.CheckConstraint("reserved >= 0", name="ck_stock_levels_reserved_non_negative"),
        sa.CheckConstraint("reserved <= total", name="ck_stock_levels_reserved_lte_total"),
    )

    # stock_reservations table
    op.create_table(
        "stock_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "sku_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skus.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "converted",
                "expired",
                "released",
                name="stock_reservation_status",
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_stock_reservations_expires",
        "stock_reservations",
        ["expires_at"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("stock_reservations")
    op.execute("DROP TYPE IF EXISTS stock_reservation_status")
    op.drop_table("stock_levels")
    op.drop_table("skus")
    op.drop_table("products")
