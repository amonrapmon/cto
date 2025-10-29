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
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP, settings
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, field_validator, model_validator

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
# WORDSTAT CONSTANTS
# =============================================================================

class WordstatConstants:
    """Constants for Wordstat API including quota costs and valid values."""
    
    # Valid periods for dynamics queries
    VALID_PERIODS = ["DAILY", "WEEKLY", "MONTHLY"]
    
    # Valid region types
    VALID_REGION_TYPES = ["COUNTRY", "REGION", "CITY"]
    
    # Valid device types
    VALID_DEVICE_TYPES = ["DESKTOP", "MOBILE", "TABLET", "ALL"]
    
    # Quota costs (units per call)
    QUOTA_COSTS = {
        "get_regions_tree": 1,
        "get_top_requests": 5,
        "get_dynamics": 10,
        "get_regions_distribution": 10
    }
    
    # Default limits
    DEFAULT_TOP_REQUESTS_LIMIT = 10
    MAX_TOP_REQUESTS_LIMIT = 100
    REGIONS_DISTRIBUTION_OUTPUT_LIMIT = 20

# =============================================================================
# PYDANTIC MODELS FOR VALIDATION
# =============================================================================

class RegionTypeEnum(str, Enum):
    """Valid region types for region distribution queries."""
    COUNTRY = "COUNTRY"
    REGION = "REGION"
    CITY = "CITY"

class PeriodEnum(str, Enum):
    """Valid time periods for dynamics queries."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

class TopRequestsInput(BaseModel):
    """Input validation for get_top_requests tool."""
    phrase: str = Field(..., description="Search phrase to analyze", min_length=1)
    limit: Optional[int] = Field(
        default=WordstatConstants.DEFAULT_TOP_REQUESTS_LIMIT,
        description=f"Maximum number of results (1-{WordstatConstants.MAX_TOP_REQUESTS_LIMIT})",
        ge=1,
        le=WordstatConstants.MAX_TOP_REQUESTS_LIMIT
    )
    regions: Optional[List[int]] = Field(
        default=None,
        description="List of region IDs to filter by (optional)"
    )
    devices: Optional[List[str]] = Field(
        default=None,
        description="List of device types: DESKTOP, MOBILE, TABLET (optional)"
    )
    
    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v):
        if v is None:
            return v
        valid_devices = {device.upper() for device in WordstatConstants.VALID_DEVICE_TYPES}
        normalized_devices: List[str] = []
        for device in v:
            candidate = device.upper()
            if candidate not in valid_devices:
                raise ValueError(
                    f"Invalid device type '{device}'. "
                    f"Must be one of: {', '.join(sorted(valid_devices))}"
                )
            normalized_devices.append(candidate)
        return normalized_devices

class DynamicsInput(BaseModel):
    """Input validation for get_dynamics tool."""
    phrase: str = Field(..., description="Search phrase to analyze", min_length=1)
    period: PeriodEnum = Field(
        default=PeriodEnum.MONTHLY,
        description="Time period granularity: DAILY, WEEKLY, or MONTHLY"
    )
    from_date: Optional[str] = Field(
        default=None,
        description="Start date in YYYY-MM-DD format (optional)"
    )
    to_date: Optional[str] = Field(
        default=None,
        description="End date in YYYY-MM-DD format (optional)"
    )
    regions: Optional[List[int]] = Field(
        default=None,
        description="List of region IDs to filter by (optional)"
    )
    devices: Optional[List[str]] = Field(
        default=None,
        description="List of device types: DESKTOP, MOBILE, TABLET (optional)"
    )
    
    @field_validator('from_date', 'to_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        return v
    
    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v):
        if v is None:
            return v
        valid_devices = {device.upper() for device in WordstatConstants.VALID_DEVICE_TYPES}
        normalized_devices: List[str] = []
        for device in v:
            candidate = device.upper()
            if candidate not in valid_devices:
                raise ValueError(
                    f"Invalid device type '{device}'. "
                    f"Must be one of: {', '.join(sorted(valid_devices))}"
                )
            normalized_devices.append(candidate)
        return normalized_devices
    
    @model_validator(mode="after")
    def validate_date_range(self):
        if self.from_date and self.to_date:
            start = datetime.strptime(self.from_date, '%Y-%m-%d')
            end = datetime.strptime(self.to_date, '%Y-%m-%d')
            if start > end:
                raise ValueError("from_date must be earlier than or equal to to_date")
        return self

class RegionsDistributionInput(BaseModel):
    """Input validation for get_regions_distribution tool."""
    phrase: str = Field(..., description="Search phrase to analyze", min_length=1)
    region_type: RegionTypeEnum = Field(
        default=RegionTypeEnum.REGION,
        description="Type of regions to return: COUNTRY, REGION, or CITY"
    )
    devices: Optional[List[str]] = Field(
        default=None,
        description="List of device types: DESKTOP, MOBILE, TABLET (optional)"
    )
    
    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v):
        if v is None:
            return v
        valid_devices = {device.upper() for device in WordstatConstants.VALID_DEVICE_TYPES}
        normalized_devices: List[str] = []
        for device in v:
            candidate = device.upper()
            if candidate not in valid_devices:
                raise ValueError(
                    f"Invalid device type '{device}'. "
                    f"Must be one of: {', '.join(sorted(valid_devices))}"
                )
            normalized_devices.append(candidate)
        return normalized_devices

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
# WORDSTAT RESPONSE HELPERS
# =============================================================================

def unwrap_response(response: Any) -> Any:
    """Unwrap Wordstat API responses to extract the core payload."""
    keys = ("result", "data", "response")
    current = response
    depth = 0
    while isinstance(current, dict) and depth < 5:
        for key in keys:
            if key in current:
                current = current[key]
                break
        else:
            return current
        depth += 1
    return current


def extract_sequence(data: Any, candidate_keys: List[str]) -> List[Any]:
    """Extract a list of items from a response payload using fallback keys."""
    if isinstance(data, dict):
        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
        # Fall back to the first list value in the dict
        for value in data.values():
            if isinstance(value, list):
                return value
    elif isinstance(data, list):
        return data
    return []


def format_count(value: Any) -> str:
    """Format integer-like values with thousands separators."""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return "n/a"
    return f"{number:,}"


def format_percentage(value: Any, *, assume_fraction: Optional[bool] = None) -> str:
    """Format values as percentages, handling fraction or percent inputs."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if assume_fraction is True:
        pct = number
    elif assume_fraction is False:
        pct = number / 100.0
    else:
        pct = number if abs(number) <= 1 else number / 100.0
    return f"{pct:.2%}"


