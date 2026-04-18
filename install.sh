#!/bin/bash
# O-ALL-WANT — One-Command Installer
# https://github.com/lihowfun/O-ALL-WANT

set -e  # Exit on error

echo "🚀 O-ALL-WANT Installer"
echo "===================================="
echo ""

# Detect project root (where this script is run from)
PROJECT_ROOT="$(pwd)"
FRAMEWORK_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📁 Installing to: $PROJECT_ROOT"
echo "📦 Framework source: $FRAMEWORK_DIR"
echo ""

# Refuse to install into the OAW framework repo itself.
# Running ./install.sh from inside the OAW clone treats the repo as a target
# and overwrites its own root CLAUDE.md / AI_CONTEXT.md / ROADMAP.md. Catch
# this before the copy step — prior self-install accidents are what motivated
# the check. Pass --force-self-install to override (rarely wanted).
if [ "$PROJECT_ROOT" = "$FRAMEWORK_DIR" ] || [ -f "$PROJECT_ROOT/templates/AGENT_RULES.md" ]; then
    if [ "$1" != "--force-self-install" ]; then
        echo "❌ Refusing to install: this directory looks like the OAW framework repo itself."
        echo ""
        echo "   PROJECT_ROOT: $PROJECT_ROOT"
        echo "   FRAMEWORK_DIR: $FRAMEWORK_DIR"
        echo ""
        echo "   Installing here would overwrite the framework's own root files."
        echo "   To install into another project:"
        echo "     cd /path/to/your/project && $FRAMEWORK_DIR/install.sh"
        echo "   If you really know what you are doing, pass --force-self-install."
        exit 1
    fi
    echo "⚠️  --force-self-install set — proceeding despite self-install detection."
    echo ""
fi

# Build the exact list of managed files the installer may overwrite
MANAGED_PATHS=(
    "CLAUDE.md"
    "AI_CONTEXT.md"
    "ROADMAP.md"
    "VERSION.json"
    ".github/copilot-instructions.md"
    "scripts/context_hub.py"
    "scripts/wiki_sync.py"
)

while IFS= read -r relative_path; do
    MANAGED_PATHS+=(".agents/$relative_path")
done < <(cd "$FRAMEWORK_DIR/templates/.agents" && find . -type f | sed 's#^\./##' | sort)

while IFS= read -r relative_path; do
    MANAGED_PATHS+=("docs/knowledge/$relative_path")
done < <(cd "$FRAMEWORK_DIR/templates/docs/knowledge" && find . -type f | sed 's#^\./##' | sort)

while IFS= read -r relative_path; do
    MANAGED_PATHS+=("docs/raw/$relative_path")
done < <(cd "$FRAMEWORK_DIR/templates/docs/raw" && find . -type f | sed 's#^\./##' | sort)

EXISTING_PATHS=()
for managed_path in "${MANAGED_PATHS[@]}"; do
    if [ -e "$PROJECT_ROOT/$managed_path" ]; then
        EXISTING_PATHS+=("$managed_path")
    fi
done

# Check if managed files already exist
if [ "${#EXISTING_PATHS[@]}" -gt 0 ]; then
    echo "⚠️  WARNING: This installer will overwrite the following managed files:"
    for existing_path in "${EXISTING_PATHS[@]}"; do
        echo "   - $existing_path"
    done
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
cp "$FRAMEWORK_DIR/templates/ROADMAP.md" "$PROJECT_ROOT/ROADMAP.md"
cp "$FRAMEWORK_DIR/templates/VERSION.json" "$PROJECT_ROOT/VERSION.json"

# Copy directories
mkdir -p "$PROJECT_ROOT/.agents"
cp -R "$FRAMEWORK_DIR/templates/.agents/." "$PROJECT_ROOT/.agents/"

mkdir -p "$PROJECT_ROOT/docs/knowledge"
cp -R "$FRAMEWORK_DIR/templates/docs/knowledge/." "$PROJECT_ROOT/docs/knowledge/"

mkdir -p "$PROJECT_ROOT/docs/raw"
cp -R "$FRAMEWORK_DIR/templates/docs/raw/." "$PROJECT_ROOT/docs/raw/"

mkdir -p "$PROJECT_ROOT/.github"
cp "$FRAMEWORK_DIR/templates/.github/copilot-instructions.md" "$PROJECT_ROOT/.github/"

mkdir -p "$PROJECT_ROOT/scripts"
cp "$FRAMEWORK_DIR/scripts/context_hub.py" "$PROJECT_ROOT/scripts/"
cp "$FRAMEWORK_DIR/scripts/wiki_sync.py" "$PROJECT_ROOT/scripts/"
chmod +x "$PROJECT_ROOT/scripts/context_hub.py"
chmod +x "$PROJECT_ROOT/scripts/wiki_sync.py"

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
echo "📝 Next step — paste this to your AI agent:"
echo ""
echo "   🆕 Brand-new project:"
echo "   Read CLAUDE.md first, then AI_CONTEXT.md."
echo "   I'm building [describe your project]. Fill in the AI_CONTEXT.md scaffold, then suggest which repeated workflows belong in .agents/skills/."
echo ""
echo "   📂 Existing project:"
echo "   Read CLAUDE.md first, then AI_CONTEXT.md. Based on OAW's architecture, audit this project and suggest how to optimize it."
echo ""
echo "💡 Try the tools:"
echo "   python3 scripts/context_hub.py status"
echo "   python3 scripts/context_hub.py memory add \"[DECISION] Installed O-ALL-WANT\""
echo "   python3 scripts/wiki_sync.py lint"
echo ""
echo "📚 Full docs: $FRAMEWORK_DIR/docs/"
echo ""
