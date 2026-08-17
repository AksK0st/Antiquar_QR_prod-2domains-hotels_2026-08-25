from pydantic import BaseModel, ConfigDict, Field


class AdminItemImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    original_filename: str | None
    content_type: str | None
    size: int | None
    width: int | None
    height: int | None
    sort_order: int
    is_primary: bool


class AdminItemImageOrderRequest(BaseModel):
    image_ids: list[int] = Field(max_length=100)
