#!/bin/bash
# package_for_new_mac.sh
# Run this on the OLD Mac to bundle all budget data for AirDrop to new MacBook M5 Pro
# Usage: bash package_for_new_mac.sh

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$HOME/Desktop/darrian_budget_data_TRANSFER.tar.gz"
STAGING=$(mktemp -d)

echo ""
echo "🍑 Peach State Savings — New Mac Data Packager"
echo "================================================"
echo "  Source: $REPO_DIR"
echo "  Output: $OUTPUT"
echo ""

# ── 1. Budget DBs (all your financial data + API keys) ────────────────────────
echo "📦 Packing budget databases..."
mkdir -p "$STAGING/data/users"
cp "$REPO_DIR/data/budget.db"    "$STAGING/data/"       2>/dev/null && echo "  ✅ budget.db"
cp "$REPO_DIR/data/budget_qa.db" "$STAGING/data/"       2>/dev/null && echo "  ✅ budget_qa.db (QA)"  || true
cp -r "$REPO_DIR/data/users/"    "$STAGING/data/users/" 2>/dev/null && echo "  ✅ per-user DBs (your financial data)" || true

# ── 2. Spotify token cache ────────────────────────────────────────────────────
if [ -f "$REPO_DIR/.spotify_token_cache" ]; then
    cp "$REPO_DIR/.spotify_token_cache" "$STAGING/" && echo "  ✅ Spotify token cache"
fi

# ── 3. .env file (if exists) ─────────────────────────────────────────────────
if [ -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env" "$STAGING/" && echo "  ✅ .env file"
fi

# ── 4. SSH keys (for GitHub + homelab) ────────────────────────────────────────
echo ""
echo "🔑 Packing SSH keys..."
mkdir -p "$STAGING/ssh"
if ls ~/.ssh/id_* >/dev/null 2>&1; then
    cp ~/.ssh/id_* "$STAGING/ssh/" 2>/dev/null || true
    cp ~/.ssh/known_hosts "$STAGING/ssh/" 2>/dev/null || true
    echo "  ✅ SSH keys copied"
else
    echo "  ⚠️  No SSH keys found — you'll generate a new one on the new Mac"
fi

# ── 5. Claude Desktop config (MCP setup) ─────────────────────────────────────
echo ""
echo "🤖 Packing Claude Desktop config..."
CLAUDE_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_CFG" ]; then
    mkdir -p "$STAGING/claude"
    cp "$CLAUDE_CFG" "$STAGING/claude/" && echo "  ✅ claude_desktop_config.json"
fi

# ── 6. Bookmarks ─────────────────────────────────────────────────────────────
echo ""
echo "🔖 Packing bookmarks..."
cp "$REPO_DIR/PEACH_STATE_BOOKMARKS.html" "$STAGING/" 2>/dev/null && echo "  ✅ PEACH_STATE_BOOKMARKS.html" || true

# Export Safari bookmarks from this Mac
SAFARI_BOOKMARKS="$HOME/Library/Safari/Bookmarks.plist"
if [ -f "$SAFARI_BOOKMARKS" ]; then
    cp "$SAFARI_BOOKMARKS" "$STAGING/Safari_Bookmarks_$(date +%Y%m%d).plist" && echo "  ✅ Safari bookmarks (plist)"
fi

# ── 7. VS Code settings + extensions list ─────────────────────────────────────
echo ""
echo "💻 Packing VS Code settings..."
VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User"
if [ -d "$VSCODE_SETTINGS" ]; then
    mkdir -p "$STAGING/vscode"
    cp "$VSCODE_SETTINGS/settings.json"  "$STAGING/vscode/" 2>/dev/null || true
    cp "$VSCODE_SETTINGS/keybindings.json" "$STAGING/vscode/" 2>/dev/null || true
    # Export installed extensions list
    code --list-extensions > "$STAGING/vscode/extensions.txt" 2>/dev/null && echo "  ✅ VS Code extensions list" || true
    echo "  ✅ VS Code settings.json + keybindings"
fi

# ── 8. Git global config ───────────────────────────────────────────────────────
if [ -f ~/.gitconfig ]; then
    cp ~/.gitconfig "$STAGING/gitconfig" && echo "  ✅ .gitconfig (git user/email)"
fi

# ── 9. Cline settings ─────────────────────────────────────────────────────────
CLINE_SETTINGS="$HOME/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev"
if [ -d "$CLINE_SETTINGS" ]; then
    mkdir -p "$STAGING/cline"
    cp "$CLINE_SETTINGS/settings/cline_mcp_settings.json" "$STAGING/cline/" 2>/dev/null || true
    echo "  ✅ Cline MCP settings"
fi

# ── 10. zsh config ────────────────────────────────────────────────────────────
for f in ~/.zshrc ~/.zprofile ~/.zsh_history; do
    [ -f "$f" ] && cp "$f" "$STAGING/$(basename $f)" && echo "  ✅ $(basename $f)"
done

# ── Create a README inside the package ────────────────────────────────────────
cat > "$STAGING/RESTORE_INSTRUCTIONS.txt" << 'RESTORE'
DARRIAN'S MAC DATA PACKAGE — Restore Instructions
===================================================

1. After cloning darrian-budget on new Mac:
   cd ~/Downloads/darrian-budget
   tar -xzf ~/Desktop/darrian_budget_data_TRANSFER.tar.gz -C .
   # This restores: data/ folder with all DBs + API keys

2. Restore SSH keys (if included):
   cp ssh/id_* ~/.ssh/
   chmod 600 ~/.ssh/id_*
   chmod 644 ~/.ssh/id_*.pub
   ssh-add ~/.ssh/id_ed25519   # or whatever key name

3. Restore git config:
   cp gitconfig ~/.gitconfig

4. Restore zsh config:
   cp .zshrc ~/.zshrc
   source ~/.zshrc

5. Restore Claude Desktop MCP:
   mkdir -p ~/Library/Application\ Support/Claude
   cp claude/claude_desktop_config.json ~/Library/Application\ Support/Claude/
   # Restart Claude Desktop

6. Restore VS Code extensions:
   cat vscode/extensions.txt | xargs -L 1 code --install-extension
   cp vscode/settings.json ~/Library/Application\ Support/Code/User/
   cp vscode/keybindings.json ~/Library/Application\ Support/Code/User/

7. Import Safari bookmarks:
   Safari → File → Import From → Bookmarks HTML File
   Select: PEACH_STATE_BOOKMARKS.html

DONE! Run the verification checklist in NEW_MACBOOK_SETUP.md
RESTORE

# ── Pack everything ────────────────────────────────────────────────────────────
echo ""
echo "📦 Creating archive..."
cd "$STAGING"
tar -czf "$OUTPUT" .
rm -rf "$STAGING"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "================================================"
echo "✅ Package created: $OUTPUT ($SIZE)"
echo ""
echo "Next steps:"
echo "  1. AirDrop '$OUTPUT' to your new MacBook M5 Pro"
echo "  2. On new Mac: cd ~/Downloads/darrian-budget && tar -xzf ~/Desktop/darrian_budget_data_TRANSFER.tar.gz"
echo "  3. Follow RESTORE_INSTRUCTIONS.txt (included in the archive)"
echo "  4. See NEW_MACBOOK_SETUP.md for the full setup guide"
echo ""
echo "🎉 Opening Desktop so you can AirDrop the file..."
open "$HOME/Desktop"
