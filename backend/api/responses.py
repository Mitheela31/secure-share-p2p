"""
=============================================================================
PHASE 8: Standardized API Response Module
=============================================================================

This module provides consistent JSON response formatting across all API
endpoints. It ensures all responses follow the same structure for:
- Easier frontend integration
- Better error handling
- Consistent user experience
- Cleaner API documentation

RESPONSE FORMAT:
{
    "status": "success" | "error" | "warning",
    "message": "Human-readable message",
    "data": { ... } | null,
    "errors": { ... } | null
}

=============================================================================
"""

from rest_framework.response import Response
from rest_framework import status
from typing import Any, Dict, Optional


def api_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    **kwargs
) -> Response:
    """
    Create a standardized success API response.
    
    Args:
        data: The response payload (dict, list, or any serializable data)
        message: Human-readable success message
        status_code: HTTP status code (default: 200 OK)
        **kwargs: Additional fields to include in response
    
    Returns:
        Response: DRF Response object with standardized format
    
    Example:
        return api_response(
            data={'user_id': 1, 'username': 'john_doe'},
            message='User created successfully',
            status_code=status.HTTP_201_CREATED
        )
    
    Output:
        {
            "status": "success",
            "message": "User created successfully",
            "data": {
                "user_id": 1,
                "username": "john_doe"
            }
        }
    """
    response_data = {
        "status": "success",
        "message": message,
        "data": data,
    }
    # Add any extra fields
    response_data.update(kwargs)
    
    return Response(response_data, status=status_code)


def api_error(
    message: str = "An error occurred",
    errors: Optional[Dict] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    **kwargs
) -> Response:
    """
    Create a standardized error API response.
    
    Args:
        message: Human-readable error message
        errors: Dictionary of field-specific errors
        status_code: HTTP status code (default: 400 Bad Request)
        **kwargs: Additional fields to include in response
    
    Returns:
        Response: DRF Response object with standardized error format
    
    Example:
        return api_error(
            message='Validation failed',
            errors={'email': ['Invalid email format']},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    Output:
        {
            "status": "error",
            "message": "Validation failed",
            "errors": {
                "email": ["Invalid email format"]
            }
        }
    """
    response_data = {
        "status": "error",
        "message": message,
        "errors": errors,
    }
    # Add any extra fields
    response_data.update(kwargs)
    
    return Response(response_data, status=status_code)


def api_warning(
    data: Any = None,
    message: str = "Warning",
    status_code: int = status.HTTP_200_OK,
    **kwargs
) -> Response:
    """
    Create a standardized warning API response.
    
    Used when the operation succeeded but with caveats.
    
    Args:
        data: The response payload
        message: Human-readable warning message
        status_code: HTTP status code
        **kwargs: Additional fields to include in response
    
    Returns:
        Response: DRF Response object with warning format
    """
    response_data = {
        "status": "warning",
        "message": message,
        "data": data,
    }
    response_data.update(kwargs)
    
    return Response(response_data, status=status_code)


# =============================================================================
# COMMON ERROR RESPONSES
# =============================================================================
# Pre-defined error responses for common scenarios
# =============================================================================

def unauthorized_error(message: str = "Unauthorized access") -> Response:
    """
    Return 401 Unauthorized response.
    
    Use when authentication is required but not provided or invalid.
    """
    return api_error(
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def forbidden_error(message: str = "Access denied") -> Response:
    """
    Return 403 Forbidden response.
    
    Use when user is authenticated but lacks permission for the resource.
    """
    return api_error(
        message=message,
        status_code=status.HTTP_403_FORBIDDEN
    )


def not_found_error(message: str = "Resource not found") -> Response:
    """
    Return 404 Not Found response.
    
    Use when the requested resource doesn't exist.
    """
    return api_error(
        message=message,
        status_code=status.HTTP_404_NOT_FOUND
    )


def validation_error(errors: Dict, message: str = "Validation failed") -> Response:
    """
    Return 400 Bad Request response for validation errors.
    
    Args:
        errors: Dictionary mapping field names to error messages
        message: Overall error message
    
    Example:
        return validation_error({
            'email': ['This field is required.'],
            'password': ['Password must be at least 8 characters.']
        })
    """
    return api_error(
        message=message,
        errors=errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )


def server_error(message: str = "Internal server error") -> Response:
    """
    Return 500 Internal Server Error response.
    
    Use for unexpected server errors.
    """
    return api_error(
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def rate_limit_error(message: str = "Rate limit exceeded. Please try again later.") -> Response:
    """
    Return 429 Too Many Requests response.
    
    Use when user has exceeded API rate limits.
    """
    return api_error(
        message=message,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )


# =============================================================================
# COMMON SUCCESS RESPONSES
# =============================================================================

def created_response(data: Any, message: str = "Resource created successfully") -> Response:
    """Return 201 Created response."""
    return api_response(
        data=data,
        message=message,
        status_code=status.HTTP_201_CREATED
    )


def deleted_response(message: str = "Resource deleted successfully") -> Response:
    """Return 200 OK response for deletion."""
    return api_response(
        data=None,
        message=message,
        status_code=status.HTTP_200_OK
    )


def no_content_response() -> Response:
    """Return 204 No Content response."""
    return Response(status=status.HTTP_204_NO_CONTENT)
