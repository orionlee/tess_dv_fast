#!/bin/bash

# Quick Start Guide for E2E Test Suite

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  TESS DV Fast - E2E Test Suite Quick Start                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v curl &> /dev/null; then
    echo "❌ curl is required but not installed"
    echo "   Install with: apt-get install curl (Ubuntu/Debian)"
    echo "                 brew install curl (macOS)"
    exit 1
fi
echo "✓ curl is available"

if ! command -v bash &> /dev/null; then
    echo "❌ bash is required"
    exit 1
fi
echo "✓ bash is available"

# Check test script exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/test_e2e_sanity.sh"

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "❌ Test script not found at $TEST_SCRIPT"
    exit 1
fi
echo "✓ Test script found"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Available Commands                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Test Go version only:"
echo "  cd $SCRIPT_DIR"
echo "  ./test_e2e_sanity.sh go"
echo ""
echo "Test Python version only:"
echo "  cd $SCRIPT_DIR"
echo "  ./test_e2e_sanity.sh python"
echo ""
echo "Test both versions (default):"
echo "  cd $SCRIPT_DIR"
echo "  ./test_e2e_sanity.sh both"
echo ""
echo "Test with custom port (Go only):"
echo "  PORT=9090 ./test_e2e_sanity.sh go"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Build Instructions (if needed)                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Build Go version:"
echo "  cd $SCRIPT_DIR/src/go"
echo "  go build -o tess_dv_fast_server"
echo ""
echo "Setup Python version:"
echo "  cd $SCRIPT_DIR"
echo "  pip install -r requirements.txt"
echo "  python tess_dv_fast_build.py --update --minimal_db"
echo "  python tess_spoc_dv_fast_build.py --update"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Documentation                                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Full documentation: TEST_E2E_SANITY_README.md"
echo "Implementation details: E2E_TEST_IMPLEMENTATION.md"
echo ""
echo "Ready to run tests! 🚀"
