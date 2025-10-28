# Yandex MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with secure access to Yandex services.

## Overview

This project implements an MCP server that enables AI assistants like Claude and Gemini to interact with Yandex APIs on your behalf. The server uses OAuth 2.0 for secure authentication and communicates via the stdio transport protocol.

## Features

- **Secure OAuth 2.0 Authentication**: Safe access to Yandex services
- **MCP Protocol Implementation**: Standards-compliant server for AI assistant integration
- **Python 3.10+**: Modern Python with type hints and async support
- **Extensible Architecture**: Designed for easy addition of new Yandex service integrations

## Prerequisites

- Python 3.10 or higher
- A Yandex account with API access
- Valid Yandex OAuth token

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/amonrapmon/cto.git
   cd cto
   ```

2. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your YANDEX_OAUTH_TOKEN
   ```

4. **Run the server**:
   ```bash
   python server.py
   ```

## Configuration

The server requires a Yandex OAuth token to access Yandex APIs. See `.env.example` for configuration options, including:

- `YANDEX_OAUTH_TOKEN` (required): Your Yandex OAuth token
- Optional overrides for API endpoints, rate limiting, and logging

For detailed OAuth token setup instructions, see the [Yandex OAuth documentation](https://yandex.com/dev/oauth/).

## Project Structure

```
.
├── server.py              # Main MCP server entry point
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── .gitignore            # Git ignore rules
├── LICENSE               # GNU GPLv3 license
└── README.md             # This file
```

## Development Status

This project is currently in the bootstrap phase. The core server implementation and detailed usage documentation will be added in subsequent development iterations.

**Note**: Detailed usage guides, API documentation, and configuration instructions will be provided in future releases.

## Testing

Run the test suite:

```bash
pytest
pytest --cov  # With coverage report
```

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3). See the [LICENSE](LICENSE) file for details.

Key points about GPLv3:
- ✅ Free to use, modify, and distribute
- ✅ Source code must be disclosed when distributing
- ✅ Derivative works must use the same GPLv3 license
- ✅ Provides patent protection

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Security

⚠️ **Important**: Never commit your `.env` file or any files containing real OAuth tokens to version control. The `.gitignore` is configured to protect sensitive files.

## Resources

- [Model Context Protocol](https://modelcontextprotocol.io)
- [Yandex API Documentation](https://yandex.com/dev/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

## Support

For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/amonrapmon/cto/issues).

---

**Note**: This README provides basic project information. Comprehensive documentation including detailed setup instructions, API guides, and usage examples will be added in future development phases.
