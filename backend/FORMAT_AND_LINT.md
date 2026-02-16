# Code Formatting & Linting

This backend uses three tools for code quality:

## Tools

- **black** - Automatic code formatter
- **isort** - Import statement organizer
- **flake8** - Code linter (style and error checker)

## Usage

### Format Code
```powershell
# Format all Python files
black .

# Format specific file
black main.py
```

### Sort Imports
```powershell
# Sort imports in all files
isort .

# Sort imports in specific file
isort main.py
```

### Lint Code
```powershell
# Check all files for style/errors
flake8 .

# Check specific file
flake8 main.py
```

### Run All Together
```powershell
# Format, sort, and lint (in order)
black . ; isort . ; flake8 .
```

## Configuration

All tools are configured in `pyproject.toml`:
- Line length: 88 characters
- Black-compatible isort profile
- Flake8 ignores some whitespace rules for black compatibility

## Tips

- Run `black .` and `isort .` before committing code
- `flake8` will show any remaining warnings/errors after formatting
- Configuration is already set up to work well together
