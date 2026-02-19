"""Custom OpenAPI schema configuration for BMKG API.

This module provides customizations to the auto-generated OpenAPI schema,
including security schemes, additional documentation, and examples.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict:
    """Generate custom OpenAPI schema with additional metadata.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Customized OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        contact=app.contact,
        license_info=app.license_info,
        terms_of_service=app.terms_of_service,
        servers=app.servers,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for higher rate limits (120 req/min vs 30 req/min)",
        }
    }

    # Add response headers documentation
    openapi_schema["components"]["headers"] = {
        "X-Cache": {
            "description": "Cache status: HIT (from cache) or MISS (fetched from BMKG)",
            "schema": {"type": "string", "enum": ["HIT", "MISS"]},
        },
        "X-Cache-TTL": {
            "description": "Seconds until cache expires",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Limit": {
            "description": "Request limit per time window",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Remaining": {
            "description": "Remaining requests in current window",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Reset": {
            "description": "Unix timestamp when the rate limit resets",
            "schema": {"type": "integer"},
        },
    }

    # Add common responses to all endpoints
    for path_data in openapi_schema.get("paths", {}).values():
        for method_data in path_data.values():
            if isinstance(method_data, dict):
                # Add rate limit headers to successful responses
                responses = method_data.get("responses", {})
                for response in responses.values():
                    if isinstance(response, dict) and "headers" not in response:
                        response["headers"] = {
                            "X-Cache": {"$ref": "#/components/headers/X-Cache"},
                            "X-Cache-TTL": {"$ref": "#/components/headers/X-Cache-TTL"},
                        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def configure_openapi(app: FastAPI) -> None:
    """Configure custom OpenAPI for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Store the original openapi function
    original_openapi = app.openapi

    def get_custom_openapi():
        """Override the default openapi function."""
        return custom_openapi(app)

    # Replace the openapi method
    app.openapi = get_custom_openapi
