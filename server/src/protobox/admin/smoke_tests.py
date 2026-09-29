"""Comprehensive smoke tests and environment variable validation for ProtoBox."""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from loguru import logger

# Import settings for validation
from .config import Settings


@dataclass 
class SettingSpec:
    """Settings property specification for validation."""
    
    property_name: str
    env_var_name: str
    required: bool
    default_value: Any = None
    description: str = ""
    validation: Optional[callable] = None
    category: str = "general"
    is_secret: bool = False


class EnvironmentValidator:
    """Validates all environment variables through Settings class."""
    
    # Define all settings properties and their corresponding env vars
    SETTING_SPECS = [
        # Core Environment
        SettingSpec("environment", "ENVIRONMENT", True, "development", "Environment identifier", 
                   lambda x: x in ["development", "staging", "production", "dev_test"], "core"),
        SettingSpec("port", "PORT", False, 8090, "Server port", None, "core"),
        SettingSpec("host", "HOST", False, "0.0.0.0", "Server host", None, "core"),
        SettingSpec("workers", "WORKERS", False, 1, "Number of workers", None, "core"),
        
        # Authentication - Firebase
        SettingSpec("firebase_project_id", "FIREBASE_PROJECT_ID", True, None, "Firebase project ID", None, "auth"),
        SettingSpec("firebase_service_account_key", "FIREBASE_SERVICE_ACCOUNT_KEY", False, None, "Firebase service account JSON", None, "auth", True),
        SettingSpec("firebase_service_account_path", "FIREBASE_SERVICE_ACCOUNT_PATH", False, None, "Firebase service account file path", None, "auth"),
        SettingSpec("firebase_auth_emulator_host", "FIREBASE_AUTH_EMULATOR_HOST", False, None, "Firebase emulator host", None, "auth"),
        SettingSpec("use_firebase_emulator", None, False, False, "Firebase emulator enabled", None, "auth"),
        
        # Authentication - JWT
        SettingSpec("jwt_secret", "JWT_SECRET", True, "development-jwt-secret", "JWT signing secret", 
                   lambda x: len(x) >= 32 if x != "development-jwt-secret" else True, "auth", True),
        SettingSpec("jwt_algorithm", "JWT_ALGORITHM", False, "HS256", "JWT algorithm", None, "auth"),
        SettingSpec("access_token_expire_minutes", "ACCESS_TOKEN_EXPIRE_MINUTES", False, 60, "Access token expiry minutes", None, "auth"),
        SettingSpec("refresh_token_expire_days", "REFRESH_TOKEN_EXPIRE_DAYS", False, 30, "Refresh token expiry days", None, "auth"),
        SettingSpec("auth_test_mode", "AUTH_TEST_MODE", False, False, "Enable test mode", None, "auth"),
        SettingSpec("auth_allow_test_tokens", "AUTH_ALLOW_TEST_TOKENS", False, False, "Allow test tokens", None, "auth"),
        
        # Database
        SettingSpec("mongodb_url", "MONGODB_URL", True, "mongodb://localhost:27017", "MongoDB connection URL", None, "database"),
        SettingSpec("database_name", "DATABASE_NAME", False, "mcp_server", "Database name", None, "database"),
        SettingSpec("skip_index_creation", "SKIP_INDEX_CREATION", False, False, "Skip index creation", None, "database"),
        SettingSpec("mcp_skip_index_creation", "MCP_SKIP_INDEX_CREATION", False, False, "Skip MCP index creation", None, "database"),
        
        # S3/Tigris Storage (CRITICAL)
        SettingSpec("tigris_access_key", "AWS_ACCESS_KEY_ID", True, "", "S3/Tigris access key", 
                   lambda x: len(x) > 0, "storage", True),
        SettingSpec("tigris_secret_key", "AWS_SECRET_ACCESS_KEY", True, "", "S3/Tigris secret key",
                   lambda x: len(x) > 0, "storage", True),
        SettingSpec("tigris_endpoint", "AWS_ENDPOINT_URL_S3", True, "", "S3/Tigris endpoint URL",
                   lambda x: len(x) > 0 and x.startswith("http"), "storage"),
        SettingSpec("tigris_bucket_name", "AWS_BUCKET_NAME", True, "protobox-dev", "S3/Tigris bucket name",
                   lambda x: len(x) > 0, "storage"),
        
        # AI/OpenAI
        SettingSpec("openai_api_key", "OPENAI_API_KEY", True, "", "OpenAI API key",
                   lambda x: len(x) > 0 and x.startswith("sk-"), "ai", True),
        SettingSpec("openai_model", "OPENAI_MODEL", False, "gpt-4o-mini", "OpenAI model", None, "ai"),
        SettingSpec("embedding_model", "EMBEDDING_MODEL", False, "text-embedding-3-small", "Embedding model", None, "ai"),
        SettingSpec("embedding_provider", "EMBEDDING_PROVIDER", False, "openai", "Embedding provider", 
                   lambda x: x in ["openai", "huggingface"], "ai"),
        
        # Document Processing
        SettingSpec("document_processor_url", "DOCUMENT_PROCESSOR_URL", False, None, "Document processor URL", None, "processing"),
        SettingSpec("document_processor_api_key", "DOCUMENT_PROCESSOR_API_KEY", False, None, "Document processor API key", None, "processing", True),
        
        # Security
        SettingSpec("_secret_encryption_key", "MCP_SECRET_KEY", True, "development-secret-key-12345", "MCP encryption secret",
                   lambda x: len(x) >= 32 if x != "development-secret-key-12345" else True, "security", True),
        SettingSpec("internal_api_secret", "INTERNAL_API_SECRET", False, "", "Internal API secret", None, "security", True),
        SettingSpec("admin_config_secret", "ADMIN_CONFIG_SECRET", False, None, "Admin config secret", None, "security", True),
        
        # Monitoring
        SettingSpec("monitoring_api_key", "MCP_MONITORING_API_KEY", False, "", "Monitoring API key", 
                   lambda x: x.startswith("mon_") and len(x) >= 20 if x else True, "monitoring", True),
        SettingSpec("commit_sha", "COMMIT_SHA", False, "unknown", "Git commit SHA", None, "monitoring"),
        SettingSpec("deployed_at", "DEPLOYED_AT", False, "unknown", "Deployment timestamp", None, "monitoring"),
        SettingSpec("app_version", "APP_VERSION", False, "1.0.0", "Application version", None, "monitoring"),
        
        # URLs and Integration
        SettingSpec("admin_api_base_url", "ADMIN_API_BASE_URL", False, "http://localhost:8090/admin/api/v1", "Admin API base URL", None, "urls"),
        SettingSpec("platform_api_url", "PLATFORM_API_URL", False, "http://localhost:3000", "Platform API URL", None, "urls"),
        SettingSpec("mcp_base_url", "MCP_BASE_URL", False, "http://localhost:8090", "MCP base URL", None, "urls"),
        SettingSpec("mcp_server_url", "MCP_SERVER_URL", False, "http://localhost:8090", "MCP server URL", None, "urls"),
        
        # CORS
        SettingSpec("cors_allowed_origins", "CORS_ALLOWED_ORIGINS", False, "", "CORS allowed origins", None, "cors"),
        SettingSpec("vercel_url", "VERCEL_URL", False, None, "Vercel URL", None, "cors"),
        
        # Cache
        SettingSpec("cache_backend", "CACHE_BACKEND", False, "memory", "Cache backend", 
                   lambda x: x in ["memory", "redis"], "cache"),
        SettingSpec("redis_url", "REDIS_URL", False, "redis://localhost:6379", "Redis URL", None, "cache"),
        
        # Performance Limits
        SettingSpec("max_content_size", "MAX_CONTENT_SIZE", False, 50 * 1024 * 1024, "Max content size (bytes)", None, "limits"),
        SettingSpec("max_file_size", "MAX_FILE_SIZE", False, 10 * 1024 * 1024, "Max file size (bytes)", None, "limits"),
        SettingSpec("page_retrieval_timeout", "PAGE_RETRIEVAL_TIMEOUT", False, 10, "Page retrieval timeout (seconds)", None, "limits"),
        SettingSpec("kb_source_processing_timeout", "KB_SOURCE_PROCESSING_TIMEOUT", False, 300, "Knowledge base processing timeout", None, "limits"),
    ]
    
    def __init__(self):
        self.settings = Settings()
        self.results: Dict[str, Any] = {}
        
    def validate_all(self) -> Dict[str, Any]:
        """Validate all settings through Settings class."""
        logger.info("🔍 Starting comprehensive settings validation...")
        
        results = {
            "overall_status": "healthy",
            "total_settings": len(self.SETTING_SPECS),
            "categories": {},
            "missing_required": [],
            "validation_failures": [],
            "recommendations": [],
            "summary": {}
        }
        
        # Group by category
        by_category = {}
        for spec in self.SETTING_SPECS:
            if spec.category not in by_category:
                by_category[spec.category] = []
            by_category[spec.category].append(spec)
            
        # Validate each category
        for category, specs in by_category.items():
            category_results = self._validate_category(category, specs)
            results["categories"][category] = category_results
            
            # Collect issues
            if category_results["missing_required"]:
                results["missing_required"].extend(category_results["missing_required"])
            if category_results["validation_failures"]:
                results["validation_failures"].extend(category_results["validation_failures"])
                
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)
        
        # Overall status
        if results["missing_required"] or results["validation_failures"]:
            results["overall_status"] = "degraded"
            if results["missing_required"]:
                results["overall_status"] = "unhealthy"
                
        # Summary
        results["summary"] = {
            "total_checked": len(self.SETTING_SPECS),
            "missing_required": len(results["missing_required"]),
            "validation_failures": len(results["validation_failures"]),
            "categories_healthy": sum(1 for cat in results["categories"].values() 
                                    if cat["status"] == "healthy"),
            "categories_total": len(results["categories"])
        }
        
        logger.info(f"✅ Settings validation complete: {results['overall_status']}")
        return results
        
    def _validate_category(self, category: str, specs: List[SettingSpec]) -> Dict[str, Any]:
        """Validate settings in a category."""
        category_result = {
            "status": "healthy",
            "settings": {},
            "missing_required": [],
            "validation_failures": [],
            "count": len(specs)
        }
        
        for spec in specs:
            setting_result = self._validate_setting(spec)
            category_result["settings"][spec.property_name] = setting_result
            
            if setting_result["status"] == "missing" and spec.required:
                category_result["missing_required"].append(spec.property_name)
                category_result["status"] = "unhealthy"
            elif setting_result["status"] == "invalid":
                category_result["validation_failures"].append(spec.property_name)
                if category_result["status"] == "healthy":
                    category_result["status"] = "degraded"
                    
        return category_result
        
    def _validate_setting(self, spec: SettingSpec) -> Dict[str, Any]:
        """Validate a single setting from Settings class."""
        # Get value from settings object
        try:
            value = getattr(self.settings, spec.property_name)
        except AttributeError:
            return {
                "name": spec.property_name,
                "env_var": spec.env_var_name,
                "status": "missing",
                "message": f"Setting property {spec.property_name} not found in Settings class",
                "required": spec.required,
                "description": spec.description
            }
        
        result = {
            "name": spec.property_name,
            "env_var": spec.env_var_name,
            "value_present": value is not None and value != "",
            "using_default": False,
            "status": "healthy",
            "description": spec.description,
            "required": spec.required,
            "is_secret": spec.is_secret
        }
        
        # Handle secret values (don't expose actual value)
        if spec.is_secret:
            result["value_length"] = len(str(value)) if value else 0
            result["value_masked"] = "***" if value else None
        else:
            result["value"] = value
            result["value_length"] = len(str(value)) if value else 0
        
        # Check if missing or empty
        if value is None or value == "":
            if spec.required:
                result["status"] = "missing"
                result["message"] = f"Required setting {spec.property_name} is not configured"
            else:
                result["status"] = "using_default" 
                result["using_default"] = True
                result["default_value"] = spec.default_value
                result["message"] = f"Using default value for {spec.property_name}"
            return result
            
        # Check if using default
        if value == spec.default_value:
            result["using_default"] = True
            result["message"] = f"Using default value for {spec.property_name}"
        
        # Validate if function provided
        if spec.validation:
            try:
                if not spec.validation(value):
                    result["status"] = "invalid"
                    result["message"] = f"Validation failed for {spec.property_name}"
                    return result
            except (TypeError, ValueError, AttributeError) as e:
                result["status"] = "invalid"
                result["message"] = f"Validation error for {spec.property_name}: {e}"
                return result
                
        result["message"] = f"✅ {spec.property_name} is properly configured"
        return result
        
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Missing required variables
        if results["missing_required"]:
            recommendations.append(
                f"⚠️ Set {len(results['missing_required'])} required environment variables: "
                f"{', '.join(results['missing_required'])}"
            )
            
        # Validation failures
        if results["validation_failures"]:
            recommendations.append(
                f"🔧 Fix {len(results['validation_failures'])} validation issues: "
                f"{', '.join(results['validation_failures'])}"
            )
            
        # Security recommendations
        security_vars = results["categories"].get("security", {}).get("variables", {})
        for var_name, var_result in security_vars.items():
            if var_result.get("using_default") and "development" in var_result.get("default_value", ""):
                recommendations.append(
                    f"🔒 Change {var_name} from development default in production"
                )
                
        # Storage health
        storage_status = results["categories"].get("storage", {}).get("status")
        if storage_status != "healthy":
            recommendations.append(
                "💾 Configure S3/Tigris storage credentials - required for file uploads"
            )
            
        if not recommendations:
            recommendations.append("✅ All environment variables are properly configured")
            
        return recommendations


