# Manual Tests

This directory is for manual test scripts and procedures that require human interaction or cannot be automated.

## Purpose

Manual tests are used for:
- Testing features that require real system resources (large downloads, etc.)
- Performance testing with real workloads
- User acceptance testing scenarios
- Exploratory testing scripts
- Tests that require specific hardware or environments

## Running Manual Tests

Manual tests are **not** run by the automated test suite. They must be executed individually:

```bash
# Run a specific manual test
python tests/manual/test_something_manual.py
```

## Creating Manual Tests

When creating manual tests:
1. Use the `@pytest.mark.manual` marker
2. Document prerequisites clearly
3. Include expected outcomes
4. Add cleanup instructions

Example:
```python
import pytest

@pytest.mark.manual
def test_large_sysroot_creation():
    """
    Manual test: Create a large sysroot with many packages.
    
    Prerequisites:
    - At least 5GB free disk space
    - Stable internet connection
    - debootstrap, binutils, fakeroot installed
    
    Expected outcome:
    - Sysroot created successfully
    - All packages installed
    - Time: ~10-15 minutes
    
    Cleanup:
    - rm -rf /tmp/large-sysroot
    """
    # Test implementation
    pass
```

## Test Categories

- **Performance Tests**: Measure execution time, resource usage
- **Stress Tests**: Test with large inputs, many packages
- **Real-World Scenarios**: Test actual use cases end-to-end
- **Interactive Tests**: Tests requiring user input or verification
