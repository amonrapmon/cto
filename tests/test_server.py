"""
Comprehensive test suite for Yandex MCP Server

Tests cover:
- Server bootstrap and configuration validation
- Tool and resource registration
- HTTP request mocking for happy-path scenarios
- Payload validation against Yandex Wordstat API expectations
- Output format verification (counts, dates, etc.)
- Error handling (non-200 responses, timeouts, network errors)
"""

import os
import sys
import json
import pytest
import respx
import httpx
from httpx import Response
from fastmcp.exceptions import ToolError

# Configure environment before importing server
os.environ.setdefault('YANDEX_OAUTH_TOKEN', 'test-token-for-testing')


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv('YANDEX_OAUTH_TOKEN', 'test-token-for-testing')
    monkeypatch.setenv('LOG_LEVEL', 'ERROR')  # Reduce log noise during tests


@pytest.fixture
def mock_server():
    """Import and return the server module with a fresh state."""
    # Clear cached module to ensure fresh import
    if 'src.server' in sys.modules:
        del sys.modules['src.server']
    
    import src.server as server
    return server


# =============================================================================
# CONFIGURATION AND BOOTSTRAP TESTS
# =============================================================================

def test_server_bootstrap_without_token_raises_error(monkeypatch):
    """
    Verify that server bootstrap without YANDEX_OAUTH_TOKEN raises a clear error.
    This tests the configuration validation on module load.
    """
    # Clear the token
    monkeypatch.delenv('YANDEX_OAUTH_TOKEN', raising=False)
    
    # Clear cached module
    if 'src.server' in sys.modules:
        del sys.modules['src.server']
    
    # Import should succeed but Config.validate() should fail
    import src.server as server
    
    with pytest.raises(ValueError) as exc_info:
        server.Config.validate()
    
    error_message = str(exc_info.value)
    assert "YANDEX_OAUTH_TOKEN is required but not set" in error_message


def test_config_validation_with_token(mock_server):
    """Verify that configuration validation succeeds with a valid token."""
    # Should not raise any exception
    mock_server.Config.validate()
    assert mock_server.Config.OAUTH_TOKEN == 'test-token-for-testing'


@pytest.mark.asyncio
async def test_fastmcp_registry_exposes_four_tools(mock_server):
    """
    Verify that the FastMCP registry exposes exactly four expected tools.
    Tests tool registration and availability through the MCP server.
    """
    tools = await mock_server.mcp.get_tools()
    
    # Verify we have exactly 4 tools
    assert len(tools) == 4, f"Expected 4 tools, found {len(tools)}"
    
    # Verify the expected tool names
    expected_tools = {
        'get_keyword_suggestions',
        'get_search_volume',
        'get_keyword_stats',
        'get_related_keywords'
    }
    
    tool_names = set(tools.keys())
    assert tool_names == expected_tools, f"Tool names mismatch: {tool_names} != {expected_tools}"
    
    # Verify each tool has proper metadata
    for tool_name, tool in tools.items():
        assert tool.name == tool_name
        assert tool.description is not None and len(tool.description) > 0
        assert tool.enabled is True


@pytest.mark.asyncio
async def test_fastmcp_registry_exposes_info_resource(mock_server):
    """
    Verify that the FastMCP registry exposes the info resource.
    Tests resource registration and availability.
    """
    resources = await mock_server.mcp.get_resources()
    
    # Verify we have the info resource
    assert len(resources) >= 1, "Expected at least 1 resource"
    assert 'wordstat://info' in resources, "Info resource not found"
    
    info_resource = resources['wordstat://info']
    assert info_resource.name == 'get_wordstat_info'
    assert info_resource.description is not None
    assert 'information' in info_resource.description.lower()


# =============================================================================
# HAPPY PATH - TOOL EXECUTION WITH MOCKED RESPONSES
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_get_keyword_suggestions_happy_path(mock_server):
    """
    Test get_keyword_suggestions with mocked successful API response.
    Verifies payload structure and output formatting.
    """
    # Mock the API response
    mock_response = {
        'result': {
            'SearchedWith': [
                {'Keyword': 'python tutorial', 'Shows': 12500},
                {'Keyword': 'python programming', 'Shows': 10200},
                {'Keyword': 'python course', 'Shows': 8900}
            ]
        }
    }
    
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    # Call the tool
    result = await mock_server.get_keyword_suggestions.fn(keywords=['python'])
    
    # Verify the request was made
    assert route.called
    
    # Verify the payload structure
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload['method'] == 'get'
    assert 'params' in request_payload
    assert request_payload['params']['Keywords'] == ['python']
    assert request_payload['params']['RegionIds'] == [225]
    
    # Verify output formatting includes required fields
    assert 'python tutorial' in result
    assert '12,500' in result  # Count with formatting
    assert 'monthly searches' in result
    assert 'Keyword suggestions for: python' in result


