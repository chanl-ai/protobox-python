"""
Action Registry

Manages registration and discovery of actions.
"""


from loguru import logger


class ActionRegistry:
    """Registry for actions"""

    def __init__(self):
        self._actions: dict[str, dict] = {}

    def register_action(self, action_def: dict):
        """Register an action"""
        action_name = action_def.get("name")
        if action_name:
            self._actions[action_name] = action_def
            logger.info(f"Registered action: {action_name}")

    def get_action(self, action_name: str) -> dict:
        """Get action definition"""
        return self._actions.get(action_name, {})

    def list_actions(self) -> list[str]:
        """List all registered actions"""
        return list(self._actions.keys())
