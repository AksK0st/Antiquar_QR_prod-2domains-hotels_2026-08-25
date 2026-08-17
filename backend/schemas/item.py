from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .item_image import PublicItemImageRead


SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
YEAR_MIN = -5000
YEAR_MAX = 3000
SORT_ORDER_MAX = 1_000_000


class _ItemTextNormalization(BaseModel):
    @field_validator(
        "slug",
        "name",
        "period_text",
        "country",
        "creator",
        "material",
        "location",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def strip_short_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator(
        "short_description",
        "description",
        "attribution_notes",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ItemBase(_ItemTextNormalization):
    slug: str = Field(min_length=1, max_length=150, pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=50_000)
    period_from: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    period_to: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    period_text: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    creator: str | None = Field(default=None, max_length=255)
    material: str | None = Field(default=None, max_length=255)
    attribution_notes: str | None = Field(default=None, max_length=20_000)
    sort_order: int = Field(default=0, ge=0, le=SORT_ORDER_MAX)
    is_active: bool = True
    collection_id: int | None = Field(default=None, ge=1)
    location: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_period(self):
        if (
            self.period_from is not None
            and self.period_to is not None
            and self.period_from > self.period_to
        ):
            raise ValueError("period_from must be less than or equal to period_to")
        return self


class ItemCreate(ItemBase):
    pass


class ItemUpdate(_ItemTextNormalization):
    slug: str | None = Field(default=None, min_length=1, max_length=150, pattern=SLUG_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=50_000)
    period_from: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    period_to: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    period_text: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    creator: str | None = Field(default=None, max_length=255)
    material: str | None = Field(default=None, max_length=255)
    attribution_notes: str | None = Field(default=None, max_length=20_000)
    sort_order: int | None = Field(default=None, ge=0, le=SORT_ORDER_MAX)
    is_active: bool | None = None
    collection_id: int | None = Field(default=None, ge=1)
    location: str | None = Field(default=None, max_length=255)
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self):
        for field_name in ("slug", "name", "sort_order", "is_active"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ItemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    slug: str
    name: str
    short_description: str | None
    period_text: str | None
    collection_id: int | None
    sort_order: int
    primary_image: PublicItemImageRead | None = None


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    images: list[PublicItemImageRead] = Field(default_factory=list)


class AdminItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