def format_decimal(value: Any, precision: int = 2) -> str:
    """Format decimal numbers with fixed precision."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{number:.{precision}f}"

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
# WORDSTAT TOOLS
# =============================================================================

@mcp.tool(
    name="get_regions_tree",
    description="Retrieve the complete Yandex.Wordstat region hierarchy.",
    tags={"wordstat", "regions"}
)
async def get_regions_tree() -> str:
    """Retrieve and format the Yandex.Wordstat region hierarchy."""
    try:
        logger.info("Calling get_regions_tree")

        result = await make_wordstat_request("v1/getRegionsTree", {}, method="GET")
        data = unwrap_response(result)

        regions = data
        if isinstance(data, dict):
            for key in ("regions", "Regions", "tree", "Tree"):
                if key in data:
                    regions = data[key]
                    break

        def count_regions(node: Any) -> int:
            if isinstance(node, dict):
                children = node.get("children") or node.get("Children") or []
                return 1 + sum(count_regions(child) for child in children)
            if isinstance(node, list):
                return sum(count_regions(item) for item in node)
            return 0

        def format_tree(node: Any, level: int = 0) -> List[str]:
            lines: List[str] = []
            indent = "  " * level
            if isinstance(node, dict):
                name = node.get("name") or node.get("Name") or "Unknown region"
                region_id = node.get("id") or node.get("GeoRegionId") or node.get("RegionId")
                id_suffix = f" (ID: {region_id})" if region_id is not None else ""
                lines.append(f"{indent}• {name}{id_suffix}")
                children = node.get("children") or node.get("Children") or []
                for child in children:
                    lines.extend(format_tree(child, level + 1))
            elif isinstance(node, list):
                for item in node:
                    lines.extend(format_tree(item, level))
            return lines

        total_regions = count_regions(regions)
        tree_lines = format_tree(regions)
        if not tree_lines:
            tree_lines = ["No regions returned by the Wordstat API."]

        output_lines = [
            "Yandex.Wordstat Regions Tree",
            "=" * 50,
            f"Total Regions: {total_regions}",
            ""
        ]
        output_lines.extend(tree_lines)

        logger.info("get_regions_tree completed successfully", extra={"total_regions": total_regions})
        return "\n".join(output_lines)

    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Error in get_regions_tree")
        raise ToolError(f"Failed to retrieve regions tree: {exc}")


@mcp.tool(
    name="get_top_requests",
    description="Fetch top related search queries for a phrase from Yandex.Wordstat.",
    tags={"wordstat", "keywords"}
)
async def get_top_requests(
    phrase: str,
    limit: int = WordstatConstants.DEFAULT_TOP_REQUESTS_LIMIT,
    regions: Optional[List[int]] = None,
    devices: Optional[List[str]] = None
) -> str:
    """Return a formatted list of top related search queries for a phrase."""
    try:
        validated = TopRequestsInput(
            phrase=phrase,
            limit=limit,
            regions=regions,
            devices=devices
        )

        logger.info(
            "Calling get_top_requests",
            extra={"phrase": validated.phrase, "limit": validated.limit}
        )

        payload: Dict[str, Any] = {
            "phrase": validated.phrase,
            "limit": validated.limit
        }
        if validated.regions:
            payload["regions"] = validated.regions
        if validated.devices:
            payload["devices"] = validated.devices

        result = await make_wordstat_request("v1/getTopRequests", payload)
        data = unwrap_response(result)
        queries = extract_sequence(
            data,
            [
                "topRequests",
                "TopRequests",
                "searchQueries",
                "SearchQueries",
                "requests",
                "Requests",
                "phrases",
                "Phrases",
            ]
        )

        header_lines = [
            f"Top Search Requests for '{validated.phrase}'",
            "=" * 50,
            f"Limit: {validated.limit}"
        ]
        if validated.regions:
            header_lines.append(f"Regions: {', '.join(map(str, validated.regions))}")
        if validated.devices:
            header_lines.append(f"Devices: {', '.join(validated.devices)}")
        header_lines.append("")

        if not queries:
            header_lines.append("No results returned by the Wordstat API.")
        else:
            for index, query in enumerate(queries[:validated.limit], start=1):
                if isinstance(query, dict):
                    query_text = (
                        query.get("phrase")
                        or query.get("Phrase")
                        or query.get("query")
                        or query.get("Query")
                        or query.get("keyword")
                        or query.get("Keyword")
                        or f"Result {index}"
                    )
                    shows_value = (
                        query.get("shows")
                        or query.get("Shows")
                        or query.get("count")
                        or query.get("Count")
                        or query.get("volume")
                        or query.get("Volume")
                    )
                    share_value = query.get("share") or query.get("Share")
                    growth_value = (
                        query.get("growth")
                        or query.get("Growth")
                        or query.get("change")
                        or query.get("Change")
                    )

                    details: List[str] = []
                    count_text = format_count(shows_value)
                    if count_text != "n/a":
                        details.append(f"{count_text} searches")
                    share_text = format_percentage(share_value)
                    if share_text != "n/a":
                        details.append(f"{share_text} share")
                    growth_text = format_percentage(growth_value)
                    if growth_text != "n/a":
                        details.append(f"Δ {growth_text}")

                    detail_suffix = f" — {', '.join(details)}" if details else ""
                    header_lines.append(f"{index}. {query_text}{detail_suffix}")
                else:
                    header_lines.append(f"{index}. {query}")

        logger.info(
            "get_top_requests completed successfully",
            extra={"results": len(queries)} if isinstance(queries, list) else None
        )
        return "\n".join(header_lines)

    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Error in get_top_requests")
        raise ToolError(f"Failed to retrieve top requests: {exc}")


@mcp.tool(
    name="get_dynamics",
    description="Analyze how search interest changes over time for a phrase.",
    tags={"wordstat", "trends"}
)
async def get_dynamics(
    phrase: str,
    period: str = "MONTHLY",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    regions: Optional[List[int]] = None,
    devices: Optional[List[str]] = None
) -> str:
    """Return a time series of search interest for a phrase."""
    try:
        validated = DynamicsInput(
            phrase=phrase,
            period=period,
            from_date=from_date,
            to_date=to_date,
            regions=regions,
            devices=devices
        )

        logger.info(
            "Calling get_dynamics",
            extra={
                "phrase": validated.phrase,
                "period": validated.period.value,
                "from_date": validated.from_date,
                "to_date": validated.to_date,
            }
        )

        payload: Dict[str, Any] = {
            "phrase": validated.phrase,
            "period": validated.period.value,
        }
        if validated.from_date:
            payload["fromDate"] = validated.from_date
        if validated.to_date:
            payload["toDate"] = validated.to_date
        if validated.regions:
            payload["regions"] = validated.regions
        if validated.devices:
            payload["devices"] = validated.devices

        result = await make_wordstat_request("v1/getDynamics", payload)
        data = unwrap_response(result)
        entries = extract_sequence(
            data,
            [
                "dynamics",
                "Dynamics",
                "items",
                "Items",
                "trend",
                "Trend",
                "data",
                "Data",
            ]
        )

        output_lines = [
            f"Search Dynamics for '{validated.phrase}'",
            "=" * 70,
            f"Period: {validated.period.value}"
        ]
        if validated.from_date:
            output_lines.append(f"From: {validated.from_date}")
        if validated.to_date:
            output_lines.append(f"To: {validated.to_date}")
        if validated.regions:
            output_lines.append(f"Regions: {', '.join(map(str, validated.regions))}")
        if validated.devices:
            output_lines.append(f"Devices: {', '.join(validated.devices)}")
        output_lines.append("")

        if not entries:
            output_lines.append("No dynamics data returned by the Wordstat API.")
        else:
            output_lines.append(f"{'Date':<15} {'Requests':>12} {'Share':>12}")
            output_lines.append("-" * 45)
            for row in entries:
                if not isinstance(row, dict):
                    continue
                date_value = (
                    row.get("date")
                    or row.get("Date")
                    or row.get("period")
                    or row.get("Period")
                    or row.get("time")
                    or row.get("Time")
                    or "Unknown"
                )
                count_value = (
                    row.get("shows")
                    or row.get("Shows")
                    or row.get("count")
                    or row.get("Count")
                )
                share_value = (
                    row.get("share")
                    or row.get("Share")
                    or row.get("sharePercent")
                    or row.get("SharePercent")
                )

                count_text = format_count(count_value)
                share_text = format_percentage(share_value)
                output_lines.append(
                    f"{str(date_value):<15} {count_text:>12} {share_text:>12}"
                )

        logger.info(
            "get_dynamics completed successfully",
            extra={"rows": len(entries)} if isinstance(entries, list) else None
        )
        return "\n".join(output_lines)

    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Error in get_dynamics")
        raise ToolError(f"Failed to retrieve dynamics data: {exc}")


@mcp.tool(
    name="get_regions_distribution",
    description="Identify where a phrase is most popular across Yandex.Wordstat regions.",
    tags={"wordstat", "regions"}
)
async def get_regions_distribution(
    phrase: str,
    region_type: str = "REGION",
    devices: Optional[List[str]] = None
) -> str:
    """Return a table of regions ranked by search interest for a phrase."""
    try:
        validated = RegionsDistributionInput(
            phrase=phrase,
            region_type=region_type,
            devices=devices
        )

        logger.info(
            "Calling get_regions_distribution",
            extra={"phrase": validated.phrase, "region_type": validated.region_type.value}
        )

        payload: Dict[str, Any] = {
            "phrase": validated.phrase,
            "regionType": validated.region_type.value,
        }
        if validated.devices:
            payload["devices"] = validated.devices

        result = await make_wordstat_request("v1/getRegionsDistribution", payload)
        data = unwrap_response(result)
        regions_data = extract_sequence(
            data,
            [
                "regionsDistribution",
                "RegionsDistribution",
                "regions",
                "Regions",
                "items",
                "Items",
                "data",
                "Data",
            ]
        )

        output_lines = [
            f"Regional Distribution for '{validated.phrase}'",
            "=" * 80,
            f"Region Type: {validated.region_type.value}"
        ]
        if validated.devices:
            output_lines.append(f"Devices: {', '.join(validated.devices)}")
        output_lines.append("")

        if not regions_data:
            output_lines.append("No regional data returned by the Wordstat API.")
        else:
            output_lines.append(
                f"{'Region ID':<12} {'Region Name':<30} {'Count':>12} {'Share':>12} {'Affinity':>10}"
            )
            output_lines.append("-" * 80)

            for item in regions_data[:WordstatConstants.REGIONS_DISTRIBUTION_OUTPUT_LIMIT]:
                if not isinstance(item, dict):
                    continue
                region_id = (
                    item.get("regionId")
                    or item.get("RegionId")
                    or item.get("GeoId")
                    or item.get("id")
                    or "N/A"
                )
                region_name = (
                    item.get("name")
                    or item.get("Name")
                    or item.get("regionName")
                    or item.get("RegionName")
                    or "Unknown"
                )
                count_value = (
                    item.get("shows")
                    or item.get("Shows")
                    or item.get("count")
                    or item.get("Count")
                )
                share_value = (
                    item.get("share")
                    or item.get("Share")
                    or item.get("sharePercent")
                    or item.get("SharePercent")
                )
                affinity_value = item.get("affinity") or item.get("Affinity")

                count_text = format_count(count_value)
                share_text = format_percentage(share_value)
                affinity_text = format_decimal(affinity_value)

                output_lines.append(
                    f"{str(region_id):<12} {region_name[:30]:<30} {count_text:>12} {share_text:>12} {affinity_text:>10}"
                )

            if isinstance(regions_data, list) and len(regions_data) > WordstatConstants.REGIONS_DISTRIBUTION_OUTPUT_LIMIT:
                output_lines.append(
                    f"\n(Showing top {WordstatConstants.REGIONS_DISTRIBUTION_OUTPUT_LIMIT} of {len(regions_data)} total regions)"
                )

        logger.info(
            "get_regions_distribution completed successfully",
            extra={"returned": len(regions_data)} if isinstance(regions_data, list) else None
        )
        return "\n".join(output_lines)

    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Error in get_regions_distribution")
        raise ToolError(f"Failed to retrieve regions distribution: {exc}")


# =============================================================================
# WORDSTAT RESOURCE
# =============================================================================

@mcp.resource(
    "wordstat://info",
    description="Documentation for Yandex.Wordstat MCP tools.",
    tags={"wordstat", "docs"}
)
def wordstat_info() -> str:
    """
    Documentation resource for Yandex.Wordstat tools.
    
    This resource provides comprehensive information about available Wordstat tools,
    their parameters, quota costs, and usage examples.
    """
    return f"""
