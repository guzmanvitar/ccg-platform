# Tests for CCG Platform

This directory contains tests for the CCG Platform, specifically for the geographic assignment functionality.

## Test Structure

- `test_geoassign_api.py` - Integration tests for the API endpoints (requires running server)
- `test_geoassign_models.py` - Django model and API tests using Django's test framework
- `run_tests.py` - Test runner script for running all tests

## Logging

All tests now output detailed logs to the `logs/` directory. Each test run creates timestamped log files:

- `test_api_YYYYMMDD_HHMMSS.log` - API integration test logs
- `test_django_YYYYMMDD_HHMMSS.log` - Django test logs
- `test_models_YYYYMMDD_HHMMSS.log` - Model test logs
- `test_runner_YYYYMMDD_HHMMSS.log` - Test runner logs

Logs are also displayed in the console for immediate feedback.

## Running Tests

### 1. Integration Tests (API Tests)

These tests require the Django server to be running:

```bash
# Start the Django server first
DJANGO_SETTINGS_MODULE=ccg_platform.settings uv run -m django runserver 8000

# In another terminal, run the integration tests
uv run python tests/test_geoassign_api.py
```

### 2. Django Tests

These tests use Django's test framework and don't require a running server:

```bash
# Run Django tests
DJANGO_SETTINGS_MODULE=ccg_platform.settings uv run -m django test tests.test_geoassign_models -v 2

# Or run all Django tests
DJANGO_SETTINGS_MODULE=ccg_platform.settings uv run -m django test
```

### 3. All Tests

Use the test runner script:

```bash
uv run python tests/run_tests.py
```

## Test Types

### Integration Tests (`test_geoassign_api.py`)
- Test actual API endpoints
- Require running Django server
- Test the full pipeline including SCAT execution
- Use `requests` library to make HTTP calls
- Logs saved to `logs/test_api_*.log`

### Django Tests (`test_geoassign_models.py`)
- Use Django's test framework
- Don't require running server
- Can test models, views, and API endpoints
- Use Django's test client
- Logs saved to `logs/test_django_*.log` and `logs/test_models_*.log`

## Adding New Tests

1. For API integration tests: Add to `test_geoassign_api.py`
2. For Django model/view tests: Add to `test_geoassign_models.py`
3. For new test categories: Create new files following the naming convention `test_*.py`

## Notes

- The SCAT pipeline tests require the SCAT executable to be compiled and available
- In a CI/CD environment, you might want to mock the SCAT execution
- Django tests are faster and more suitable for automated testing
- Integration tests are better for manual verification of the full system
- All test logs are automatically saved to the `logs/` directory with timestamps