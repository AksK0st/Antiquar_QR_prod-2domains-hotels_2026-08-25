from __future__ import annotations

from fastapi import APIRouter, Request

from services.site import hotel_name_for_request


router = APIRouter(prefix="/site", tags=["public-site"])


@router.get("/")
async def get_site(request: Request):
    return {"hotel_name": hotel_name_for_request(request)}
