from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .item import SLUG_PATTERN


class _CollectionNormalization(BaseModel):
    @field_validator("hotel_name", "slug", "name", "location", mode="before", check_fields=False)
    @classmethod
    def strip_short_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("description", mode="before", check_fields=False)
    @classmethod
    def normalize_description(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class CollectionBase(_CollectionNormalization):
    hotel_name: str = Field(default="Галерея", min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=150, pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    location: str | None = Field(default=None, max_length=255)


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(_CollectionNormalization):
    hotel_name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=150, pattern=SLUG_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    location: str | None = Field(default=None, max_length=255)
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self):
        for field_name in ("hotel_name", "slug", "name"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PublicCollectionRead(CollectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CollectionRead(CollectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime
