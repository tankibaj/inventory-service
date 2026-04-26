# Entity Schema: inventory-service

> Auto-generated from SQLAlchemy models on 2026-04-25 23:13 UTC. Do not edit manually.

---

## Table: `products`

| Column | Type | Nullable | PK | FK |
|---|---|---|---|---|
| `id` | `UUID` | NO | PK |  |
| `tenant_id` | `UUID` | NO |  |  |
| `name` | `VARCHAR(200)` | NO |  |  |
| `description` | `TEXT` | YES |  |  |
| `image_url` | `VARCHAR(500)` | YES |  |  |
| `is_active` | `BOOLEAN` | NO |  |  |
| `created_at` | `DATETIME` | NO |  |  |
| `updated_at` | `DATETIME` | NO |  |  |

**Constraints:**
- UNIQUE (`tenant_id`, `name`) (uq_products_tenant_name)

**Indexes:**
- `ix_products_tenant_id`: (`tenant_id`)

**Relationships:**
- `skus` → `skus` (one-to-many)

---

## Table: `skus`

| Column | Type | Nullable | PK | FK |
|---|---|---|---|---|
| `id` | `UUID` | NO | PK |  |
| `product_id` | `UUID` | NO |  | `products.id` |
| `tenant_id` | `UUID` | NO |  |  |
| `label` | `VARCHAR(200)` | NO |  |  |
| `price_minor` | `INTEGER` | NO |  |  |
| `is_active` | `BOOLEAN` | NO |  |  |
| `created_at` | `DATETIME` | NO |  |  |
| `updated_at` | `DATETIME` | NO |  |  |

**Constraints:**
- UNIQUE (`product_id`, `label`) (uq_skus_product_label)

**Indexes:**
- `ix_skus_product_id`: (`product_id`)

**Relationships:**
- `product` → `products` (many-to-one)
- `stock_level` → `stock_levels` (one-to-many)

---

## Table: `stock_levels`

| Column | Type | Nullable | PK | FK |
|---|---|---|---|---|
| `sku_id` | `UUID` | NO | PK | `skus.id` |
| `total` | `INTEGER` | NO |  |  |
| `reserved` | `INTEGER` | NO |  |  |
| `updated_at` | `DATETIME` | NO |  |  |

**Constraints:**
- CHECK `total >= 0` (ck_stock_levels_total_non_negative)
- CHECK `reserved >= 0` (ck_stock_levels_reserved_non_negative)
- CHECK `reserved <= total` (ck_stock_levels_reserved_lte_total)

**Relationships:**
- `sku` → `skus` (many-to-one)

---

## Table: `stock_reservations`

| Column | Type | Nullable | PK | FK |
|---|---|---|---|---|
| `id` | `UUID` | NO | PK |  |
| `order_id` | `UUID` | NO |  |  |
| `sku_id` | `UUID` | NO |  | `skus.id` |
| `quantity` | `INTEGER` | NO |  |  |
| `status` | `VARCHAR(9)` | NO |  |  |
| `expires_at` | `DATETIME` | NO |  |  |
| `created_at` | `DATETIME` | NO |  |  |

**Indexes:**
- `idx_stock_reservations_expires`: (`expires_at`)

---
