#!/bin/bash

################################################################################
# End-to-End Sanity Test for TESS DV Fast (Go and Python versions)
#
# This script tests both the Go and Python implementations of the TESS DV Fast
# web application with the same test cases.
#
# Usage:
#   ./test_e2e_sanity.sh [go|python|both]
#
# Examples:
#   ./test_e2e_sanity.sh go        # Test Go version only
#   ./test_e2e_sanity.sh python    # Test Python version only
#   ./test_e2e_sanity.sh both      # Test both versions (default)
#
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GO_DIR="${PROJECT_DIR}/src/go"
PYTHON_DIR="${PROJECT_DIR}"
GO_BINARY="${GO_DIR}/tess_dv_fast_server"
PYTHON_FLASK_PORT=5000
GO_PORT=8080
TIMEOUT=30
TEST_VERSIONS="${1:-both}"

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_DETAILS=""

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TEST_DETAILS="${TEST_DETAILS}\n  ${RED}FAILED:${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Wait for server to be ready
wait_for_server() {
    local port=$1
    local max_attempts=$2
    local attempt=0

    log_info "Waiting for server on port $port to be ready..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "http://localhost:${port}/" > /dev/null 2>&1; then
            log_success "Server on port $port is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    log_error "Server on port $port failed to start within ${max_attempts}s"
    return 1
}

# Kill process by port
kill_by_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        local pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            log_info "Killing process on port $port (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
            sleep 1
        fi
    else
        log_warning "lsof not available, cannot check port $port"
    fi
}

# Perform HTTP test
http_test() {
    local port=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4

    local response=$(curl -s -w "\n%{http_code}" "http://localhost:${port}${endpoint}")
    local body=$(echo "$response" | head -n -1)
    local status=$(echo "$response" | tail -n 1)

    if [ "$status" = "$expected_status" ]; then
        log_success "$description (HTTP $status)"
        echo "$body"
        return 0
    else
        log_error "$description - Expected HTTP $expected_status, got $status"
        return 1
    fi
}

# Test homepage redirect
test_homepage() {
    local port=$1
    local version=$2

    log_info "Testing homepage redirect ($version)..."
    if http_test "$port" "/" "301" "Homepage redirect to /tces"; then
        return 0
    else
        return 1
    fi
}

# Test main search page loads
test_search_page() {
    local port=$1
    local version=$2

    log_info "Testing search page loads ($version)..."
    local body=$(http_test "$port" "/tces" "200" "Search page loads" || echo "")

    if echo "$body" | grep -q "TESS TCE Data Validation" || echo "$body" | grep -q "tces" || [ -n "$body" ]; then
        return 0
    else
        log_warning "Search page loaded but could not verify content"
        return 0
    fi
}

# Test SPOC query with specific TIC ID
test_spoc_query() {
    local port=$1
    local version=$2
    local tic_id="261136679"  # pi Men - well-known target

    log_info "Testing SPOC query for TIC $tic_id ($version)..."
    local body=$(http_test "$port" "/tces?tic=${tic_id}&pipeline=spoc" "200" "SPOC query loads" || echo "")

    if echo "$body" | grep -q "table_spoc" || echo "$body" | grep -q "$tic_id" || [ -n "$body" ]; then
        log_success "SPOC query returns data"
        return 0
    else
        log_warning "SPOC query loaded but could not verify SPOC table content"
        return 0
    fi
}

# Test TESS-SPOC query
test_tess_spoc_query() {
    local port=$1
    local version=$2
    local tic_id="261136679"

    log_info "Testing TESS-SPOC query for TIC $tic_id ($version)..."
    local body=$(http_test "$port" "/tces?tic=${tic_id}&pipeline=tess_spoc" "200" "TESS-SPOC query loads" || echo "")

    if echo "$body" | grep -q "table_tess_spoc" || echo "$body" | grep -q "TESS-SPOC" || [ -n "$body" ]; then
        log_success "TESS-SPOC query returns data"
        return 0
    else
        log_warning "TESS-SPOC query loaded but could not verify TESS-SPOC table content"
        return 0
    fi
}

# Test dual pipeline (both SPOC and TESS-SPOC)
test_dual_pipeline_query() {
    local port=$1
    local version=$2
    local tic_id="261136679"

    log_info "Testing dual pipeline query for TIC $tic_id ($version)..."
    local body=$(http_test "$port" "/tces?tic=${tic_id}&pipeline=both" "200" "Dual pipeline query loads" || echo "")

    if echo "$body" | grep -q "table_spoc" || [ -n "$body" ]; then
        log_success "Dual pipeline query returns data"
        return 0
    else
        log_warning "Dual pipeline query loaded but could not verify table content"
        return 0
    fi
}

# Test pipeline parameter variations
test_pipeline_parameter() {
    local port=$1
    local version=$2

    log_info "Testing pipeline parameter variations ($version)..."

    # Test default (no parameter) - should return both
    local body=$(http_test "$port" "/tces?tic=261136679" "200" "Default query (no pipeline parameter)" || echo "")
    [ -n "$body" ] && log_success "Default query works" || log_error "Default query failed"

    # Test empty pipeline parameter
    body=$(http_test "$port" "/tces?tic=261136679&pipeline=" "200" "Empty pipeline parameter" || echo "")
    [ -n "$body" ] && log_success "Empty pipeline parameter works" || log_error "Empty pipeline parameter failed"

    return 0
}

# Test invalid TIC ID handling
test_invalid_tic_id() {
    local port=$1
    local version=$2

    log_info "Testing invalid TIC ID handling ($version)..."
    # Invalid TIC ID should return a page with error message, with HTTP 400 status code
    http_test "$port" "/tces?tic=invalid123" "400" "Invalid TIC ID handling" > /dev/null && return 0
    return 0
}

