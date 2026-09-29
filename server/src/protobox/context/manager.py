"""
Context Manager

Manages context state and persistence across tool executions.
"""

from loguru import logger

from ..tools.base import MCPContext


class ContextManager:
    """Manages execution context"""

    def __init__(self):
        self._contexts: dict[str, MCPContext] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the context manager"""
        logger.info("Initializing context manager")
        self._initialized = True

    async def cleanup(self):
        """Cleanup the context manager"""
        logger.info("Cleaning up context manager")
        self._contexts.clear()
        self._initialized = False

    async def get_context(self, session_id: str, tool_name: str) -> MCPContext:
        """Get or create context for a session/tool"""
        context_key = f"{session_id}:{tool_name}"

        if context_key not in self._contexts:
            self._contexts[context_key] = MCPContext(session_id=session_id, tool_name=tool_name)

        return self._contexts[context_key]

    async def update_context(self, context: MCPContext):
        """Update context state"""
        context_key = f"{context.session_id}:{context.tool_name}"
        self._contexts[context_key] = context

    async def clear_context(self, session_id: str, tool_name: str | None = None):
        """Clear context for a session or specific tool"""
        if tool_name:
            context_key = f"{session_id}:{tool_name}"
            if context_key in self._contexts:
                del self._contexts[context_key]
        else:
            # Clear all contexts for session
            keys_to_remove = [k for k in self._contexts if k.startswith(f"{session_id}:")]
            for key in keys_to_remove:
                del self._contexts[key]
