from fastapi import APIRouter

from .item import router as items_router
from .collection import router as collections_router
from .item_image import router as images_router
from .site import router as site_router


router = APIRouter(prefix="/public")

router.include_router(items_router)
router.include_router(collections_router)
router.include_router(images_router)
router.include_router(site_router)