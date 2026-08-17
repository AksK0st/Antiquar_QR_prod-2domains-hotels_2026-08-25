import pytest
from pydantic import ValidationError

from schemas.collection import CollectionCreate, CollectionUpdate
from schemas.item import ItemCreate, ItemUpdate
from schemas.item_image import PublicItemImageRead


def test_item_slug_and_period_validation() -> None:
    with pytest.raises(ValidationError):
        ItemCreate(slug="Bad Slug", name="Item")
    with pytest.raises(ValidationError):
        ItemCreate(slug="item", name="Item", period_from=1900, period_to=1800)

    item = ItemCreate(slug="  valid-slug  ", name="  Name  ")
    assert item.slug == "valid-slug"
    assert item.name == "Name"


def test_patch_rejects_null_required_fields() -> None:
    with pytest.raises(ValidationError):
        ItemUpdate(expected_version=1, slug=None)
    with pytest.raises(ValidationError):
        CollectionUpdate(expected_version=1, name=None)


def test_public_image_schema_does_not_expose_internal_metadata() -> None:
    fields = set(PublicItemImageRead.model_fields)
    assert fields == {"id", "sort_order", "is_primary", "width", "height"}
    assert "object_name" not in fields
    assert "original_filename" not in fields


def test_collection_slug_is_normalized_and_strict() -> None:
    collection = CollectionCreate(slug="  first-floor  ", name=" Floor ")
    assert collection.slug == "first-floor"
    assert collection.name == "Floor"
    with pytest.raises(ValidationError):
        CollectionCreate(slug="first/floor", name="Floor")
