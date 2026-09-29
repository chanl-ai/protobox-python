"""Execution service for managing action executions."""
from datetime import datetime

from ..actions.rest_executor import RestActionExecutor
from ..database.repositories.execution_repository import ExecutionRepository
from ..models.execution import (
    ExecutionCreateRequest,
    ExecutionModel,
    ExecutionStatus,
    ExecutionSummary,
    ExecutionUpdateRequest,
)
from ..secrets.encryption import SecretEncryption
from ..services.action_service import ActionService
from ..services.secret_service import SecretService


class ExecutionService:
    """Service for managing action executions."""

    def __init__(self):
        """Initialize the service."""
        self.repository = ExecutionRepository()
        self.action_service = ActionService()

        # Initialize execution components
        encryption = SecretEncryption()
        secret_service = SecretService(encryption)
        self.rest_executor = RestActionExecutor(secret_service)

    async def create_execution(self, request: ExecutionCreateRequest, user_id: str) -> str:
        """Create and optionally start a new execution.

        Args:
            request: The execution creation request
            user_id: ID of the user creating the execution

        Returns:
            The ID of the created execution

        Raises:
            ValueError: If action not found or invalid
        """
        # Get the action to execute
        action = await self.action_service.get_action_by_id(request.action_id)
        if not action:
            raise ValueError(f"Action {request.action_id} not found")

        # Create execution model
        execution = ExecutionModel(
            action_id=request.action_id,
            workspace_id=request.workspace_id,
            user_id=user_id,
            input_data=request.input_data,
            execution_context=request.execution_context,
            max_retries=request.max_retries,
        )

        # Save to database
        execution_id = await self.repository.create_execution(execution)

        # Start execution asynchronously (fire and forget)
        # In production, this would use a task queue like Celery
        # For now, we'll run it in the background
        import asyncio

        asyncio.create_task(self._execute_action(execution_id, action))

        return execution_id

    async def get_execution_by_id(self, execution_id: str) -> ExecutionModel | None:
        """Get an execution by its ID.

        Args:
            execution_id: The execution ID

        Returns:
            The execution model or None if not found
        """
        return await self.repository.get_execution_by_id(execution_id)

    async def update_execution(
        self, execution_id: str, update_request: ExecutionUpdateRequest, user_id: str
    ) -> bool:
        """Update an execution.

        Args:
            execution_id: The execution ID
            update_request: The update request containing fields to update
            user_id: ID of the user performing the update

        Returns:
            True if execution was updated, False if not found
        """
        # Get current execution
        execution = await self.repository.get_execution_by_id(execution_id)
        if not execution:
            return False

        # Update fields
        update_data = {}
        if update_request.status is not None:
            update_data["status"] = update_request.status
        if update_request.output_data is not None:
            update_data["output_data"] = update_request.output_data
        if update_request.error_message is not None:
            update_data["error_message"] = update_request.error_message
        if update_request.execution_context is not None:
            update_data["execution_context"] = update_request.execution_context

        # If status is being updated to completed/failed, set completion time
        if update_request.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()

        # Update in repository
        return await self.repository.update_execution(execution_id, update_data)

    async def list_executions(
        self,
        workspace_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExecutionModel]:
        """List executions for a workspace.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution models
        """
        return await self.repository.get_executions_by_workspace(
            workspace_id=workspace_id, action_id=action_id, status=status, skip=skip, limit=limit
        )

    async def list_executions_with_names(
        self,
        workspace_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """List executions for a workspace with action and user names.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution dictionaries with action_name and user_name
        """
        return await self.repository.get_executions_with_names(
            workspace_id=workspace_id, action_id=action_id, status=status, skip=skip, limit=limit
        )

    async def retry_execution(self, execution_id: str, user_id: str) -> bool:
        """Retry a failed execution.

        Args:
            execution_id: The execution ID
            user_id: ID of the user requesting the retry

        Returns:
            True if retry was initiated, False if not possible
        """
        execution = await self.repository.get_execution_by_id(execution_id)
        if not execution or not execution.can_retry():
            return False

        # Increment retry count and reset for retry
        execution.increment_retry()

        # Update in database
        updates = {
            "status": execution.status.value,
            "retry_count": execution.retry_count,
            "error_message": execution.error_message,
            "completed_at": execution.completed_at,
        }
        await self.repository.update_execution(execution_id, updates)

        # Get the action and restart execution
        action = await self.action_service.get_action_by_id(execution.action_id)
        if action:
            import asyncio

            asyncio.create_task(self._execute_action(execution_id, action))

        return True

    async def get_execution_summary(
        self, workspace_id: str, action_id: str | None = None
    ) -> ExecutionSummary:
        """Get execution summary statistics.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter

        Returns:
            Execution summary with statistics
        """
        return await self.repository.get_execution_summary(workspace_id, action_id)

    async def _execute_action(self, execution_id: str, action) -> None:
        """Execute an action asynchronously.

        Args:
            execution_id: The execution ID
            action: The action model to execute
        """
        try:
            # Get the execution
            execution = await self.repository.get_execution_by_id(execution_id)
            if not execution:
                return

            # Mark as started
            execution.mark_started()
            await self.repository.update_execution(
                execution_id, {"status": execution.status.value, "started_at": execution.started_at}
            )

            # Execute based on action type
            from ..models.action import ActionType

            if action.action_type == ActionType.REST:
                output_data, error_message = await self.rest_executor.execute(action, execution)
            else:
                # For other action types, return not implemented
                output_data = {"error": f"Action type {action.action_type} not yet implemented"}
                error_message = f"Action type {action.action_type} execution not implemented"

            # Calculate execution time
            import time

            execution_time_ms = int((time.time() - execution.started_at.timestamp()) * 1000)

            # Mark as completed or failed
            if error_message:
                execution.mark_failed(error_message, execution_time_ms)
            else:
                execution.mark_completed(output_data, execution_time_ms)

            # Update in database
            await self.repository.update_execution(
                execution_id,
                {
                    "status": execution.status.value,
                    "output_data": execution.output_data,
                    "execution_time_ms": execution.execution_time_ms,
                    "error_message": execution.error_message,
                    "completed_at": execution.completed_at,
                },
            )

        except Exception as e:
            # Handle unexpected errors
            try:
                execution = await self.repository.get_execution_by_id(execution_id)
                if execution:
                    execution.mark_failed(f"Unexpected error: {str(e)}")
                    await self.repository.update_execution(
                        execution_id,
                        {
                            "status": execution.status.value,
                            "error_message": execution.error_message,
                            "completed_at": execution.completed_at,
                        },
                    )
            except Exception:
                # If we can't even update the execution, log it
                import logging

                logging.error(f"Failed to update execution {execution_id} with error: {e}")

    async def cancel_execution(self, execution_id: str, user_id: str) -> bool:
        """Cancel a running execution.

        Args:
            execution_id: The execution ID
            user_id: ID of the user requesting cancellation

        Returns:
            True if cancelled successfully, False if not possible
        """
        execution = await self.repository.get_execution_by_id(execution_id)
        if not execution or execution.status not in [
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
        ]:
            return False

        # Mark as cancelled
        from ..models.execution import ExecutionStatus

        updates = {
            "status": ExecutionStatus.CANCELLED.value,
            "completed_at": datetime.utcnow(),
            "error_message": f"Cancelled by user {user_id}",
        }

        return await self.repository.update_execution(execution_id, updates)

    async def get_executions_by_action(
        self,
        action_id: str,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExecutionModel]:
        """Get executions for a specific action.

        Args:
            action_id: The action ID
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution models
        """
        return await self.repository.get_executions_by_action(
            action_id=action_id, status=status, skip=skip, limit=limit
        )
