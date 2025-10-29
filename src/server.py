#!/usr/bin/env python3
"""
Yandex MCP Server - Core Server Implementation

This module implements the FastMCP server for Yandex services integration.
It handles authentication, API communication, and exposes tools for interacting
with Yandex APIs.
"""

import os
import sys
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP, settings
from fastmcp.exceptions import ToolError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables from .env file
load_dotenv()

# Centralized configuration with environment variable overrides
class Config:
    """Centralized configuration for the Yandex MCP Server."""
    
    # Authentication
    OAUTH_TOKEN: str = os.getenv("YANDEX_OAUTH_TOKEN", "")
    
    # API Configuration
    BASE_URL: str = os.getenv("YANDEX_API_BASE_URL", "https://cloud-api.yandex.net")
    WORDSTAT_BASE_URL: str = os.getenv("YANDEX_WORDSTAT_BASE_URL", "https://api-sandbox.direct.yandex.com/json/v5/keywordsresearch")
    
    # Timeout configuration (convert milliseconds to seconds)
    _request_timeout_raw: str = os.getenv("REQUEST_TIMEOUT", "30000")
    try:
        REQUEST_TIMEOUT_SECONDS: float = max(1.0, float(_request_timeout_raw) / 1000.0)
    except ValueError:
        logger.warning(
            "Invalid REQUEST_TIMEOUT value '%s'. Falling back to default 30 seconds.",
            _request_timeout_raw,
        )
        REQUEST_TIMEOUT_SECONDS = 30.0
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.OAUTH_TOKEN:
            error_msg = (
                "ERROR: YANDEX_OAUTH_TOKEN environment variable is not set.\n\n"
                "To use this MCP server, you must provide a valid Yandex OAuth token.\n"
                "Please follow these steps:\n\n"
                "1. Copy .env.example to .env:\n"
                "   cp .env.example .env\n\n"
                "2. Obtain a Yandex OAuth token:\n"
                "   Visit: https://oauth.yandex.com/\n"
                "   See README.md for detailed instructions\n\n"
                "3. Add your token to the .env file:\n"
                "   YANDEX_OAUTH_TOKEN=your_token_here\n\n"
                "For more information, see:\n"
                "- README.md - Setup and authentication guide\n"
                "- .env.example - Configuration template with all options\n"
            )
            logger.error(error_msg)
            raise ValueError("YANDEX_OAUTH_TOKEN is required but not set")
        
        logger.info("Configuration validated successfully")
        logger.debug(f"Base URL: {cls.BASE_URL}")
        logger.debug(f"Request timeout: {cls.REQUEST_TIMEOUT_SECONDS}s")

# Apply log level from configuration
if Config.DEBUG:
    logger.setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    # Set FastMCP debug mode via global settings
    settings.set_setting('debug', True)
else:
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    settings.set_setting('debug', False)

# Keep FastMCP log level in sync with application logging
settings.set_setting('log_level', Config.LOG_LEVEL.upper())

# Validate configuration on module load
try:
    Config.validate()
except ValueError as e:
    # Allow import to succeed but log the error
    # The error will be raised again when trying to use the server
    logger.error(f"Configuration validation failed: {e}")

# =============================================================================
# HTTP CLIENT HELPER
# =============================================================================

