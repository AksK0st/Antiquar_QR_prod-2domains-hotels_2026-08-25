from fastapi import APIRouter

from .items import router as items_router
from .collections import router as collections_router
from .auth import router as auth_router
from .images import router as images_router


router = APIRouter(prefix="/admin")

router.include_router(items_router)
router.include_router(collections_router)
router.include_router(auth_router)
router.include_router(images_router)