from pydantic import BaseModel, ConfigDict


class PublicItemImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sort_order: int
    is_primary: bool
    width: int | None = None
    height: int | None = None
    content_version: int
