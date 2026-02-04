# Contributing to Sysroot-Maker

Thank you for your interest in contributing! This document provides guidelines for testing and development.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sysroot-maker
   ```

2. **Install development dependencies:**
   ```bash
   uv sync --extra test
   ```

3. **Install system dependencies (for integration tests):**
   ```bash
   sudo apt-get install debootstrap binutils fakeroot
   ```

## Testing Guidelines

### Test Types

We use three types of tests:

1. **Unit Tests** (`@pytest.mark.unit`)
   - Fast tests with mocked dependencies
   - No real system calls (debootstrap, ar, etc.)
   - Test individual functions in isolation
   - Should complete in milliseconds

2. **Integration Tests** (`@pytest.mark.integration`)
   - Tests with real system calls
   - Requires system dependencies installed
   - Tests interaction between components
   - May take seconds to minutes

3. **Slow Tests** (`@pytest.mark.slow`)
   - Long-running tests (e.g., full debootstrap)
   - Only run when needed

### Running Tests

**Quick feedback (unit tests only):**
```bash
uv run pytest tests/ -m unit -v
```

**Full test suite:**
```bash
uv run pytest tests/ -v
```

**Specific test file:**
```bash
uv run pytest tests/test_unit.py -v
```

**With coverage report:**
```bash
uv run pytest tests/ --cov=. --cov-report=term-missing
```

**Skip slow tests:**
```bash
uv run pytest tests/ -m "not slow" -v
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from unittest.mock import patch
import sysroot_maker

@pytest.mark.unit
def test_get_mirror_for_arch():
    """Test mirror selection for different architectures."""
    result = sysroot_maker.get_mirror_for_arch("arm64")
    assert result == "http://ports.ubuntu.com/ubuntu-ports"
```

#### Integration Test Example

```python
import pytest
import sysroot_maker

@pytest.mark.integration
@pytest.mark.requires_debootstrap
def test_extract_deb_package(mock_deb_package, temp_output_dir):
    """Test extracting a real .deb package."""
    result = sysroot_maker.extract_deb_package(
        str(mock_deb_package),
        str(temp_output_dir),
        verbose=True,
    )
    assert result is True
```

### Test Fixtures

Common fixtures are available in `tests/conftest.py`:

- `temp_output_dir` - Temporary directory for test output (auto-cleaned)
- `sample_package_list` - Sample package list file
- `mock_deb_package` - Mock .deb package for testing
- `mock_environment` - Mock system environment

### Testing Best Practices

1. **Use temp directories:** Always use `temp_output_dir` fixture or `tmp_path`
2. **Clean up resources:** Tests should not leave artifacts in system directories
3. **Mock external calls:** Unit tests should mock subprocess calls and network I/O
4. **Test edge cases:** Include tests for error conditions and invalid inputs
5. **Fast unit tests:** Keep unit tests fast (<100ms each)
6. **Mark appropriately:** Use correct test markers (`@pytest.mark.unit`, etc.)

### Code Coverage

We aim for >80% code coverage. Check coverage with:

```bash
uv run pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

Focus coverage on:
- Core functionality (debootstrap, deb extraction)
- Error handling paths
- Input validation

Some code paths (like `main()` CLI flow) are harder to test and may have lower coverage.

## Continuous Integration

GitHub Actions runs on every push and pull request:

1. **Unit Tests** - Fast feedback on basic functionality
2. **Integration Tests** - Full system testing with dependencies
3. **Linting** - Code style and format checking

### Local CI Simulation

Run the same checks that CI runs:

```bash
# Unit tests
uv run pytest tests/ -m unit -v --cov=. --cov-report=term

# Integration tests (requires system deps)
uv run pytest tests/ -m integration -v

# Linting (if ruff is configured)
uv tool run ruff check .
uv tool run ruff format --check .
```

## Pull Request Process

1. **Write tests** for new features or bug fixes
2. **Run tests locally** before submitting PR
3. **Ensure CI passes** - all tests must pass
4. **Update documentation** if changing user-facing behavior
5. **Keep changes focused** - one feature/fix per PR

## Questions?

If you have questions about testing or development, please open an issue!
