"""
Unit tests for authentication dependencies.

NOTE: Most auth dependency tests have been moved to integration tests.

The authentication system uses complex dependency injection with database services,
JWT validation, and API key management that are better tested as integration tests
rather than unit tests with extensive mocking.

See server/tests/integration/ for comprehensive authentication testing.
"""



def test_auth_dependencies_module_imports():
    """Test that auth dependencies module imports correctly."""
    from protobox.admin.auth.dependencies import (
        get_current_user,
        get_current_user_api_key,
        get_current_user_jwt,
        require_api_key_authentication,
        require_authentication,
        require_jwt_authentication,
    )
    from protobox.admin.auth.models import JWTClaims, User

    # Test passes if imports work
    assert get_current_user_jwt is not None
    assert get_current_user_api_key is not None
    assert get_current_user is not None
    assert require_authentication is not None
    assert require_jwt_authentication is not None
    assert require_api_key_authentication is not None
    assert User is not None
    assert JWTClaims is not None
