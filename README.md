# Yandex MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with access to Yandex services through standardized tools and resources.

## Overview

This MCP server enables AI assistants like Claude and Gemini to interact with Yandex APIs on your behalf. It implements the [Model Context Protocol](https://modelcontextprotocol.io) to expose Yandex service capabilities as tools that can be called by compatible AI clients.

The server runs as a stdio-based process that communicates with MCP clients using JSON-RPC 2.0 messages over standard input/output streams.

## Features

- **Secure Authentication**: Uses OAuth 2.0 tokens for secure Yandex API access
- **Stdio Transport**: Lightweight communication via standard input/output
- **Multiple Tools**: Comprehensive set of tools for various Yandex services
- **Rate Limiting**: Built-in quota management and rate limiting
- **Error Handling**: Robust error handling with detailed logging

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher) or **Python** (v3.10 or higher) - depending on your implementation
- **npm** or **pip** - for dependency management
- A Yandex account with API access

## Obtaining a Yandex OAuth Token

To use this MCP server, you need a valid Yandex OAuth token:

### Step 1: Create a Yandex OAuth Application

1. Visit the [Yandex OAuth Application Registration](https://oauth.yandex.com/) page
2. Sign in with your Yandex account
3. Click "Register new client" or "Create application"
4. Fill in the application details:
   - **Application name**: Choose a descriptive name (e.g., "MCP Server")
   - **Platforms**: Select the appropriate platform(s)
   - **Redirect URI**: For personal use, you can use `https://oauth.yandex.com/verification_code`
5. Select the required permissions/scopes based on the services you want to access:
   - `cloud-api:disk.read` - Read access to Yandex Disk
   - `cloud-api:disk.write` - Write access to Yandex Disk
   - Additional scopes as needed for other services
6. Click "Create application" and note your **Client ID** and **Client Secret**

### Step 2: Generate OAuth Token

1. Construct the authorization URL:
   ```
   https://oauth.yandex.com/authorize?response_type=token&client_id=YOUR_CLIENT_ID
   ```
   Replace `YOUR_CLIENT_ID` with your actual Client ID.

2. Open this URL in your browser
3. Grant the requested permissions
4. You'll be redirected to a page with your access token in the URL fragment
5. Copy the `access_token` value - this is your OAuth token

### Step 3: (Optional) Use OAuth 2.0 Authorization Code Flow

For production use or long-lived tokens, implement the full OAuth 2.0 flow:

```bash
# Authorization endpoint
https://oauth.yandex.com/authorize?response_type=code&client_id=YOUR_CLIENT_ID

# Token exchange endpoint
POST https://oauth.yandex.com/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=AUTHORIZATION_CODE&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET
```

Refer to the [Yandex OAuth Documentation](https://yandex.com/dev/oauth/) for detailed information.

## Installation

### Clone the Repository

```bash
git clone https://github.com/amonrapmon/cto.git
cd cto
```

### Install Dependencies

For Node.js:
```bash
npm install
```

For Python:
```bash
pip install -r requirements.txt
# or with a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Build (if applicable)

```bash
npm run build
# or
python -m build
```

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Yandex OAuth token:
   ```env
   YANDEX_OAUTH_TOKEN=your_token_here
   ```

3. **Important**: Never commit your `.env` file or real tokens to version control. The `.gitignore` file is configured to exclude sensitive files.

For more information on environment configuration, see `.env.example` which includes references to the sample MCP client configurations (`claude_desktop_config.json` and `gemini_settings.json`).

## Running the MCP Server

The server runs using stdio transport, which means it communicates through standard input/output streams. It's not meant to be run directly by users, but rather invoked by MCP clients like Claude Desktop or Gemini.

### Standalone Testing (Development)

For development and testing purposes, you can run the server directly:

**Node.js:**
```bash
npm start
# or
node dist/index.js
```

**Python:**
```bash
python -m mcp_yandex
# or
python src/main.py
```

The server will wait for JSON-RPC messages on stdin and respond on stdout.

### Integration with MCP Clients

To use the server with an MCP client, configure the client to launch the server as a subprocess. See the [Configuration](#configuration) section below.

## Configuration

### Claude Desktop Integration

Create or edit your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

See [`claude_desktop_config.json`](./claude_desktop_config.json) for a complete sample configuration.

Example snippet:
```json
{
  "mcpServers": {
    "yandex": {
      "command": "node",
      "args": ["/absolute/path/to/cto/dist/index.js"],
      "env": {
        "YANDEX_OAUTH_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Gemini Integration

For Gemini integration, configure the MCP settings in your Gemini client:

See [`gemini_settings.json`](./gemini_settings.json) for a complete sample configuration.

Example snippet:
```json
{
  "mcp_servers": {
    "yandex": {
      "type": "stdio",
      "command": ["node", "/absolute/path/to/cto/dist/index.js"],
      "env": {
        "YANDEX_OAUTH_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Available Tools

The following tools are available through this MCP server:

### Yandex Disk Tools

- **`disk_list_files`**: List files and folders in Yandex Disk
  - Parameters: `path` (optional), `limit` (optional), `offset` (optional)
  - Returns: List of files with metadata (name, size, type, modified date)

- **`disk_read_file`**: Read file contents from Yandex Disk
  - Parameters: `path` (required)
  - Returns: File contents as text or base64-encoded binary

- **`disk_write_file`**: Write or update a file in Yandex Disk
  - Parameters: `path` (required), `content` (required), `overwrite` (optional)
  - Returns: File metadata after write

- **`disk_delete_file`**: Delete a file or folder from Yandex Disk
  - Parameters: `path` (required), `permanently` (optional)
  - Returns: Success confirmation

- **`disk_create_folder`**: Create a new folder in Yandex Disk
  - Parameters: `path` (required)
  - Returns: Folder metadata

- **`disk_get_download_link`**: Generate a public download link for a file
  - Parameters: `path` (required)
  - Returns: Download URL

### Additional Yandex Service Tools

(Extend this section as you add more tools for Yandex Translate, Yandex Maps, etc.)

## Usage Examples

### Example 1: List Files in Yandex Disk

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "disk_list_files",
    "arguments": {
      "path": "/Documents",
      "limit": 10
    }
  }
}
```

### Example 2: Read a File

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "disk_read_file",
    "arguments": {
      "path": "/Documents/notes.txt"
    }
  }
}
```

### Example 3: Create a Folder

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "disk_create_folder",
    "arguments": {
      "path": "/Projects/NewProject"
    }
  }
}
```

When using Claude or Gemini, you can simply ask in natural language:
- "Can you list the files in my Yandex Disk Documents folder?"
- "Read the contents of notes.txt from my Yandex Disk"
- "Create a folder called 'NewProject' in my Yandex Disk"

## Quota Information

Yandex APIs have rate limits and quotas. Be aware of the following:

- **Rate Limits**: Most Yandex APIs limit requests to a certain number per second/minute
- **Daily Quotas**: Some services have daily request limits
- **Storage Quotas**: Yandex Disk has storage limits based on your account type

The server implements automatic retry with exponential backoff for rate-limited requests. If you encounter quota errors:

1. Check your Yandex account quota status
2. Reduce the frequency of requests
3. Consider upgrading your Yandex account for higher limits

For specific quota limits, refer to the [Yandex API Documentation](https://yandex.com/dev/).

## Testing

### Running Tests

**Node.js:**
```bash
npm test
npm run test:watch  # Watch mode for development
npm run test:coverage  # Generate coverage report
```

**Python:**
```bash
pytest
pytest --cov=mcp_yandex  # With coverage
pytest -v  # Verbose output
```

### Manual Testing

You can test the server manually using the MCP Inspector tool:

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

This will open a web interface where you can:
- View available tools
- Call tools with custom parameters
- Inspect responses and errors
- Monitor server logs

### Integration Testing

Test the server with a real MCP client:

1. Configure the server in Claude Desktop (see [Configuration](#configuration))
2. Start Claude Desktop
3. In a conversation, try commands like:
   - "List my Yandex Disk files"
   - "Read the file at path /test.txt from Yandex Disk"
4. Verify the responses are correct

## Troubleshooting

### Common Issues

**Issue**: "Invalid OAuth token" or "Authentication failed"
- **Solution**: Verify your token is correct and hasn't expired. Regenerate if necessary.

**Issue**: "Permission denied" errors
- **Solution**: Ensure your OAuth application has the required scopes/permissions.

**Issue**: Server not appearing in Claude Desktop
- **Solution**: Check the configuration file path and JSON syntax. Restart Claude Desktop.

**Issue**: "Rate limit exceeded" errors
- **Solution**: Wait before retrying. Implement exponential backoff in your application.

**Issue**: Server crashes or doesn't start
- **Solution**: Check logs for error messages. Verify all dependencies are installed.

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Node.js
DEBUG=mcp:* npm start

# Python
LOG_LEVEL=DEBUG python -m mcp_yandex
```

### Logs Location

- **Claude Desktop logs**: Check Claude's log directory
- **Server logs**: Usually written to stdout/stderr (captured by the MCP client)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Coding standards and style guidelines
- Running tests and quality checks
- Submitting pull requests
- Reporting bugs and requesting features

## Security

- **Never commit tokens or credentials** to version control
- Store sensitive data in `.env` files (which are git-ignored)
- Rotate your OAuth tokens periodically
- Use environment-specific tokens (dev, staging, production)
- Review the security guidelines in [CONTRIBUTING.md](./CONTRIBUTING.md)

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3) - see the [LICENSE](./LICENSE) file for full details.

The GPLv3 license ensures that this software remains free and open source. Key points:

- ✅ Free to use, modify, and distribute
- ✅ Must disclose source code when distributing
- ✅ Must use the same GPLv3 license for derivative works
- ✅ Provides patent protection

For more information about GPLv3, visit: https://www.gnu.org/licenses/gpl-3.0.en.html

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [Yandex API Documentation](https://yandex.com/dev/)
- [Yandex OAuth Documentation](https://yandex.com/dev/oauth/)
- [Yandex Disk API](https://yandex.com/dev/disk/)
- [Claude Desktop MCP Setup](https://docs.anthropic.com/claude/docs/mcp)
- [MCP Specification](https://spec.modelcontextprotocol.io/)

## Quick Start

Get up and running in under 5 minutes:

```bash
# 1. Clone and install
git clone https://github.com/amonrapmon/cto.git
cd cto
npm install  # or: pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env and add your YANDEX_OAUTH_TOKEN

# 3. Build (if needed)
npm run build  # or: python -m build

# 4. Test the server
npx @modelcontextprotocol/inspector node dist/index.js

# 5. Configure your MCP client (Claude/Gemini)
# See claude_desktop_config.json or gemini_settings.json for examples

# 6. Start using it!
# Open Claude Desktop and ask: "List my Yandex Disk files"
```

## Support

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/amonrapmon/cto/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/amonrapmon/cto/discussions)
- **Documentation**: Check this README and [CONTRIBUTING.md](./CONTRIBUTING.md)

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history and release notes (coming soon).

---

**Built with ❤️ for the MCP community**
