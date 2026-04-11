import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.product_repository import ProductPage, ProductRepository
from src.schemas.product import CreateProductRequest, ProductSchema


def _sku_stock_level(sku: object) -> int:
    """Extract stock_level (available) from SKU ORM object."""
    stock = getattr(sku, "stock_level", None)
    if stock is None:
        return 0
    return stock.available


def product_to_schema(product: object) -> ProductSchema:
    from src.models.product import Product as ProductModel

    assert isinstance(product, ProductModel)
    return ProductSchema(
        id=product.id,
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        created_at=product.created_at,
        skus=[
            {
                "id": sku.id,
                "label": sku.label,
                "price_minor": sku.price_minor,
                "stock_level": _sku_stock_level(sku),
            }
            for sku in product.skus
            if sku.is_active
        ],
    )


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ProductRepository(session)

    async def list_products(
        self,
        tenant_id: uuid.UUID,
        page: int,
        per_page: int,
        in_stock_only: bool = False,
    ) -> tuple[list[ProductSchema], int]:
        page_result = await self._repo.list_products(
            tenant_id=tenant_id,
            page=page,
            per_page=per_page,
            in_stock_only=in_stock_only,
        )
        schemas = [product_to_schema(p) for p in page_result.items]
        return schemas, page_result.total

    async def get_product(
        self,
        product_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ProductSchema | None:
        product = await self._repo.get_by_id(product_id, tenant_id)
        if product is None:
            return None
        return product_to_schema(product)

    async def create_product(
        self,
        tenant_id: uuid.UUID,
        request: CreateProductRequest,
    ) -> ProductSchema:
        skus_data: list[dict[str, object]] = [
            {
                "label": sku.label,
                "price_minor": sku.price_minor,
                "initial_stock": sku.initial_stock,
            }
            for sku in request.skus
        ]
        product = await self._repo.create_product(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            image_url=request.image_url,
            skus_data=skus_data,
        )
        return product_to_schema(product)
