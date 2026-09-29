"""
Startup Integration Checks
Run integration tests during server startup to fail fast on deployment issues
"""
import logging
import asyncio
from typing import Dict, Any, Optional

from .config import settings
from ..shared.integration_testing import run_startup_integration_checks

logger = logging.getLogger(__name__)

class StartupValidator:
    """Validates system health during startup"""
    
    def __init__(self):
        self.startup_results: Optional[Dict[str, Any]] = None
        self.startup_completed = False
        
    async def run_startup_validation(self) -> Dict[str, Any]:
        """Run startup validation with integration checks"""
        logger.info("🚀 Starting startup validation...")
        
        try:
            # Run integration checks
            self.startup_results = await run_startup_integration_checks()
            self.startup_completed = True
            
            # Log results
            status = self.startup_results.get("status", "unknown")
            duration = self.startup_results.get("duration_seconds", 0)
            summary = self.startup_results.get("summary", {})
            
            logger.info(f"✅ Startup validation completed in {duration:.2f}s")
            logger.info(f"📊 Results: {summary}")
            
            # Log any self-healing actions
            healing_actions = self.startup_results.get("self_healing_actions", [])
            if healing_actions:
                logger.warning(f"🔧 Self-healing actions applied: {healing_actions}")
            
            # Check if we should fail startup
            if status == "failed" and settings.get_bool("STARTUP_CHECKS_FAIL_FAST", True):
                failed_tests = [
                    r for r in self.startup_results.get("test_results", []) 
                    if r.get("status") == "failed"
                ]
                error_msg = f"Startup validation failed: {[t['name'] for t in failed_tests]}"
                logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)
            
            return self.startup_results
            
        except Exception as e:
            logger.error(f"❌ Startup validation failed: {e}")
            self.startup_results = {
                "status": "failed",
                "error": str(e),
                "startup_failed": True
            }
            
            # Re-raise if fail_fast is enabled
            if settings.get_bool("STARTUP_CHECKS_FAIL_FAST", True):
                raise
                
            return self.startup_results
    
    def get_startup_status(self) -> Dict[str, Any]:
        """Get current startup validation status"""
        if not self.startup_completed:
            return {
                "status": "in_progress",
                "message": "Startup validation in progress"
            }
        
        return self.startup_results or {
            "status": "unknown",
            "message": "Startup validation not completed"
        }


# Global startup validator instance
startup_validator = StartupValidator()


async def run_startup_checks() -> Dict[str, Any]:
    """Entry point for startup checks - called during server startup"""
    return await startup_validator.run_startup_validation()


def get_startup_status() -> Dict[str, Any]:
    """Get startup check status - called by health endpoint"""
    return startup_validator.get_startup_status()


# Configuration validation
def validate_startup_check_config():
    """Validate startup check configuration"""
    if settings.get_bool("STARTUP_INTEGRATION_CHECKS_ENABLED", False):
        logger.info("🔧 Startup integration checks ENABLED")
        
        # Log configuration
        fail_fast = settings.get_bool("STARTUP_CHECKS_FAIL_FAST", True)
        timeout = settings.get_int("STARTUP_CHECKS_TIMEOUT", 30)
        tests_filter = settings.get_list("STARTUP_TESTS_FILTER", None)
        self_healing = settings.get_bool("STARTUP_SELF_HEALING_ENABLED", True)
        
        logger.info(f"📋 Config: fail_fast={fail_fast}, timeout={timeout}s, tests={tests_filter}, self_healing={self_healing}")
        
        if fail_fast:
            logger.warning("⚠️  FAIL_FAST enabled - server will exit on startup check failures")
    else:
        logger.info("🔧 Startup integration checks DISABLED")


# Example environment variable configuration:
"""
# Enable startup checks (disabled by default)
STARTUP_INTEGRATION_CHECKS_ENABLED=true

# Fail fast on startup check failures (default: true)
STARTUP_CHECKS_FAIL_FAST=true

# Timeout for startup checks (default: 30 seconds)
STARTUP_CHECKS_TIMEOUT=30

# Filter which tests to run (default: environment-specific)
STARTUP_TESTS_FILTER=health_check,cors_validation,auth_flow

# Enable self-healing actions (default: true)
STARTUP_SELF_HEALING_ENABLED=true
"""