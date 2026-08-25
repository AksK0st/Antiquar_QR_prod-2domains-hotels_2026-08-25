from __future__ import annotations

from fastapi import APIRouter, Depends

from config import settings
from security.dependencies import get_current_admin


router = APIRouter(
    prefix="/sites",
    tags=["admin-sites"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/")
async def get_sites():
    return {
        "sites": [
            {
                "hotel_name": hotel_name,
                "base_url": settings.public_base_url_for_hotel(hotel_name),
            }
            for hotel_name in settings.hotel_names
        ]
    }
