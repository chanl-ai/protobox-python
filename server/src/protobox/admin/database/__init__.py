"""MongoDB database integration for admin API."""

from .connection import DatabaseConnection, get_database_connection

__all__ = [
    "DatabaseConnection",
    "get_database_connection",
]
