"""
Integration tests for product catalogue endpoints.

Covers TS scenarios: TS-001-001, TS-001-002, TS-001-003, TS-001-004, TS-001-005,
TS-001-006, TS-001-007
"""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from tests.conftest import TENANT_ID


# ─── Helpers ────────────────────────────────────────────────────────────────


async def create_product_with_skus(
    name: str,
    skus: list[dict[str, Any]],
    tenant_id: uuid.UUID = TENANT_ID,
) -> uuid.UUID:
    """Insert a product + SKUs + stock_levels via the app's session factory."""
    from src.database import async_session_factory

    async with async_session_factory() as session:
        product_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO products (id, tenant_id, name, description, image_url, is_active, "
                "created_at, updated_at) "
                "VALUES (:id, :tenant_id, :name, NULL, NULL, true, now(), now())"
            ),
            {"id": str(product_id), "tenant_id": str(tenant_id), "name": name},
        )
        for sku in skus:
            sku_id = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO skus (id, product_id, tenant_id, label, price_minor, "
                    "is_active, created_at, updated_at) "
                    "VALUES (:id, :product_id, :tenant_id, :label, :price_minor, "
                    "true, now(), now())"
                ),
                {
                    "id": str(sku_id),
                    "product_id": str(product_id),
                    "tenant_id": str(tenant_id),
                    "label": sku["label"],
                    "price_minor": sku["price_minor"],
                },
            )
            await session.execute(
                text(
                    "INSERT INTO stock_levels (sku_id, total, reserved, updated_at) "
                    "VALUES (:sku_id, :total, :reserved, now())"
                ),
                {
                    "sku_id": str(sku_id),
                    "total": sku.get("stock_level", 0),
                    "reserved": sku.get("reserved", 0),
                },
            )
        await session.commit()
    return product_id


# ─── TS-001-001 ──────────────────────────────────────────────────────────────