@pytest.mark.asyncio
@respx.mock
async def test_get_search_volume_happy_path(mock_server):
    """
    Test get_search_volume with mocked successful API response.
    Verifies volume data and formatting.
    """
    mock_response = {
        'result': {
            'SearchedWith': [
                {'Keyword': 'machine learning', 'Shows': 45000, 'Dynamics': [100, 110, 120]},
                {'Keyword': 'deep learning', 'Shows': 32000}
            ]
        }
    }
    
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_search_volume.fn(keywords=['machine learning', 'deep learning'])
    
    # Verify the request
    assert route.called
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload['params']['Keywords'] == ['machine learning', 'deep learning']
    
    # Verify output includes counts and proper formatting
    assert 'Search Volume Data' in result
    assert 'machine learning' in result
    assert '45,000' in result  # Formatted count
    assert 'Monthly searches' in result
    assert 'Trend data available' in result  # Because Dynamics is present


@pytest.mark.asyncio
@respx.mock
async def test_get_keyword_stats_happy_path(mock_server):
    """
    Test get_keyword_stats with mocked response including dates and statistics.
    Verifies detailed statistics output formatting.
    """
    mock_response = {
        'result': {
            'SearchedWith': [
                {'Keyword': 'python', 'Shows': 50000},
                {'Keyword': 'python tutorial', 'Shows': 12500}
            ],
            'SearchedAlso': [
                {'Keyword': 'javascript', 'Shows': 40000},
                {'Keyword': 'java', 'Shows': 35000}
            ]
        }
    }
    
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_keyword_stats.fn(keyword='python', start_date='2024-01-01', end_date='2024-12-31'
    )
    
    # Verify the request includes date parameters
    assert route.called
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload['params']['Keywords'] == ['python']
    assert request_payload['params']['StartDate'] == '2024-01-01'
    assert request_payload['params']['EndDate'] == '2024-12-31'
    
    # Verify output includes required fields
    assert 'Detailed Statistics for: python' in result
    assert 'Related Keywords:' in result
    assert 'Users Also Searched:' in result
    assert '50,000' in result  # Formatted counts
    assert 'Period: 2024-01-01 to 2024-12-31' in result  # Date range


@pytest.mark.asyncio
@respx.mock
async def test_get_related_keywords_happy_path(mock_server):
    """
    Test get_related_keywords with mocked response.
    Verifies related keywords output with counts and relevance.
    """
    mock_response = {
        'result': {
            'SearchedAlso': [
                {'Keyword': 'javascript tutorial', 'Shows': 25000},
                {'Keyword': 'javascript course', 'Shows': 18000},
                {'Keyword': 'javascript basics', 'Shows': 15000}
            ]
        }
    }
    
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_related_keywords.fn(keyword='javascript', max_results=10)
    
    # Verify the request
    assert route.called
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload['params']['Keywords'] == ['javascript']
    
    # Verify output includes counts and proper formatting
    assert 'Related Keywords for: javascript' in result
    assert 'Related searches:' in result
    assert 'javascript tutorial' in result
    assert '25,000' in result  # Formatted count
    assert 'Monthly searches:' in result
    assert 'Total related keywords found: 3' in result


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_401_authentication_error(mock_server):
    """
    Test that tools properly handle 401 authentication errors.
    Verifies informative exception messages.
    """
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(401, text='Unauthorized')
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_keyword_suggestions.fn(keywords=['test'])
    
    error_message = str(exc_info.value)
    assert 'Authentication failed' in error_message
    assert 'OAuth token' in error_message
    assert 'invalid or expired' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_403_forbidden_error(mock_server):
    """
    Test that tools properly handle 403 forbidden errors.
    """
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(403, text='Forbidden')
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_search_volume.fn(keywords=['test'])
    
    error_message = str(exc_info.value)
    assert 'Access forbidden' in error_message
    assert 'permissions' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_429_rate_limit_error(mock_server):
    """
    Test that tools properly handle 429 rate limit errors.
    """
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(429, text='Too Many Requests')
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_keyword_stats.fn(keyword='test')
    
    error_message = str(exc_info.value)
    assert 'Rate limit exceeded' in error_message
    assert 'Quota Information' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_500_server_error(mock_server):
    """
    Test that tools properly handle 5xx server errors.
    """
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(500, text='Internal Server Error')
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_related_keywords.fn(keyword='test')
    
    error_message = str(exc_info.value)
    assert 'server error' in error_message.lower()
    assert '500' in error_message
    assert 'temporarily unavailable' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_timeout_error(mock_server):
    """
    Test that tools properly handle timeout errors.
    Verifies informative timeout exception messages.
    """
    def timeout_side_effect(request):
        raise httpx.TimeoutException("Request timed out")
    
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        side_effect=timeout_side_effect
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_keyword_suggestions.fn(keywords=['test'])
    
    error_message = str(exc_info.value)
    assert 'timed out' in error_message.lower()
    assert str(mock_server.Config.REQUEST_TIMEOUT_SECONDS) in error_message
    assert 'REQUEST_TIMEOUT' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_network_error(mock_server):
    """
    Test that tools properly handle network errors.
    """
    def network_error_side_effect(request):
        raise httpx.NetworkError("Network unreachable")
    
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        side_effect=network_error_side_effect
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_search_volume.fn(keywords=['test'])
    
    error_message = str(exc_info.value)
    assert 'Network error' in error_message
    assert 'internet connection' in error_message


