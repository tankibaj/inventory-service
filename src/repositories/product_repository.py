import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.product import SKU, Product
from src.models.stock import StockLevel


@dataclass
class ProductPage:
    items: list[Product]
    total: int


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_products(
        self,
        tenant_id: uuid.UUID,
        page: int,
        per_page: int,
        in_stock_only: bool = False,
    ) -> ProductPage:
        base_query = (
            select(Product)
            .where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
            .options(selectinload(Product.skus).selectinload(SKU.stock_level))
        )

        if in_stock_only:
            # Only products that have at least one SKU with available stock
            in_stock_subquery = (
                select(SKU.product_id)
                .join(StockLevel, StockLevel.sku_id == SKU.id)
                .where(
                    SKU.tenant_id == tenant_id,
                    SKU.is_active.is_(True),
                    (StockLevel.total - StockLevel.reserved) > 0,
                )
                .distinct()
            )
            base_query = base_query.where(Product.id.in_(in_stock_subquery))

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * per_page
        items_query = base_query.order_by(Product.created_at.desc()).offset(offset).limit(per_page)
        items_result = await self._session.execute(items_query)
        items = list(items_result.scalars().unique().all())

        return ProductPage(items=items, total=total)

    async def get_by_id(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Product | None:
        query = (
            select(Product)
            .where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
            )
            .options(selectinload(Product.skus).selectinload(SKU.stock_level))
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create_product(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str | None,
        image_url: str | None,
        skus_data: list[dict[str, str | int]],
    ) -> Product:
        product = Product(
            tenant_id=tenant_id,
            name=name,
            description=description,
            image_url=image_url,
        )
        self._session.add(product)
        await self._session.flush()  # Get product ID

        for sku_data in skus_data:
            initial_stock = int(sku_data["initial_stock"])
            sku = SKU(
                product_id=product.id,
                tenant_id=tenant_id,
                label=str(sku_data["label"]),
                price_minor=int(sku_data["price_minor"]),
            )
            self._session.add(sku)
            await self._session.flush()  # Get SKU ID

            stock_level = StockLevel(
                sku_id=sku.id,
                total=initial_stock,
                reserved=0,
            )
            self._session.add(stock_level)

        await self._session.commit()
        await self._session.refresh(product)

        # Reload with relationships
        return await self.get_by_id(product.id, tenant_id)  # type: ignore[return-value]