class SmokeTestRunner:
    """Runs comprehensive smoke tests for ProtoBox services."""
    
    def __init__(self):
        self.settings = Settings()
        self.env_validator = EnvironmentValidator()
        
    async def run_smoke_tests(self) -> Dict[str, Any]:
        """Run all smoke tests."""
        logger.info("🚀 Starting comprehensive smoke tests...")
        
        results = {
            "status": "healthy", 
            "timestamp": "UTC",
            "tests": {},
            "summary": {},
            "recommendations": []
        }
        
        # 1. Environment validation
        results["tests"]["environment"] = self.env_validator.validate_all()
        
        # 2. Settings loading
        results["tests"]["settings"] = self._test_settings_loading()
        
        # 3. Critical service availability  
        results["tests"]["critical_services"] = await self._test_critical_services()
        
        # Overall status
        test_statuses = [test["overall_status"] if "overall_status" in test 
                        else test.get("status", "unknown") 
                        for test in results["tests"].values()]
        
        if "unhealthy" in test_statuses:
            results["status"] = "unhealthy"
        elif "degraded" in test_statuses:
            results["status"] = "degraded"
            
        # Summary
        results["summary"] = {
            "total_tests": len(results["tests"]),
            "passed": sum(1 for status in test_statuses if status == "healthy"),
            "degraded": sum(1 for status in test_statuses if status == "degraded"), 
            "failed": sum(1 for status in test_statuses if status == "unhealthy"),
            "environment": self.settings.environment,
            "can_start_server": results["status"] != "unhealthy"
        }
        
        # Recommendations
        for test_result in results["tests"].values():
            if "recommendations" in test_result:
                results["recommendations"].extend(test_result["recommendations"])
                
        logger.info(f"✅ Smoke tests complete: {results['status']}")
        return results
        
    def _test_settings_loading(self) -> Dict[str, Any]:
        """Test that settings load correctly."""
        try:
            # Test key settings are accessible
            critical_settings = [
                ("environment", self.settings.environment),
                ("firebase_project_id", self.settings.firebase_project_id),
                ("mongodb_url", self.settings.mongodb_url),
                ("jwt_secret", self.settings.jwt_secret),
                ("tigris_endpoint", self.settings.tigris_endpoint),
                ("openai_api_key", self.settings.openai_api_key),
            ]
            
            failed_settings = []
            for setting_name, setting_value in critical_settings:
                if setting_value is None or setting_value == "":
                    failed_settings.append(setting_name)
                    
            status = "healthy" if not failed_settings else "degraded"
            
            return {
                "status": status,
                "settings_tested": len(critical_settings),
                "failed_settings": failed_settings,
                "message": "Settings loaded successfully" if status == "healthy" 
                          else f"Some settings missing: {failed_settings}"
            }
            
        except (ImportError, AttributeError, TypeError) as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": f"Failed to load settings: {e}"
            }
            
    async def _test_critical_services(self) -> Dict[str, Any]:
        """Test critical service configuration."""
        services = {
            "storage_config": self._test_storage_config(),
            "ai_config": self._test_ai_config(),
            "auth_config": self._test_auth_config(),
            "database_config": self._test_database_config()
        }
        
        statuses = [service["status"] for service in services.values()]
        overall_status = "healthy"
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
            
        return {
            "status": overall_status,
            "services": services,
            "ready_to_start": overall_status != "unhealthy"
        }
        
    def _test_storage_config(self) -> Dict[str, Any]:
        """Test S3/Tigris storage configuration."""
        required = ["tigris_access_key", "tigris_secret_key", "tigris_endpoint", "tigris_bucket_name"]
        missing = []
        
        for setting in required:
            value = getattr(self.settings, setting, None)
            if not value or value == "":
                missing.append(setting)
                
        status = "healthy" if not missing else "unhealthy"
        
        return {
            "status": status,
            "missing_config": missing,
            "message": "Storage properly configured" if status == "healthy"
                      else f"Missing storage config: {missing}"
        }
        
    def _test_ai_config(self) -> Dict[str, Any]:
        """Test AI/OpenAI configuration."""
        if not self.settings.openai_api_key:
            return {
                "status": "unhealthy",
                "message": "OpenAI API key not configured"
            }
            
        return {
            "status": "healthy", 
            "message": "AI configuration ready"
        }
        
    def _test_auth_config(self) -> Dict[str, Any]:
        """Test authentication configuration."""
        if self.settings.environment == "production":
            if not self.settings.firebase_project_id:
                return {
                    "status": "unhealthy",
                    "message": "Firebase project ID required for production"
                }
                
        return {
            "status": "healthy",
            "firebase_emulator": self.settings.use_firebase_emulator,
            "message": "Authentication configuration ready"
        }
        
    def _test_database_config(self) -> Dict[str, Any]:
        """Test database configuration."""
        if not self.settings.mongodb_url:
            return {
                "status": "unhealthy", 
                "message": "MongoDB URL not configured"
            }
            
        return {
            "status": "healthy",
            "message": "Database configuration ready"
        }