Yandex.Wordstat MCP Tools Documentation
{'=' * 80}

OVERVIEW
--------
Yandex.Wordstat is a keyword research tool that provides insights into search
behavior on Yandex search engine. These MCP tools enable AI assistants to access
Wordstat data for market research, SEO analysis, and trend identification.

AVAILABLE TOOLS
---------------

1. get_regions_tree()
   Description: Retrieves the complete hierarchy of regions supported by Wordstat
   Parameters: None
   Quota Cost: {WordstatConstants.QUOTA_COSTS['get_regions_tree']} unit
   Returns: Formatted tree structure with region names and IDs
   
   Example:
   get_regions_tree()

2. get_top_requests(phrase, limit, regions, devices)
   Description: Get top related search queries for a phrase
   Parameters:
     - phrase (required): Search phrase to analyze
     - limit (optional): Max results to return (1-{WordstatConstants.MAX_TOP_REQUESTS_LIMIT}, default: {WordstatConstants.DEFAULT_TOP_REQUESTS_LIMIT})
     - regions (optional): List of region IDs (e.g., [213] for Moscow)
     - devices (optional): List of device types (DESKTOP, MOBILE, TABLET)
   Quota Cost: {WordstatConstants.QUOTA_COSTS['get_top_requests']} units
   Returns: Numbered list with search volumes
   
   Examples:
   get_top_requests("iphone", limit=20)
   get_top_requests("shoes", regions=[213], devices=["MOBILE"])

