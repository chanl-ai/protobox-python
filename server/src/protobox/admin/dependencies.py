"""Shared dependencies for admin routers."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .database.connection import DatabaseConnection, get_database_connection
from .secrets.encryption import SecretEncryption
from .services.action_service import ActionService
from .services.assistant_service import AssistantService
from .services.chat_service import ChatService
from .services.prompt_service import PromptService
# from .services.resource_service import ResourceService  # TODO: Add when migrating resources feature
from .services.secret_service import SecretService


def get_database() -> DatabaseConnection:
    """Get database connection dependency."""
    return get_database_connection()


def get_action_service(db: DatabaseConnection = Depends(get_database)) -> ActionService:
    """Get action service instance."""
    return ActionService()


def get_secret_service(db: DatabaseConnection = Depends(get_database)) -> SecretService:
    """Get secret service instance."""
    encryption = SecretEncryption()
    return SecretService(encryption)


def get_chat_service(db: DatabaseConnection = Depends(get_database)) -> ChatService:
    """Get chat service instance."""
    return ChatService()


@lru_cache(maxsize=1)
def get_assistant_service_singleton() -> AssistantService:
    """Get a singleton assistant service instance to avoid multiple instantiations."""
    action_service = ActionService()
    encryption = SecretEncryption()
    secret_service = SecretService(encryption)
    return AssistantService(action_service, secret_service)


def get_assistant_service(
    db: DatabaseConnection = Depends(get_database)
) -> AssistantService:
    """Get assistant service instance (singleton)."""
    return get_assistant_service_singleton()


def get_prompt_service(db: DatabaseConnection = Depends(get_database)) -> PromptService:
    """Get prompt service instance."""
    return PromptService()


# def get_resource_service(db: DatabaseConnection = Depends(get_database)) -> ResourceService:
#     """Get resource service instance."""
#     return ResourceService()


# Type aliases for cleaner dependency injection
DatabaseDep = Annotated[DatabaseConnection, Depends(get_database)]
ActionServiceDep = Annotated[ActionService, Depends(get_action_service)]
SecretServiceDep = Annotated[SecretService, Depends(get_secret_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]
PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
# ResourceServiceDep = Annotated[ResourceService, Depends(get_resource_service)]  # TODO: Add when migrating resources
