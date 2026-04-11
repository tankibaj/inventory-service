import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.dependencies import SessionDep, TenantDep
from src.schemas.product import (
    CreateProductRequest,
    PaginationMeta,
    ProductPage,
    ProductSchema,
)
from src.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductPage)
async def list_products(
    tenant_id: TenantDep,
    session: SessionDep,
    in_stock_only: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductPage:
    service = ProductService(session)
    products, total = await service.list_products(
        tenant_id=tenant_id,
        page=page,
        per_page=per_page,
        in_stock_only=in_stock_only,
    )
    return ProductPage(
        data=products,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.post("", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    tenant_id: TenantDep,
    session: SessionDep,
    body: CreateProductRequest,
) -> ProductSchema:
    service = ProductService(session)
    return await service.create_product(tenant_id=tenant_id, request=body)


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(
    product_id: uuid.UUID,
    tenant_id: TenantDep,
    session: SessionDep,
) -> ProductSchema:
    service = ProductService(session)
    product = await service.get_product(product_id=product_id, tenant_id=tenant_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
        )
    return product
