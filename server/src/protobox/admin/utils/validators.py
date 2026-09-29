"""Utility functions for request validation."""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def validate_workspace_id(workspace_id: str) -> str:
    """
    Validate workspace ID format.
    
    Args:
        workspace_id: The workspace ID to validate
        
    Returns:
        The validated workspace ID as string
        
    Raises:
        HTTPException: If workspace ID format is invalid
    """
    try:
        # Check if it's a valid ObjectId format
        ObjectId(workspace_id)
        return workspace_id
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace ID format: {workspace_id}. Must be a valid MongoDB ObjectId."
        )


def validate_object_id(object_id: str, field_name: str = "ID") -> str:
    """
    Validate ObjectId format.
    
    Args:
        object_id: The ObjectId string to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated ObjectId as string
        
    Raises:
        HTTPException: If ObjectId format is invalid
    """
    try:
        ObjectId(object_id)
        return object_id
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format: {object_id}. Must be a valid MongoDB ObjectId."
        )


def validate_optional_object_id(object_id: str | None, field_name: str = "ID") -> str | None:
    """
    Validate optional ObjectId format.
    
    Args:
        object_id: The ObjectId string to validate (can be None)
        field_name: Name of the field for error messages
        
    Returns:
        The validated ObjectId as string, or None
        
    Raises:
        HTTPException: If ObjectId format is invalid
    """
    if object_id is None:
        return None
    return validate_object_id(object_id, field_name)
