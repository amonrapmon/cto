# Contributing to Yandex MCP Server

Thank you for your interest in contributing to this project! We welcome contributions from the community and appreciate your help in making this MCP server better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [Security Guidelines](#security-guidelines)
- [License](#license)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment:

- **Be respectful**: Treat all contributors with respect and courtesy
- **Be constructive**: Provide helpful feedback and suggestions
- **Be collaborative**: Work together to solve problems
- **Be patient**: Remember that everyone has different skill levels and backgrounds
- **Be professional**: Keep discussions focused and on-topic

## Getting Started

1. **Fork the repository** to your GitHub account
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cto.git
   cd cto
   ```
3. **Add upstream remote** to stay synced with the main repository:
   ```bash
   git remote add upstream https://github.com/amonrapmon/cto.git
   ```
4. **Create a feature branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment Setup

### Prerequisites

Ensure you have the following installed:

- **Node.js** v18+ or **Python** 3.10+ (depending on implementation)
- **npm** v9+ or **pip** 23+
- **Git** 2.30+
- A code editor (VS Code, WebStorm, PyCharm, etc.)

### Initial Setup

#### For Node.js Implementation:

```bash
# Install dependencies
npm install

# Install development dependencies
npm install --save-dev

# Build the project
npm run build

# Run in development mode with hot reload
npm run dev

# Run linter
npm run lint

# Fix linting issues automatically
npm run lint:fix

# Format code
npm run format

# Type check (if using TypeScript)
npm run type-check
```

#### For Python Implementation:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run linter
pylint src/

# Format code with black
black src/

# Type check with mypy
mypy src/

# Sort imports
isort src/
```

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Add your development credentials:
   ```env
   YANDEX_OAUTH_TOKEN=your_dev_token_here
   LOG_LEVEL=debug
   NODE_ENV=development  # or PYTHON_ENV=development
   ```

3. **Never commit your `.env` file** - it's in `.gitignore` for security

## Coding Standards

### General Guidelines

- **Write clear, readable code** - Code is read more often than it's written
- **Follow the existing style** - Maintain consistency with the codebase
- **Keep functions small** - Each function should do one thing well
- **Use meaningful names** - Variables and functions should be self-documenting
- **Comment complex logic** - Explain why, not what
- **Avoid premature optimization** - Make it work, then make it fast
- **Handle errors gracefully** - Always provide helpful error messages

### JavaScript/TypeScript Standards

Follow the project's ESLint configuration:

- **Indentation**: 2 spaces (no tabs)
- **Quotes**: Single quotes for strings (except in JSON)
- **Semicolons**: Required
- **Line length**: Maximum 100 characters
- **Naming conventions**:
  - `camelCase` for variables and functions
  - `PascalCase` for classes and types
  - `UPPER_SNAKE_CASE` for constants
- **ES6+ features**: Use modern JavaScript features (async/await, arrow functions, etc.)
- **Type safety**: Use TypeScript types and interfaces where applicable

Example:
```typescript
// Good
const fetchDiskFiles = async (path: string): Promise<DiskFile[]> => {
  try {
    const response = await yandexApi.getDiskFiles(path);
    return response.items;
  } catch (error) {
    logger.error('Failed to fetch disk files', { path, error });
    throw new DiskApiError('Unable to list files', error);
  }
};

// Avoid
function get_files(p) {
  var res = yandexApi.getDiskFiles(p)
  return res.items
}
```

### Python Standards

Follow PEP 8 and the project's pylint configuration:

- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 100 characters
- **Naming conventions**:
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- **Type hints**: Use type annotations for function signatures
- **Docstrings**: Use Google-style or NumPy-style docstrings
- **Imports**: Group and sort imports (stdlib, third-party, local)

Example:
```python
# Good
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

async def fetch_disk_files(path: str, limit: Optional[int] = None) -> List[DiskFile]:
    """
    Fetch files from Yandex Disk.
    
    Args:
        path: The path to list files from
        limit: Maximum number of files to return
        
    Returns:
        List of DiskFile objects
        
    Raises:
        DiskApiError: If the API request fails
    """
    try:
        response = await yandex_api.get_disk_files(path, limit=limit)
        return response.items
    except Exception as e:
        logger.error(f"Failed to fetch disk files: {path}", exc_info=True)
        raise DiskApiError("Unable to list files") from e
```

### MCP Protocol Standards

When implementing MCP tools and resources:

- **Follow the MCP specification**: Adhere to [MCP spec](https://spec.modelcontextprotocol.io/)
- **Provide clear tool descriptions**: Help AI assistants understand what tools do
- **Use JSON Schema**: Define parameter schemas for all tools
- **Handle errors properly**: Return appropriate MCP error responses
- **Log interactions**: Log tool calls for debugging and monitoring
- **Validate inputs**: Always validate tool parameters before processing

Example:
```typescript
{
  name: 'disk_read_file',
  description: 'Read the contents of a file from Yandex Disk',
  inputSchema: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'The full path to the file in Yandex Disk (e.g., /Documents/file.txt)'
      },
      encoding: {
        type: 'string',
        enum: ['utf-8', 'base64'],
        description: 'Encoding for the file content',
        default: 'utf-8'
      }
    },
    required: ['path']
  }
}
```

## Testing Requirements

All contributions must include appropriate tests. We aim for high test coverage to ensure reliability.

### Writing Tests

#### Node.js (Jest/Vitest):

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- path/to/test.spec.ts
```

Example test:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DiskService } from '../src/services/disk';

describe('DiskService', () => {
  let diskService: DiskService;
  
  beforeEach(() => {
    diskService = new DiskService('mock-token');
  });
  
  it('should list files in a directory', async () => {
    const files = await diskService.listFiles('/Documents');
    expect(files).toBeInstanceOf(Array);
    expect(files.length).toBeGreaterThan(0);
  });
  
  it('should handle API errors gracefully', async () => {
    await expect(
      diskService.listFiles('/nonexistent')
    ).rejects.toThrow('Directory not found');
  });
});
```

#### Python (pytest):

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_yandex --cov-report=html

# Run specific test
pytest tests/test_disk.py::test_list_files

# Run in verbose mode
pytest -v
```

Example test:
```python
import pytest
from mcp_yandex.services.disk import DiskService

@pytest.fixture
def disk_service():
    return DiskService(token="mock-token")

def test_list_files(disk_service):
    """Test that list_files returns a list of files."""
    files = disk_service.list_files("/Documents")
    assert isinstance(files, list)
    assert len(files) > 0

def test_api_error_handling(disk_service):
    """Test that API errors are handled gracefully."""
    with pytest.raises(DiskApiError, match="Directory not found"):
        disk_service.list_files("/nonexistent")
```

### Test Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% coverage for authentication and data handling
- **Edge cases**: Include tests for error conditions and boundary cases
- **Integration tests**: Test MCP protocol interactions end-to-end

### Manual Testing

Before submitting a PR:

1. **Test with MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector node dist/index.js
   ```

2. **Test with Claude Desktop**: Configure and test all tools

3. **Test error scenarios**: Verify error handling with invalid inputs

4. **Test with real Yandex API**: Use a test account if possible

## Submitting Changes

### Commit Message Guidelines

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(disk): add support for folder creation

Implement disk_create_folder tool to allow AI assistants to create
folders in Yandex Disk. Includes validation and error handling.

Closes #42
```

```
fix(auth): handle expired OAuth tokens gracefully

Previously, expired tokens would cause the server to crash. Now we
catch the error and return a helpful message to refresh the token.

Fixes #38
```

### Preparing Your Pull Request

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**:
   ```bash
   npm run lint
   npm test
   npm run type-check
   # or for Python:
   black src/
   pylint src/
   pytest
   mypy src/
   ```

3. **Update documentation** if needed (README, comments, etc.)

4. **Test thoroughly** - both automated and manual tests

5. **Commit your changes** with clear commit messages

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Pull Request Process

1. **Create a Pull Request** from your fork to the main repository

2. **Fill out the PR template** with:
   - Description of changes
   - Related issue numbers
   - Testing performed
   - Screenshots/examples (if applicable)
   - Checklist completion

3. **Wait for review** - Maintainers will review your PR and may request changes

4. **Address feedback** - Make requested changes and push updates

5. **Approval and merge** - Once approved, a maintainer will merge your PR

### PR Checklist

- [ ] Code follows the project's coding standards
- [ ] All tests pass (`npm test` or `pytest`)
- [ ] Linting passes (`npm run lint` or `pylint src/`)
- [ ] Type checking passes (if applicable)
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated (README, comments, etc.)
- [ ] Commit messages follow conventional commits format
- [ ] Branch is up-to-date with main
- [ ] No sensitive data (tokens, passwords) in commits

## Reporting Bugs

Found a bug? Please create an issue with:

1. **Clear title** describing the bug
2. **Steps to reproduce** the issue
3. **Expected behavior** vs **actual behavior**
4. **Environment details** (OS, Node/Python version, etc.)
5. **Error messages and logs** (sanitize any sensitive data)
6. **Screenshots** if applicable

Use the bug report template in GitHub Issues.

## Requesting Features

Have an idea for a new feature?

1. **Check existing issues** to avoid duplicates
2. **Create a feature request** with:
   - Clear description of the feature
   - Use cases and benefits
   - Proposed implementation (if you have ideas)
   - Willingness to contribute (if applicable)

Use the feature request template in GitHub Issues.

## Security Guidelines

### Handling Sensitive Data

- **Never commit tokens, passwords, or credentials** to the repository
- **Use environment variables** for all sensitive configuration
- **Sanitize logs** - don't log tokens or personal data
- **Use `.gitignore`** to exclude sensitive files
- **Review diffs** before committing to ensure no secrets are included

### Security Best Practices

- **Validate all inputs** from MCP clients
- **Sanitize file paths** to prevent directory traversal attacks
- **Implement rate limiting** to prevent abuse
- **Use HTTPS** for all API calls
- **Keep dependencies updated** to patch vulnerabilities
- **Follow principle of least privilege** for OAuth scopes

### Reporting Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead:
1. Email the maintainers directly (see repository for contact info)
2. Provide detailed information about the vulnerability
3. Allow time for a patch before public disclosure
4. We'll acknowledge and work with you on a fix

## License

By contributing to this project, you agree that your contributions will be licensed under the GNU General Public License v3.0 (GPLv3), the same license as the project.

Key implications:
- Your contributions become part of the GPL-licensed codebase
- Any derivative works must also be GPL-licensed
- You retain copyright to your contributions
- You grant the project permission to distribute your code under GPLv3

See the [LICENSE](./LICENSE) file for full details.

## Additional Resources

- [README.md](./README.md) - Project overview and usage
- [Sample Configs](./claude_desktop_config.json) - MCP client configuration examples
- [Environment Template](./.env.example) - Environment variable reference
- [MCP Documentation](https://modelcontextprotocol.io) - MCP protocol details
- [Yandex API Docs](https://yandex.com/dev/) - Yandex API reference

## Questions?

If you have questions about contributing:

1. Check the [README](./README.md) and this guide
2. Search [existing issues](https://github.com/amonrapmon/cto/issues)
3. Ask in [GitHub Discussions](https://github.com/amonrapmon/cto/discussions)
4. Create a new issue with the "question" label

---

Thank you for contributing to the Yandex MCP Server project! 🎉
