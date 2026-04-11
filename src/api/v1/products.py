import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from src.dependencies import SessionDep, TenantDep
from src.schemas.product import (
    CreateProductRequest,
    PaginationMeta,
    ProductPage,
    ProductSchema,
)
from src.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)


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
    try:
        return await service.create_product(tenant_id=tenant_id, request=body)
    except IntegrityError as exc:
        logger.warning("Product creation integrity error", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CONFLICT",
                "message": "Product with this name already exists for this tenant",
            },
        ) from exc
    except Exception as exc:
        logger.error("Product creation failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Invalid product data"},
        ) from exc


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
            detail={"code": "PRODUCT_NOT_FOUND", "message": f"Product {product_id!s} not found"},
        )
    return product
