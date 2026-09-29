"""Base models for MongoDB integration with proper ObjectId handling."""

from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import AfterValidator
from pydantic.json_schema import WithJsonSchema


def validate_object_id(v: Any) -> ObjectId | str:
    """Validate and convert to ObjectId or keep as string."""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return v  # Keep as string, let serializer handle it
        raise ValueError(f"Invalid ObjectId: {v}")
    raise ValueError("ObjectId must be ObjectId instance or string")


# Custom ObjectId type for Pydantic v2 - Best Practice
PyObjectId = Annotated[
    ObjectId | str,
    PlainSerializer(
        lambda x: str(x) if isinstance(x, ObjectId) else x, return_type=str, when_used="json"
    ),
    AfterValidator(validate_object_id),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents with proper ObjectId handling and audit fields."""

    id: PyObjectId | None = Field(
        None, 
        validation_alias="_id",
        serialization_alias="id"
    )
    
    # Audit fields - to be set by service layer
    # Made optional for backward compatibility with existing database records
    created_by: Optional[str] = Field(None, description="User ID who created this record")
    updated_by: Optional[str] = Field(None, description="User ID who last updated this record")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, datetime: lambda v: v.isoformat() if v else None},
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, value: ObjectId | str | None) -> str | None:
        """Ensure ID is always serialized as string."""
        if value is None:
            return None
        return str(value)

    def dict(self, **kwargs) -> dict:
        """Override dict to ensure proper serialization."""
        data = super().model_dump(**kwargs)
        # Remove _id from JSON output as 'id' field handles it via alias
        if "_id" in data:
            del data["_id"]
        return data

    def model_dump(self, **kwargs) -> dict:
        """Pydantic v2 compatible dump with proper serialization."""
        # Force JSON mode and by_alias for proper serialization
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        if "by_alias" not in kwargs:
            kwargs["by_alias"] = True
        return super().model_dump(**kwargs)

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(exclude_none=True, mode="python")
        # Convert id to _id for MongoDB
        if "id" in data:
            if data["id"] is not None:
                data["_id"] = data["id"] if isinstance(data["id"], ObjectId) else ObjectId(data["id"])
            del data["id"]
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "MongoBaseModel":
        """Create model from MongoDB document."""
        # Pydantic will use validation_alias to map _id to id automatically
        return cls(**data)
    
    @property
    def id_str(self) -> str | None:
        """Get ID as string - safe for JSON serialization."""
        if self.id is None:
            return None
        return str(self.id)
