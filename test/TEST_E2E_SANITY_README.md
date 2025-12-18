# End-to-End Sanity Test Suite

Comprehensive bash script for testing both the Go and Python versions of the TESS DV Fast web application.

## Features

- **Dual-version support**: Test Go and Python implementations independently or together
- **Automatic server management**: Starts/stops servers, handles port conflicts
- **Comprehensive test coverage**: 9 test scenarios per version
- **Color-coded output**: Easy-to-read test results with visual feedback
- **Detailed reporting**: Summary statistics and failure details
- **Cross-platform compatible**: Works on Linux, macOS, and Windows with bash

## Test Coverage

Each version is tested with the following scenarios:

1. **Homepage Redirect** - Verify `/` redirects to `/tces`
2. **Search Page Load** - Verify `/tces` page loads successfully
3. **SPOC Query** - Test SPOC-only pipeline (`?pipeline=spoc`)
4. **TESS-SPOC Query** - Test TESS-SPOC-only pipeline (`?pipeline=tess_spoc`)
5. **Dual Pipeline Query** - Test both pipelines together (`?pipeline=both`)
6. **Pipeline Parameter Variations** - Test default, empty, and explicit parameters
7. **Invalid TIC ID Handling** - Verify graceful error handling
8. **SPOC Column Validation** - Check for expected columns in results
9. **HTML Structure** - Verify proper HTML document structure

## Prerequisites

- `bash` - Shell interpreter
- `curl` - For HTTP requests
- `lsof` (optional) - For port management

## Usage

### Run all tests (both versions)
```bash
./test_e2e_sanity.sh
# or explicitly
./test_e2e_sanity.sh both
```

### Run Go version tests only
```bash
./test_e2e_sanity.sh go
```

### Run Python version tests only
```bash
./test_e2e_sanity.sh python
```

## Output Format

### Success Example
```
[INFO] Starting Go server on port 8080...
[✓] Server on port 8080 is ready
[✓] Homepage redirect to /tces (HTTP 301)
[✓] Search page loads (HTTP 200)
[✓] SPOC query loads (HTTP 200)
[✓] SPOC query returns data
...
```

### Test Summary
```
═══════════════════════════════════════════════════════════
Test Summary
═══════════════════════════════════════════════════════════
Passed: 18
Failed: 0

✓ All tests passed!
```

## Configuration

Edit these variables at the top of the script to customize:

```bash
PYTHON_FLASK_PORT=5000    # Python Flask server port
GO_PORT=8080              # Go server port  
TIMEOUT=30                # Maximum seconds to wait for server startup
```

## Environment Variables

- `PORT` - Set Go server port (e.g., `PORT=9000 ./test_e2e_sanity.sh go`)
- `FLASK_APP` - Set Python Flask app (used internally)
- `FLASK_ENV` - Set Flask environment (production by default)

## Server Ports

- **Go version**: `8080` (configurable via PORT env var)
- **Python version**: `5000` (Flask default)

The script will attempt to kill any existing processes on these ports before starting.

## Requirements

### Go Version
- Go binary at `src/go/tess_dv_fast_server`
- SQLite databases in `data/tess_dv_fast/` directory
- Port 8080 available (or specify PORT environment variable)

### Python Version
- Python Flask application at `tess_dv_fast_webapp.py`
- Dependencies installed (from `requirements.txt`)
- SQLite databases in `data/tess_dv_fast/` directory
- Port 5000 available

## Log Files

Server output is captured in:
- `/tmp/go_server.log` - Go server logs
- `/tmp/python_server.log` - Python server logs

Check these files if tests fail.

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed, or prerequisite check failed

## Troubleshooting

### "Server failed to start within 30s"
- Check that port is not in use: `lsof -i :8080` or `lsof -i :5000`
- Check server logs in `/tmp/*.log`
- Verify databases exist in `data/tess_dv_fast/`

### "Go binary not found"
- Build the Go binary: `cd src/go && go build -o tess_dv_fast_server`

### "Python webapp not found"
- Verify `tess_dv_fast_webapp.py` exists in project root
- Install dependencies: `pip install -r requirements.txt`

### Port conflicts
- The script attempts to kill existing processes automatically
- If manual cleanup needed: `lsof -ti :PORT | xargs kill -9`

## Performance Expectations

- Go version server startup: ~2-5 seconds
- Python version server startup: ~5-10 seconds
- Total test suite execution: ~30-45 seconds (both versions)
- Each test HTTP request: ~200-500ms

## Test Data

Tests use well-known TESS target:
- **TIC ID**: 261136679 (π Mensae / pi Men)
- This target has both SPOC and TESS-SPOC data available

## Extending Tests

To add new tests:

1. Create a new test function following the pattern:
```bash
test_new_feature() {
    local port=$1
    local version=$2
    
    log_info "Testing new feature ($version)..."
    local body=$(http_test "$port" "/endpoint" "200" "Test description" || echo "")
    
    if check_result; then
        return 0
    else
        return 1
    fi
}
```

2. Call from the test runner:
```bash
run_go_tests() {
    # ... existing tests ...
    test_new_feature $GO_PORT "Go"
}
```

## Limitations

- Tests use hardcoded TIC ID (261136679) - may not work if data changes
- No database state validation (assumes databases are pre-populated)
- No authentication testing (if authentication is added later)
- Limited to HTTP status codes and content presence checks (not deep content validation)

## Contributing

To add new tests or improve the suite:

1. Follow the existing test function pattern
2. Use provided utility functions (`log_success`, `log_error`, `http_test`)
3. Add description and documentation for new tests
4. Test with both versions: `./test_e2e_sanity.sh both`

## License

Part of the TESS DV Fast project. See project LICENSE file.
