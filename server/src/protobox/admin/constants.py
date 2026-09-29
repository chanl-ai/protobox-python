"""Constants for the admin API."""

# System user constants
SYSTEM_USER_ID = "system"
ADMIN_USER_ID = "admin"

# Audit field constants
class SystemUsers:
    """System user identifiers for audit fields."""
    SYSTEM = "system"
    ADMIN = "admin"
    MIGRATION = "migration"
    SEEDER = "seeder"
    
# Common field defaults
DEFAULT_PAGE_SIZE = 20
DEFAULT_MAX_PAGE_SIZE = 100