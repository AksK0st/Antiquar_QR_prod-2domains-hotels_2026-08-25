from fastapi import APIRouter

from routes.public import router as public_router
from routes.admin import router as admin_router


router = APIRouter(prefix="/api")

router.include_router(public_router)
router.include_router(admin_router)