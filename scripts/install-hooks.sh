#!/bin/bash
# Install git hooks for ProtoBox
# Sets up both pre-commit (fast checks) and pre-push (integration tests)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📦 Installing ProtoBox git hooks..."

# ============================================================================
# PRE-COMMIT HOOK - Fast checks only (<5 seconds)
# ============================================================================
cat > "$PROJECT_ROOT/.git/hooks/pre-commit" << 'EOF'
#!/bin/bash
# ProtoBox pre-commit hook - Uses Makefile targets for consistency
# Target: <5 seconds execution time

# Change to project root
cd "$(git rev-parse --show-toplevel)"

# Run fast checks via Makefile
make check-fast || exit 1
EOF

# ============================================================================
# PRE-PUSH HOOK - Integration tests and deeper checks (<30 seconds)
# ============================================================================
cat > "$PROJECT_ROOT/.git/hooks/pre-push" << 'EOF'
#!/bin/bash
# ProtoBox pre-push hook - Uses Makefile targets for consistency
# Target: <30 seconds execution time

# Change to project root
cd "$(git rev-parse --show-toplevel)"

# Run push checks via Makefile (includes integration tests if needed)
make check-push || exit 1
EOF

# Make hooks executable
chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"
chmod +x "$PROJECT_ROOT/.git/hooks/pre-push"

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "📋 Hook Configuration:"
echo "   • Pre-commit: Fast checks (<5 seconds)"
echo "     - File size limits"
echo "     - Debug statement detection"
echo "     - Syntax validation (Python, JSON)"
echo "     - Merge conflict detection"
echo ""
echo "   • Pre-push: Quality gates (<30 seconds)"
echo "     - Integration tests (if Python changed)"
echo "     - TypeScript compilation (if TS/JS changed)"
echo "     - Automatic backend startup if needed"
echo ""
echo "💡 Tips:"
echo "   - Skip hooks temporarily: git commit --no-verify"
echo "   - Skip push hooks: git push --no-verify"
echo "   - Run tests manually: make test-integration-api"
echo ""

# Check if pre-commit package is installed
if command -v pre-commit &> /dev/null; then
    echo "📦 pre-commit package detected. Installing additional formatters..."
    pre-commit install
    echo "   Run 'pre-commit run --all-files' to format all files"
else
    echo "💡 Optional: Install pre-commit for automatic formatting:"
    echo "   pip install pre-commit && pre-commit install"
fi