async def test_ts_001_001_paginated_product_list_returns_products(
    client: AsyncClient,
) -> None:
    """
    TS-001-001: Paginated product list returns products with metadata.
    Preconditions: DB has 25 seeded products for test tenant, each with ≥1 SKU stock_level > 0
    Action: GET /api/v1/products?page=1&per_page=20 with header X-Tenant-ID
    Expected: HTTP 200; data has 20 products; meta.total=25, meta.page=1, meta.per_page=20
    """
    for i in range(25):
        await create_product_with_skus(
            name=f"Product {i:03d}",
            skus=[{"label": "Default", "price_minor": 1000, "stock_level": 10}],
        )

    response = await client.get(
        "/api/v1/products",
        params={"page": 1, "per_page": 20},
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert len(body["data"]) == 20
    assert body["meta"]["total"] == 25
    assert body["meta"]["page"] == 1
    assert body["meta"]["per_page"] == 20

    for product in body["data"]:
        assert "id" in product
        assert "name" in product
        assert "skus" in product
        assert "created_at" in product
        assert len(product["skus"]) > 0
        for sku in product["skus"]:
            assert "id" in sku
            assert "label" in sku
            assert "price_minor" in sku
            assert "stock_level" in sku


# ─── TS-001-002 ──────────────────────────────────────────────────────────────


async def test_ts_001_002_in_stock_filter_returns_only_products_with_available_stock(
    client: AsyncClient,
) -> None:
    """
    TS-001-002: In-stock filter returns only products with available stock.
    Preconditions: 5 products — 3 with ≥1 SKU stock_level>0, 2 with all SKUs stock_level=0
    """
    for i in range(3):
        await create_product_with_skus(
            name=f"InStock Product {i}",
            skus=[{"label": "Default", "price_minor": 500, "stock_level": 5}],
        )
    for i in range(2):
        await create_product_with_skus(
            name=f"OutOfStock Product {i}",
            skus=[{"label": "Default", "price_minor": 500, "stock_level": 0}],
        )

    response = await client.get(
        "/api/v1/products",
        params={"in_stock_only": "true"},
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 3
    for product in body["data"]:
        assert any(sku["stock_level"] > 0 for sku in product["skus"]), (
            f"Product {product['name']} has no SKU with stock_level > 0"
        )


# ─── TS-001-003 ──────────────────────────────────────────────────────────────


async def test_ts_001_003_pagination_second_page_returns_remaining_products(
    client: AsyncClient,
) -> None:
    """
    TS-001-003: Second page returns remaining products.
    """
    for i in range(25):
        await create_product_with_skus(
            name=f"Paged Product {i:03d}",
            skus=[{"label": "S", "price_minor": 800, "stock_level": 3}],
        )

    response = await client.get(
        "/api/v1/products",
        params={"page": 2, "per_page": 20},
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 5
    assert body["meta"]["page"] == 2
    assert body["meta"]["total"] == 25


# ─── TS-001-004 ──────────────────────────────────────────────────────────────


async def test_ts_001_004_product_detail_returns_product_with_all_sku_variants(
    client: AsyncClient,
) -> None:
    """
    TS-001-004: Product detail returns product with all SKU variants.
    """
    product_id = await create_product_with_skus(
        name="Classic T-Shirt",
        skus=[
            {"label": "Small", "price_minor": 1999, "stock_level": 5},
            {"label": "Medium", "price_minor": 1999, "stock_level": 10},
            {"label": "Large", "price_minor": 2199, "stock_level": 0},
        ],
    )
    from src.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(
            text("UPDATE products SET description = :desc WHERE id = :id"),
            {"desc": "A comfortable cotton tee", "id": str(product_id)},
        )
        await session.commit()

    response = await client.get(
        f"/api/v1/products/{product_id}",
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Classic T-Shirt"
    assert body["description"] == "A comfortable cotton tee"
    assert len(body["skus"]) == 3
    labels = {sku["label"] for sku in body["skus"]}
    assert labels == {"Small", "Medium", "Large"}
    for sku in body["skus"]:
        assert "id" in sku
        assert "label" in sku
        assert "price_minor" in sku
        assert "stock_level" in sku


# ─── TS-001-005 ──────────────────────────────────────────────────────────────


async def test_ts_001_005_product_detail_shows_variant_stock_levels_accurately(
    client: AsyncClient,
) -> None:
    """
    TS-001-005: Product detail shows variant stock levels accurately.
    """
    product_id = await create_product_with_skus(
        name="Stock Accuracy Product",
        skus=[
            {"label": "SKU-A", "price_minor": 1000, "stock_level": 10},
            {"label": "SKU-B", "price_minor": 1000, "stock_level": 0},
        ],
    )

    response = await client.get(
        f"/api/v1/products/{product_id}",
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    sku_map = {sku["label"]: sku for sku in body["skus"]}
    assert "SKU-A" in sku_map
    assert "SKU-B" in sku_map
    assert sku_map["SKU-A"]["stock_level"] == 10
    assert sku_map["SKU-B"]["stock_level"] == 0


# ─── TS-001-006 ──────────────────────────────────────────────────────────────


async def test_ts_001_006_empty_catalogue_returns_empty_data_array(
    client: AsyncClient,
) -> None:
    """
    TS-001-006: Empty catalogue returns empty data array.
    """
    response = await client.get(
        "/api/v1/products",
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


# ─── TS-001-007 ──────────────────────────────────────────────────────────────


async def test_ts_001_007_non_existent_product_returns_404(
    client: AsyncClient,
) -> None:
    """
    TS-001-007: Non-existent product returns 404.
    """
    non_existent_id = uuid.uuid4()

    response = await client.get(
        f"/api/v1/products/{non_existent_id}",
        headers={"x-tenant-id": str(TENANT_ID)},
    )

    assert response.status_code == 404
    body = response.json()
    detail = body.get("detail", body)
    assert "code" in detail or "PRODUCT_NOT_FOUND" in str(body)
    assert "message" in detail or "not found" in str(body).lower()
