# Contributing to MCP Server

Thank you for your interest in contributing to the MCP Server project! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Git

### Setting up the Development Environment

1. Clone the repository:
```bash
git clone https://github.com/chanl-ai/protobox-python.git
cd mcp-server
```

2. Install dependencies:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

4. Run tests to ensure everything is working:
```bash
pytest
```

## Development Workflow

### Making Changes

1. Create a new branch for your feature or bug fix:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. Make your changes following the coding standards below.

3. Add or update tests as necessary.

4. Run the test suite:
```bash
pytest
```

5. Run linting and formatting:
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

### Testing

- Write unit tests for all new functionality
- Ensure all tests pass before submitting a PR
- Aim for high test coverage
- Use pytest fixtures for common test setup

### Documentation

- Update the README.md if you add new features
- Add docstrings to all public APIs
- Update configuration examples if you add new config options
- Consider adding examples for new tools or features

## Submitting Changes

### Pull Request Process

1. Push your branch to GitHub:
```bash
git push origin feature/your-feature-name
```

2. Create a pull request with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots or examples if applicable

3. Ensure all CI checks pass

4. Request review from maintainers

### Commit Message Guidelines

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

Examples:
```
feat(tools): add database query tool
fix(transport): resolve websocket connection issues
docs(readme): update installation instructions
```

## Project Structure

```
mcp-server/
├── src/mcp/           # Main package code
│   ├── __init__.py
│   ├── server.py      # Core server implementation
│   ├── cli.py         # Command-line interface
│   ├── config/        # Configuration management
│   ├── protocol/      # MCP protocol implementation
│   ├── tools/         # Tool system
│   ├── actions/       # Action execution
│   ├── context/       # Context management
│   └── resources/     # Resource management
├── tests/             # Test files
├── examples/          # Example configurations
├── docs/              # Documentation
└── pyproject.toml     # Project configuration
```

## Adding New Tools

To add a new built-in tool:

1. Create a new file in `src/mcp/tools/`
2. Inherit from `BaseTool`
3. Implement required methods
4. Add tool to the registry
5. Add tests
6. Update documentation

Example:
```python
from mcp.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Description of what this tool does"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param"]
        }
    
    async def execute(self, arguments: dict) -> dict:
        # Tool implementation
        return {"result": "success"}
```

## Release Process

Releases are handled by maintainers following semantic versioning:

- `MAJOR.MINOR.PATCH`
- Breaking changes increment MAJOR
- New features increment MINOR
- Bug fixes increment PATCH

## Getting Help

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Join our community chat (link TBD)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License. 