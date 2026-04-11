from fastapi import APIRouter

from src.api.v1.products import router as products_router
from src.api.v1.stock import router as stock_router

router = APIRouter()
router.include_router(products_router)
router.include_router(stock_router)