@pytest.mark.asyncio
@respx.mock
async def test_tool_handles_invalid_json_response(mock_server):
    """
    Test that tools properly handle invalid JSON responses.
    """
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, text='Not valid JSON')
    )
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.get_keyword_stats.fn(keyword='test')
    
    error_message = str(exc_info.value)
    assert 'parse JSON' in error_message


@pytest.mark.asyncio
async def test_make_wordstat_request_requires_token(mock_server, monkeypatch):
    """
    Test that make_wordstat_request validates token presence.
    """
    # Temporarily clear the token
    monkeypatch.setattr(mock_server.Config, 'OAUTH_TOKEN', '')
    
    with pytest.raises(ToolError) as exc_info:
        await mock_server.make_wordstat_request('', {'test': 'payload'})
    
    error_message = str(exc_info.value)
    assert 'YANDEX_OAUTH_TOKEN is not configured' in error_message


# =============================================================================
# PAYLOAD VALIDATION TESTS
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_keyword_suggestions_payload_structure(mock_server):
    """
    Test that get_keyword_suggestions sends correct payload structure
    matching Yandex Wordstat API expectations.
    """
    mock_response = {'result': {'SearchedWith': []}}
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    await mock_server.get_keyword_suggestions.fn(keywords=['keyword1', 'keyword2'], region_ids=[213, 2])
    
    # Verify payload structure
    request_payload = json.loads(route.calls[0].request.content)
    assert 'method' in request_payload
    assert request_payload['method'] == 'get'
    assert 'params' in request_payload
    assert 'Keywords' in request_payload['params']
    assert 'RegionIds' in request_payload['params']
    assert request_payload['params']['Keywords'] == ['keyword1', 'keyword2']
    assert request_payload['params']['RegionIds'] == [213, 2]


@pytest.mark.asyncio
@respx.mock
async def test_request_headers_include_authentication(mock_server):
    """
    Test that requests include proper authentication headers.
    """
    route = respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json={'result': {'SearchedWith': []}})
    )
    
    await mock_server.get_keyword_suggestions.fn(keywords=['test'])
    
    # Verify headers
    request = route.calls[0].request
    assert 'Authorization' in request.headers
    assert request.headers['Authorization'] == 'Bearer test-token-for-testing'
    assert request.headers['Content-Type'] == 'application/json'
    assert request.headers['Accept'] == 'application/json'


# =============================================================================
# OUTPUT FORMAT VALIDATION TESTS
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_output_includes_formatted_counts(mock_server):
    """
    Verify that tool outputs include properly formatted counts (with commas).
    """
    mock_response = {
        'result': {
            'SearchedWith': [
                {'Keyword': 'test', 'Shows': 1234567}
            ]
        }
    }
    
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_keyword_suggestions.fn(keywords=['test'])
    
    # Verify count is formatted with commas
    assert '1,234,567' in result


@pytest.mark.asyncio
@respx.mock
async def test_output_includes_dates_when_provided(mock_server):
    """
    Verify that outputs include date information when provided.
    """
    mock_response = {
        'result': {
            'SearchedWith': [{'Keyword': 'test', 'Shows': 100}]
        }
    }
    
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_keyword_stats.fn(keyword='test', start_date='2024-01-01', end_date='2024-12-31'
    )
    
    # Verify dates appear in output
    assert '2024-01-01' in result
    assert '2024-12-31' in result


@pytest.mark.asyncio
@respx.mock
async def test_empty_results_handled_gracefully(mock_server):
    """
    Test that tools handle empty result sets gracefully.
    """
    mock_response = {'result': {'SearchedWith': []}}
    
    respx.post(mock_server.Config.WORDSTAT_BASE_URL).mock(
        return_value=Response(200, json=mock_response)
    )
    
    result = await mock_server.get_keyword_suggestions.fn(keywords=['nonexistent'])
    
    # Should not crash, should return informative message
    assert result == 'No suggestions found'


# =============================================================================
# RESOURCE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_info_resource_returns_documentation(mock_server):
    """
    Test that the info resource returns comprehensive documentation.
    """
    result = await mock_server.get_wordstat_info.fn()
    
    # Verify comprehensive documentation
    assert 'Yandex Wordstat MCP Server Information' in result
    assert 'get_keyword_suggestions' in result
    assert 'get_search_volume' in result
    assert 'get_keyword_stats' in result
    assert 'get_related_keywords' in result
    assert 'Region IDs' in result
    assert 'API Limits' in result
    assert 'Authentication' in result
    assert '225' in result  # Russia region ID