3. get_dynamics(phrase, period, from_date, to_date, regions, devices)
   Description: Get search trends over time for a phrase
   Parameters:
     - phrase (required): Search phrase to analyze
     - period (optional): Time granularity - {', '.join(WordstatConstants.VALID_PERIODS)} (default: MONTHLY)
     - from_date (optional): Start date in YYYY-MM-DD format
     - to_date (optional): End date in YYYY-MM-DD format
     - regions (optional): List of region IDs
     - devices (optional): List of device types
   Quota Cost: {WordstatConstants.QUOTA_COSTS['get_dynamics']} units
   Returns: Tabular data with date, request count, and market share
   
   Examples:
   get_dynamics("iphone", period="MONTHLY")
   get_dynamics("covid", period="DAILY", from_date="2023-01-01", to_date="2023-12-31")

4. get_regions_distribution(phrase, region_type, devices)
   Description: Get geographic distribution of search interest
   Parameters:
     - phrase (required): Search phrase to analyze
     - region_type (optional): Type of regions - {', '.join(WordstatConstants.VALID_REGION_TYPES)} (default: REGION)
     - devices (optional): List of device types
   Quota Cost: {WordstatConstants.QUOTA_COSTS['get_regions_distribution']} units
   Returns: Top {WordstatConstants.REGIONS_DISTRIBUTION_OUTPUT_LIMIT} regions with ID, count, share, and affinity
   
   Examples:
   get_regions_distribution("iphone")
   get_regions_distribution("skiing", region_type="CITY", devices=["MOBILE"])

