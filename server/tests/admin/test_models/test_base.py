"""Unit tests for base models."""

from datetime import datetime

import pytest
from bson import ObjectId
from pydantic import ValidationError

from protobox.admin.models.base import MongoBaseModel, validate_object_id


class TestValidateObjectId:
    """Test ObjectId validation function."""

    def test_validate_object_id_with_valid_objectid(self):
        """Test validation with a valid ObjectId instance."""
        oid = ObjectId()
        result = validate_object_id(oid)
        assert result == oid

    def test_validate_object_id_with_valid_string(self):
        """Test validation with a valid ObjectId string."""
        oid_str = "507f1f77bcf86cd799439011"
        result = validate_object_id(oid_str)
        assert result == oid_str

    def test_validate_object_id_with_invalid_string(self):
        """Test validation with an invalid ObjectId string."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            validate_object_id("invalid_id")

    def test_validate_object_id_with_invalid_type(self):
        """Test validation with an invalid type."""
        with pytest.raises(ValueError, match="ObjectId must be ObjectId instance or string"):
            validate_object_id(123)


class TestMongoBaseModel:
    """Test MongoBaseModel functionality."""

    def test_model_creation_without_id(self):
        """Test creating a model without specifying an ID."""
        model = MongoBaseModel()
        assert model.id is None
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_model_creation_with_objectid(self):
        """Test creating a model with an ObjectId."""
        oid = ObjectId()
        model = MongoBaseModel(id=oid)
        assert model.id == oid  # ObjectId is preserved as-is
        assert isinstance(model.created_at, datetime)

    def test_model_creation_with_string_id(self):
        """Test creating a model with a string ID."""
        oid_str = "507f1f77bcf86cd799439011"
        model = MongoBaseModel(id=oid_str)
        assert model.id == oid_str

    def test_model_creation_with_alias(self):
        """Test creating a model using the _id alias."""
        oid_str = "507f1f77bcf86cd799439011"
        model = MongoBaseModel(_id=oid_str)
        assert model.id == oid_str

    def test_model_with_invalid_id(self):
        """Test that invalid IDs raise validation errors."""
        with pytest.raises(ValidationError):
            MongoBaseModel(id="invalid_id")

    def test_model_dump_json_mode(self):
        """Test model_dump with JSON mode."""
        oid = ObjectId()
        model = MongoBaseModel(id=oid)
        data = model.model_dump(mode="json")

        assert "_id" in data
        assert data["_id"] == str(oid)
        assert data["id"] == str(oid)
        assert isinstance(data["created_at"], str)  # Should be ISO format string
        assert isinstance(data["updated_at"], str)

    def test_model_dump_python_mode(self):
        """Test model_dump with Python mode."""
        oid = ObjectId()
        model = MongoBaseModel(id=oid)
        data = model.model_dump(mode="python")

        # In Python mode, dates should still be datetime objects
        assert isinstance(data["created_at"], datetime)
        assert isinstance(data["updated_at"], datetime)

    def test_dict_method_compatibility(self):
        """Test the dict method for backward compatibility."""
        oid = ObjectId()
        model = MongoBaseModel(id=oid)
        data = model.dict()

        assert "_id" in data
        assert data["_id"] == str(oid)
        assert data["id"] == oid  # ObjectId is preserved in dict

    def test_model_serialization_to_json(self):
        """Test that the model can be serialized to JSON."""
        import json

        oid = ObjectId()
        model = MongoBaseModel(id=oid)

        # This should not raise an error
        json_str = json.dumps(model.model_dump(mode="json"))
        assert str(oid) in json_str

    def test_model_field_validation(self):
        """Test that field validation works properly."""
        model = MongoBaseModel()

        # Test that we can update fields
        model.updated_at = datetime.now()
        assert isinstance(model.updated_at, datetime)

    def test_model_strip_whitespace(self):
        """Test that string fields have whitespace stripped."""

        # Create a subclass to test string field stripping
        class TestModel(MongoBaseModel):
            name: str

        model = TestModel(name="  test name  ")
        assert model.name == "test name"
