"""Slug validation utilities for workspace slugs."""

import re

# Reserved slugs that cannot be used
RESERVED_SLUGS = {
    "api",
    "app",
    "admin",
    "dashboard",
    "login",
    "logout",
    "signup",
    "register",
    "auth",
    "oauth",
    "callback",
    "webhook",
    "webhooks",
    "settings",
    "profile",
    "account",
    "billing",
    "subscribe",
    "subscription",
    "help",
    "support",
    "docs",
    "documentation",
    "blog",
    "about",
    "contact",
    "privacy",
    "terms",
    "legal",
    "www",
    "mail",
    "ftp",
    "email",
    "smtp",
    "pop",
    "imap",
    "ssh",
    "sftp",
    "vpn",
    "cdn",
    "assets",
    "static",
    "public",
    "private",
    "test",
    "dev",
    "development",
    "staging",
    "prod",
    "production",
    "localhost",
    "127",
    "0",
    "console",
    "portal",
    "manage",
    "management",
    "api-docs",
    "swagger",
    "graphql",
    "rest",
    "rpc",
    "grpc",
    "health",
    "healthcheck",
    "status",
    "metrics",
    "monitoring",
    "analytics",
    "tracking",
    "pixel",
    "tag",
    "tags",
    "category",
    "categories",
    "user",
    "users",
    "team",
    "teams",
    "org",
    "organization",
    "organizations",
    "workspace",
    "workspaces",
    "project",
    "projects",
    "repo",
    "repository",
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "svn",
    "hg",
    "mercurial",
}

# Patterns that are not allowed in slugs
INVALID_PATTERNS = [
    r"^-",  # Starts with hyphen
    r"-$",  # Ends with hyphen
    r"--",  # Contains double hyphen
    r"^[0-9]+$",  # Only numbers
    r"^\.",  # Starts with dot
    r"\.$",  # Ends with dot
    r"\.{2,}",  # Contains multiple dots
    r"^_",  # Starts with underscore
    r"_$",  # Ends with underscore
]


def sanitize_slug(name: str) -> str:
    """
    Sanitize a name into a valid slug.

    Args:
        name: The name to convert to a slug

    Returns:
        A sanitized slug
    """
    # Convert to lowercase and strip whitespace
    slug = name.lower().strip()

    # Replace spaces and special characters with hyphens
    slug = re.sub(r"[^a-z0-9-]", "-", slug)

    # Replace multiple hyphens with single hyphen
    slug = re.sub(r"-+", "-", slug)

    # Remove leading and trailing hyphens
    slug = slug.strip("-")

    # If slug is empty or only numbers, prepend 'workspace-'
    if not slug or slug.isdigit():
        slug = f"workspace-{slug if slug else 'default'}"

    return slug


def validate_slug(slug: str) -> tuple[bool, str | None]:
    """
    Validate a workspace slug.

    Args:
        slug: The slug to validate

    Returns:
        A tuple of (is_valid, error_message)
    """
    # Check if empty
    if not slug:
        return False, "Slug cannot be empty"

    # Check length
    if len(slug) < 3:
        return False, "Slug must be at least 3 characters long"

    if len(slug) > 63:
        return False, "Slug cannot exceed 63 characters"

    # Check if it's a reserved slug
    if slug.lower() in RESERVED_SLUGS:
        return False, f"'{slug}' is a reserved name and cannot be used"

    # Check for valid characters (lowercase letters, numbers, hyphens)
    if not re.match(r"^[a-z0-9-]+$", slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"

    # Check against invalid patterns
    for pattern in INVALID_PATTERNS:
        if re.search(pattern, slug):
            if pattern == r"^-":
                return False, "Slug cannot start with a hyphen"
            if pattern == r"-$":
                return False, "Slug cannot end with a hyphen"
            if pattern == r"--":
                return False, "Slug cannot contain consecutive hyphens"
            if pattern == r"^[0-9]+$":
                return False, "Slug cannot be only numbers"
            if pattern == r"^\.":
                return False, "Slug cannot start with a dot"
            if pattern == r"\.$":
                return False, "Slug cannot end with a dot"
            if pattern == r"\.{2,}":
                return False, "Slug cannot contain consecutive dots"
            if pattern == r"^_":
                return False, "Slug cannot start with an underscore"
            if pattern == r"_$":
                return False, "Slug cannot end with an underscore"

    return True, None


def is_slug_available(slug: str, existing_slugs: list) -> bool:
    """
    Check if a slug is available (not already taken).

    Args:
        slug: The slug to check
        existing_slugs: List of existing slugs in the system

    Returns:
        True if the slug is available, False otherwise
    """
    return slug.lower() not in [s.lower() for s in existing_slugs if s is not None]


def suggest_alternative_slug(
    base_slug: str, existing_slugs: list, max_attempts: int = 10
) -> str | None:
    """
    Suggest an alternative slug if the desired one is taken.

    Args:
        base_slug: The base slug to modify
        existing_slugs: List of existing slugs
        max_attempts: Maximum number of attempts to find a unique slug

    Returns:
        An available slug, or None if no alternatives found
    """
    # First, try the base slug
    if is_slug_available(base_slug, existing_slugs):
        return base_slug

    # Try appending numbers
    for i in range(1, max_attempts + 1):
        alternative = f"{base_slug}-{i}"
        if is_slug_available(alternative, existing_slugs):
            return alternative

    # Try with a random suffix
    import random
    import string

    for _ in range(max_attempts):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        alternative = f"{base_slug}-{suffix}"
        if is_slug_available(alternative, existing_slugs):
            return alternative

    return None