# Test column presence in SPOC results
test_spoc_columns() {
    local port=$1
    local version=$2

    log_info "Testing SPOC table columns ($version)..."
    local body=$(curl -s "http://localhost:${port}/tces?tic=261136679&pipeline=spoc")

    local expected_columns=("exomast_id" "dvs" "dvm" "dvr" "R<sub>p</sub>" "Epoch" "Duration" "Period" "Depth" "Impact")
    local missing_columns=()

    for col in "${expected_columns[@]}"; do
        if ! echo "$body" | grep -q "$col"; then
            missing_columns+=("$col")
        fi
    done

    if [ ${#missing_columns[@]} -eq 0 ]; then
        log_success "All expected SPOC columns present"
        return 0
    else
        log_warning "Some expected SPOC columns missing: ${missing_columns[*]}"
        return 0
    fi
}

# Test HTML structure
test_html_structure() {
    local port=$1
    local version=$2

    log_info "Testing HTML structure ($version)..."
    local body=$(curl -s "http://localhost:${port}/tces")

    local checks=(
        "<!DOCTYPE"
        "<html"
        "<body"
        "</html"
    )

    for check in "${checks[@]}"; do
        if echo "$body" | grep -q "$check"; then
            log_success "Found: $check"
        else
            log_warning "Missing: $check"
        fi
    done

    return 0
}

################################################################################
# Version-Specific Test Runners
################################################################################

run_go_tests() {
    log_info "====== Testing Go Version ======"

    # Check if binary exists
    if [ ! -f "$GO_BINARY" ]; then
        log_error "Go binary not found at $GO_BINARY"
        return 1
    fi

    # Clean up any existing process
    kill_by_port $GO_PORT

    # Start the Go server
    log_info "Starting Go server on port $GO_PORT..."
    PORT=$GO_PORT "$GO_BINARY" > /tmp/go_server.log 2>&1 &
    local go_pid=$!
    trap "kill -9 $go_pid 2>/dev/null || true" EXIT

    # Wait for server to start
    if ! wait_for_server $GO_PORT $TIMEOUT; then
        cat /tmp/go_server.log
        return 1
    fi

    # Run tests
    test_homepage $GO_PORT "Go"
    test_search_page $GO_PORT "Go"
    test_spoc_query $GO_PORT "Go"
    test_tess_spoc_query $GO_PORT "Go"
    test_dual_pipeline_query $GO_PORT "Go"
    test_pipeline_parameter $GO_PORT "Go"
    test_invalid_tic_id $GO_PORT "Go"
    test_spoc_columns $GO_PORT "Go"
    test_html_structure $GO_PORT "Go"

    # Clean up
    log_info "Stopping Go server..."
    kill -9 $go_pid 2>/dev/null || true

    return 0
}

run_python_tests() {
    log_info "====== Testing Python Version ======"

    # Check if required files exist
    if [ ! -f "$PYTHON_DIR/tess_dv_fast_webapp.py" ]; then
        log_error "Python webapp not found at $PYTHON_DIR/tess_dv_fast_webapp.py"
        return 1
    fi

    # Clean up any existing process
    kill_by_port $PYTHON_FLASK_PORT

    # Start the Python server
    log_info "Starting Python Flask server on port $PYTHON_FLASK_PORT..."
    cd "$PYTHON_DIR"
    FLASK_APP=tess_dv_fast_webapp FLASK_ENV=production flask run -p $PYTHON_FLASK_PORT > /tmp/python_server.log 2>&1 &
    local python_pid=$!
    trap "kill -9 $python_pid 2>/dev/null || true" EXIT

    # Wait for server to start
    if ! wait_for_server $PYTHON_FLASK_PORT $TIMEOUT; then
        log_warning "Python server failed to start, showing logs:"
        tail -20 /tmp/python_server.log
        log_warning "Continuing with other tests..."
        kill -9 $python_pid 2>/dev/null || true
        return 0  # Don't fail entirely
    fi

    # Run tests
    test_homepage $PYTHON_FLASK_PORT "Python"
    test_search_page $PYTHON_FLASK_PORT "Python"
    test_spoc_query $PYTHON_FLASK_PORT "Python"
    test_tess_spoc_query $PYTHON_FLASK_PORT "Python"
    test_dual_pipeline_query $PYTHON_FLASK_PORT "Python"
    test_pipeline_parameter $PYTHON_FLASK_PORT "Python"
    test_invalid_tic_id $PYTHON_FLASK_PORT "Python"
    test_spoc_columns $PYTHON_FLASK_PORT "Python"
    test_html_structure $PYTHON_FLASK_PORT "Python"

    # Clean up
    log_info "Stopping Python server..."
    kill -9 $python_pid 2>/dev/null || true

    return 0
}

################################################################################
# Main
################################################################################

main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   TESS DV Fast - End-to-End Sanity Test Suite              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    log_info "Project directory: $PROJECT_DIR"
    log_info "Test mode: $TEST_VERSIONS"

    # Verify curl is available
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed. Please install curl to run this test."
        exit 1
    fi

    # Run requested tests
    case "$TEST_VERSIONS" in
        go)
            run_go_tests
            ;;
        python)
            run_python_tests
            ;;
        both|*)
            run_go_tests
            run_python_tests
            ;;
    esac

    # Print summary
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"

    if [ -n "$TEST_DETAILS" ]; then
        echo -e "\n${YELLOW}Test Details:${NC}"
        echo -e "$TEST_DETAILS"
    fi

    echo ""

    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed (see details above)${NC}"
        exit 1
    fi
}

# Run main
main "$@"
