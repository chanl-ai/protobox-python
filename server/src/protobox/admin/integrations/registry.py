"""Integration registry for managing all available integrations."""

from typing import TYPE_CHECKING, Optional, Type

from loguru import logger

from ..models.integration import IntegrationType

if TYPE_CHECKING:
    from ..integrations.base_classes import BaseIntegration


class IntegrationRegistry:
    """Registry for managing all available integration types."""
    
    def __init__(self):
        self._integrations: dict[IntegrationType, Type["BaseIntegration"]] = {}
        self._instances: dict[IntegrationType, "BaseIntegration"] = {}
    
    def register(self, integration_class: Type["BaseIntegration"]) -> None:
        """
        Register an integration class.
        
        Args:
            integration_class: The integration class to register
        """
        instance = integration_class()
        integration_type = instance.integration_type
        
        if integration_type in self._integrations:
            logger.warning(
                f"Integration {integration_type} already registered, overwriting"
            )
        
        self._integrations[integration_type] = integration_class
        self._instances[integration_type] = instance
        
        logger.info(f"Registered integration: {integration_type}")
    
    def get(self, integration_type: IntegrationType) -> Optional["BaseIntegration"]:
        """
        Get an integration instance by type.
        
        Args:
            integration_type: The type of integration to retrieve
            
        Returns:
            The integration instance if found, None otherwise
        """
        return self._instances.get(integration_type)
    
    def get_class(
        self, integration_type: IntegrationType
    ) -> Optional[Type["BaseIntegration"]]:
        """
        Get an integration class by type.
        
        Args:
            integration_type: The type of integration to retrieve
            
        Returns:
            The integration class if found, None otherwise
        """
        return self._integrations.get(integration_type)
    
    def list_all(self) -> list[IntegrationType]:
        """
        List all registered integration types.
        
        Returns:
            List of registered integration types
        """
        return list(self._integrations.keys())
    
    def list_instances(self) -> list["BaseIntegration"]:
        """
        List all integration instances.
        
        Returns:
            List of integration instances
        """
        return list(self._instances.values())
    
    def is_registered(self, integration_type: IntegrationType) -> bool:
        """
        Check if an integration type is registered.
        
        Args:
            integration_type: The type to check
            
        Returns:
            True if registered, False otherwise
        """
        return integration_type in self._integrations
    
    def clear(self) -> None:
        """Clear all registered integrations."""
        self._integrations.clear()
        self._instances.clear()


# Global registry instance
integration_registry = IntegrationRegistry()


def get_integration_registry() -> IntegrationRegistry:
    """Get the global integration registry instance."""
    return integration_registry