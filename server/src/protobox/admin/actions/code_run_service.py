"""Code execution microservice for MCP."""

import asyncio
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..models.action import ActionModel, ActionType, CodeRunConfig
from ..models.execution import ExecutionModel, ExecutionStatus
from .code_run_executor import CodeRunActionExecutor
from ..services.secret_service import SecretService, SecretEncryption


# Global executor instance
executor: CodeRunActionExecutor | None = None


class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""

    code: str
    language: str = "python"
    timeout: int = 30
    memory_limit_mb: int = 256
    allowed_imports: list[str] = ["json", "math", "datetime", "re", "time", "random"]
    entry_point: str = "output"
    input_data: dict[str, Any] = {}


class CodeExecutionResponse(BaseModel):
    """Response model for code execution."""

    success: bool
    result: dict[str, Any] | None = None
    error_message: str | None = None
    execution_time_ms: int
    memory_usage_mb: int
    exit_code: int
    stdout: str = ""
    stderr: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global executor

    # Startup
    logger.info("Starting code execution service")
    encryption = SecretEncryption()
    secret_service = SecretService(encryption)
    executor = CodeRunActionExecutor(secret_service)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    yield

    # Shutdown
    logger.info("Shutting down code execution service")
    executor = None


# Create FastAPI app with security headers
app = FastAPI(
    title="MCP Code Execution Service",
    description="Secure sandboxed code execution microservice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production
    redoc_url=None,  # Disable redoc in production
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000"],  # Restrict origins
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-code-executor", "version": "1.0.0"}


@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(
    request: CodeExecutionRequest, background_tasks: BackgroundTasks
) -> CodeExecutionResponse:
    """Execute code in a secure sandbox."""
    global executor

    if not executor:
        raise HTTPException(status_code=503, detail="Service not ready")

    logger.info("Code execution requested", language=request.language, timeout=request.timeout)

    try:
        # Create action model with new CodeRunConfig
        config = CodeRunConfig(
            language=request.language,
            code=request.code,
            timeout=min(request.timeout, 60),  # Cap at 60 seconds
            memory_limit_mb=min(request.memory_limit_mb, 512),  # Cap at 512MB
            allowed_imports=request.allowed_imports,
            entry_point=request.entry_point,
        )
        
        action = ActionModel(
            name="api_code_execution",
            type=ActionType.CODE_RUN,
            description="API code execution request",
            default_config=config.model_dump(),
            created_by="api_user",
        )

        # Create execution model
        execution = ExecutionModel(
            action_id="api_execution",
            workspace_id="api_workspace",
            user_id="api_user",
            input_data=request.input_data,
            status=ExecutionStatus.PENDING,
        )

        # Execute with timeout
        try:
            success, output_data, error_message = await asyncio.wait_for(
                executor.execute(action, execution),
                timeout=request.timeout + 5,  # Add buffer for cleanup
            )
        except TimeoutError:
            logger.warning("Code execution timed out", timeout=request.timeout)
            return CodeExecutionResponse(
                success=False,
                error_message="Execution timed out",
                execution_time_ms=request.timeout * 1000,
                memory_usage_mb=0,
                exit_code=124,
            )

        # Parse response from worker
        success = success and error_message is None

        # Log execution for monitoring
        background_tasks.add_task(
            log_execution,
            success=success,
            execution_time=output_data.get("execution_time_ms", 0),
            memory_usage=output_data.get("memory_usage_mb", 0),
        )

        return CodeExecutionResponse(
            success=success,
            result=output_data.get("result"),
            error_message=error_message or output_data.get("error"),
            execution_time_ms=output_data.get("execution_time_ms", 0),
            memory_usage_mb=output_data.get("memory_usage_mb", 0),
            exit_code=0 if success else 1,
            stdout=output_data.get("stdout", ""),
            stderr=output_data.get("stderr", ""),
        )

    except Exception as e:
        logger.error("Code execution failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal execution error")


async def log_execution(success: bool, execution_time: int, memory_usage: int):
    """Log execution metrics for monitoring."""
    logger.info(
        "Code execution completed",
        success=success,
        execution_time_ms=execution_time,
        memory_usage_mb=memory_usage,
    )


if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    workers = int(os.getenv("WORKERS", "1"))

    # Security: limit workers to prevent resource exhaustion
    workers = min(workers, 2)

    logger.info("Starting server", host=host, port=port, workers=workers)

    uvicorn.run(
        "protobox.admin.actions.code_run_service:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True,
        server_header=False,  # Don't expose server info
        date_header=False,  # Don't expose date
    )
