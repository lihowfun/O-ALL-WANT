#!/bin/bash
# Agent Memory Framework — One-Command Installer
# https://github.com/lihowfun/agent-memory-framework

set -e  # Exit on error

echo "🚀 Agent Memory Framework Installer"
echo "===================================="
echo ""

# Detect project root (where this script is run from)
PROJECT_ROOT="$(pwd)"
FRAMEWORK_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📁 Installing to: $PROJECT_ROOT"
echo "📦 Framework source: $FRAMEWORK_DIR"
echo ""

# Check if files already exist
if [ -f "$PROJECT_ROOT/CLAUDE.md" ] || [ -f "$PROJECT_ROOT/AI_CONTEXT.md" ]; then
    echo "⚠️  WARNING: CLAUDE.md or AI_CONTEXT.md already exists!"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled."
        exit 1
    fi
fi

echo "📋 Copying templates..."

# Copy core files
cp "$FRAMEWORK_DIR/templates/AGENT_RULES.md" "$PROJECT_ROOT/CLAUDE.md"
cp "$FRAMEWORK_DIR/templates/AI_CONTEXT.md" "$PROJECT_ROOT/AI_CONTEXT.md"
cp "$FRAMEWORK_DIR/templates/VERSION.json" "$PROJECT_ROOT/VERSION.json"

# Copy directories
mkdir -p "$PROJECT_ROOT/.agents"
cp -r "$FRAMEWORK_DIR/templates/.agents"/* "$PROJECT_ROOT/.agents/"

mkdir -p "$PROJECT_ROOT/docs/knowledge"
cp -r "$FRAMEWORK_DIR/templates/docs/knowledge"/* "$PROJECT_ROOT/docs/knowledge/"

mkdir -p "$PROJECT_ROOT/.github"
cp "$FRAMEWORK_DIR/templates/.github/copilot-instructions.md" "$PROJECT_ROOT/.github/"

mkdir -p "$PROJECT_ROOT/scripts"
cp "$FRAMEWORK_DIR/scripts/context_hub.py" "$PROJECT_ROOT/scripts/"
chmod +x "$PROJECT_ROOT/scripts/context_hub.py"

echo "✅ Files installed!"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "⚠️  Python 3 not found. Install Python 3 to use context_hub.py CLI."
else
    echo "🐍 Python 3 detected: $(python3 --version)"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit AI_CONTEXT.md — Fill in \${PROJECT_NAME}, architecture, tech stack"
echo "   2. Edit CLAUDE.md — Set language preference + forbidden actions"
echo "   3. Tell your AI agent: \"Read CLAUDE.md first, then AI_CONTEXT.md. Follow the lazy-read protocol.\""
echo ""
echo "💡 Try the CLI:"
echo "   python scripts/context_hub.py status"
echo "   python scripts/context_hub.py memory add \"[DECISION] Installed agent memory framework\""
echo ""
echo "📚 Full docs: $FRAMEWORK_DIR/docs/"
echo ""