VALID VALUES
------------
Periods: {', '.join(WordstatConstants.VALID_PERIODS)}
Region Types: {', '.join(WordstatConstants.VALID_REGION_TYPES)}
Device Types: {', '.join(WordstatConstants.VALID_DEVICE_TYPES)}

QUOTA COSTS
-----------
Each tool consumes API quota units. Monitor your usage to stay within limits:
- get_regions_tree: {WordstatConstants.QUOTA_COSTS['get_regions_tree']} unit per call
- get_top_requests: {WordstatConstants.QUOTA_COSTS['get_top_requests']} units per call
- get_dynamics: {WordstatConstants.QUOTA_COSTS['get_dynamics']} units per call
- get_regions_distribution: {WordstatConstants.QUOTA_COSTS['get_regions_distribution']} units per call

USAGE NOTES
-----------
1. Authentication: Requires valid YANDEX_OAUTH_TOKEN in environment
2. Rate Limits: Respect API rate limits to avoid throttling
3. Date Format: Always use YYYY-MM-DD format for dates
4. Region IDs: Use get_regions_tree() to find valid region IDs
5. Filters: Optional filters (regions, devices) help narrow results
6. Output Limits: get_regions_distribution is capped at {WordstatConstants.REGIONS_DISTRIBUTION_OUTPUT_LIMIT} regions

ERROR HANDLING
--------------
All tools provide detailed error messages including:
- Authentication errors (401/403)
- Rate limit errors (429)
- Invalid parameter errors
- Network connectivity issues
- API server errors (5xx)

For more information, see:
- README.md: Setup and authentication guide
- .env.example: Configuration options
- Yandex Wordstat API: https://yandex.com/dev/direct/doc/dg/concepts/about.html

{'=' * 80}
"""

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