# Main smoke test function for use in startup
async def run_startup_smoke_tests() -> Dict[str, Any]:
    """Run smoke tests during startup."""
    runner = SmokeTestRunner()
    return await runner.run_smoke_tests()


# Environment validation function
def validate_environment() -> Dict[str, Any]:
    """Validate environment variables."""
    validator = EnvironmentValidator()
    return validator.validate_all()


if __name__ == "__main__":
    """CLI usage for testing."""
    import asyncio
    
    async def main():
        # Run smoke tests
        results = await run_startup_smoke_tests()
        
        print(f"\n🏥 SMOKE TEST RESULTS - Status: {results['status'].upper()}")
        print(f"Environment: {results['summary']['environment']}")
        print(f"Tests: {results['summary']['passed']}/{results['summary']['total_tests']} passed")
        
        if results["recommendations"]:
            print("\n📋 RECOMMENDATIONS:")
            for rec in results["recommendations"]:
                print(f"  {rec}")
                
        # Detailed environment validation
        env_results = results["tests"]["environment"]
        print(f"\n🔍 ENVIRONMENT VARIABLES: {env_results['overall_status'].upper()}")
        print(f"Categories: {env_results['summary']['categories_healthy']}/{env_results['summary']['categories_total']} healthy")
        
        if env_results["missing_required"]:
            print(f"\n❌ MISSING REQUIRED: {', '.join(env_results['missing_required'])}")
            
        if env_results["validation_failures"]:
            print(f"\n⚠️ VALIDATION FAILURES: {', '.join(env_results['validation_failures'])}")
            
        return results["status"] == "healthy"
        
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)