async def make_wordstat_request(
    endpoint: str,
    payload: Dict[str, Any],
    method: str = "POST"
) -> Dict[str, Any]:
    """
    Make an authenticated request to Yandex Wordstat API.
    
    This helper function provides robust error handling for API requests,
    including timeout management, authentication, and status code validation.
    
    Args:
        endpoint: The API endpoint path (relative to base URL)
        payload: The JSON payload to send in the request body
        method: HTTP method to use (default: "POST")
    
    Returns:
        Parsed JSON response from the API
    
    Raises:
        ToolError: If the request fails due to network issues, timeouts,
                   authentication errors, or invalid responses
    
    Examples:
        >>> result = await make_wordstat_request(
        ...     endpoint="/wordstat",
        ...     payload={"method": "get", "params": {...}}
        ... )
    """
    # Validate token is present
    if not Config.OAUTH_TOKEN:
        raise ToolError(
            "YANDEX_OAUTH_TOKEN is not configured. "
            "Please set it in your .env file or environment variables."
        )
    
    # Construct full URL
    url = f"{Config.WORDSTAT_BASE_URL}/{endpoint.lstrip('/')}" if endpoint else Config.WORDSTAT_BASE_URL
    
    # Prepare headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.OAUTH_TOKEN}",
        "Accept": "application/json"
    }
    
    logger.debug(f"Making {method} request to {url}")
    logger.debug(f"Payload: {payload}")
    
    try:
        # Create async HTTP client with timeout configuration
        async with httpx.AsyncClient(timeout=httpx.Timeout(Config.REQUEST_TIMEOUT_SECONDS)) as client:
            # Make the request
            if method.upper() == "POST":
                response = await client.post(url, json=payload, headers=headers)
            elif method.upper() == "GET":
                response = await client.get(url, params=payload, headers=headers)
            else:
                raise ToolError(f"Unsupported HTTP method: {method}")
            
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"Response data: {result}")
                    return result
                except Exception as e:
                    raise ToolError(
                        f"Failed to parse JSON response: {str(e)}\n"
                        f"Response text: {response.text[:500]}"
                    )
            
            elif response.status_code == 401:
                raise ToolError(
                    "Authentication failed. Your Yandex OAuth token may be invalid or expired.\n"
                    "Please check your YANDEX_OAUTH_TOKEN and regenerate it if necessary.\n"
                    "See README.md for instructions on obtaining a new token."
                )
            
            elif response.status_code == 403:
                raise ToolError(
                    "Access forbidden. Your OAuth token may not have the required permissions.\n"
                    "Ensure your Yandex application has the necessary scopes/permissions."
                )
            
            elif response.status_code == 429:
                raise ToolError(
                    "Rate limit exceeded. Please wait a moment and try again.\n"
                    "See README.md section on 'Quota Information' for rate limit details."
                )
            
            elif response.status_code >= 500:
                raise ToolError(
                    f"Yandex API server error (status {response.status_code}).\n"
                    f"The service may be temporarily unavailable. Please try again later.\n"
                    f"Error details: {response.text[:200]}"
                )
            
            else:
                raise ToolError(
                    f"Request failed with status {response.status_code}\n"
                    f"Response: {response.text[:500]}"
                )
    
    except httpx.TimeoutException:
        raise ToolError(
            f"Request timed out after {Config.REQUEST_TIMEOUT_SECONDS} seconds.\n"
            "The Yandex API may be slow or unreachable. Please try again.\n"
            "You can increase the timeout by setting REQUEST_TIMEOUT in your .env file."
        )
    
    except httpx.NetworkError as e:
        raise ToolError(
            f"Network error occurred: {str(e)}\n"
            "Please check your internet connection and try again."
        )
    
    except httpx.HTTPError as e:
        raise ToolError(
            f"HTTP error occurred: {str(e)}\n"
            "An unexpected HTTP error occurred while communicating with Yandex API."
        )
    
    except ToolError:
        # Re-raise ToolError as-is
        raise
    
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception("Unexpected error in make_wordstat_request")
        raise ToolError(
            f"Unexpected error occurred: {type(e).__name__}: {str(e)}\n"
            "Please check the logs for more details."
        )

# =============================================================================
# FASTMCP SERVER SETUP
# =============================================================================

# Initialize FastMCP server
mcp = FastMCP(
    name="Yandex MCP Server",
    instructions=(
        "This server provides access to Yandex services including "
        "Yandex.Wordstat for keyword research, Yandex Disk for cloud storage, "
        "and other Yandex APIs. All operations require proper authentication "
        "via OAuth token."
    ),
    version="1.0.0"
)

logger.info("FastMCP server initialized")
logger.info(f"Server name: Yandex MCP Server v1.0.0")
logger.info(f"Debug mode: {Config.DEBUG}")

# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    """
    Main entry point for the Yandex MCP Server.
    
    This function runs the FastMCP server with stdio transport,
    which is the standard mode for MCP servers to communicate
    with clients like Claude Desktop.
    """
    try:
        # Validate configuration before starting
        Config.validate()
        
        logger.info("Starting Yandex MCP Server...")
        logger.info("Transport: stdio")
        logger.info("Waiting for MCP client connection...")
        
        # Run the server with stdio transport
        # This is a blocking call that handles the MCP protocol
        mcp.run(transport="stdio")
        
    except ValueError as e:
        # Configuration validation failed
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        sys.exit(0)
    
    except Exception as e:
        logger.exception("Unexpected error occurred while running server")
        sys.exit(1)

if __name__ == "__main__":
    main()
