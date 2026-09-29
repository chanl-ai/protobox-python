"""Configuration for Document Processor Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Service configuration using same pattern as main backend."""
    
    # Environment
    environment: str = "development"
    
    # Service configuration
    service_port: int = 8092
    service_host: str = "0.0.0.0"
    
    # Processing limits
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    processing_timeout: int = 120  # seconds
    download_timeout: int = 60  # seconds for downloading from S3
    
    # OCR settings
    ocr_enabled: bool = True
    ocr_languages: str = "eng"  # Tesseract language codes
    ocr_confidence_threshold: float = 60.0
    
    # Table extraction
    table_extraction_enabled: bool = True
    
    # Performance
    max_pages_per_document: int = 500
    max_image_dimension: int = 4000  # pixels
    
    # Logging
    log_level: str = "INFO"
    
    # Security
    api_key: Optional[str] = None  # API key for authentication
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ["development", "dev", "local", "dev_test"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ["production", "prod", "prd"]


# Create global settings instance
settings = Settings()