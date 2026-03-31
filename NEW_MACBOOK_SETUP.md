# 🍎 New MacBook M5 Pro 16" — Complete Setup Guide
## Darrian Belcher · March 2026

> **Order of operations matters.** Follow the phases in order.
> Total time: ~45–60 min (most of it is waiting for installs).

---

## ⚡ PHASE 0 — Migration Assistant Decision

On the "Transfer Your Data to This Mac" screen you're seeing right now:

**Recommendation: Skip Migration Assistant → Do a clean install**

Why: M5 arm64 chip — fresh install runs faster, no old x86 cruft.
Your data is all in GitHub or iCloud — nothing is lost.

→ **Click "Not Now" / "Don't Transfer Any Information"**
→ Finish the macOS setup wizard (Apple ID, Touch ID, etc.)

---

## PHASE 1 — System Essentials (do this first, everything else depends on it)

### 1a. Sign into iCloud
- System Settings → Apple ID → sign in
- Turn ON: iCloud Drive, Contacts, Calendar, Safari, Keychain, Photos
- This auto-restores your Safari bookmarks, passwords, and iCloud files

### 1b. Xcode Command Line Tools (required for Homebrew + Git)
```bash
xcode-select --install
```
Click Install in the popup. Takes ~5 min.

### 1c. Homebrew (Mac package manager)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
After install, run the two `eval` commands it prints at the end (adds brew to PATH for arm64).

### 1d. Core dev tools via Homebrew
```bash
brew install git python@3.12 node tailscale
brew install --cask visual-studio-code google-chrome
```

---

## PHASE 2 — SSH Key + GitHub (get this working before cloning)

### 2a. Generate a new SSH key for the new Mac
```bash
ssh-keygen -t ed25519 -C "darrianebelcher@gmail.com" -f ~/.ssh/id_ed25519_m5pro
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_m5pro
cat ~/.ssh/id_ed25519_m5pro.pub
```

### 2b. Add the public key to GitHub
- Copy the output from the `cat` command
- Go to: https://github.com/settings/ssh/new
- Title: "MacBook M5 Pro 16" (2026)"
- Paste the key → Add SSH Key

### 2c. Test it
```bash
ssh -T git@github.com
# Should say: Hi bookofdarrian! You've successfully authenticated...
```

---

## PHASE 3 — Clone the Repos

```bash
mkdir -p ~/Downloads
cd ~/Downloads

# darrian-budget (PSS app)
git clone git@github.com:bookofdarrian/darrian-budget.git darrian-budget
cd darrian-budget

# Set up Python virtual environment (MUST use arm64 Python)
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Repo cloned and venv ready"
```

---

## PHASE 4 — Restore Your Budget Data (DBs + API Keys)

Your data files are NOT in git (they're gitignored). You need to AirDrop or copy them from the old Mac.

### Option A: AirDrop (easiest — both Macs on same WiFi)

**On the OLD Mac** — run this to create the package:
```bash
cd ~/Downloads/darrian-budget
bash package_for_new_mac.sh
```
This creates `~/Desktop/darrian_budget_data_TRANSFER.tar.gz`

Then **AirDrop that file to the new Mac**.

**On the NEW Mac** — after receiving the AirDrop:
```bash
cd ~/Downloads/darrian-budget
tar -xzf ~/Desktop/darrian_budget_data_TRANSFER.tar.gz
echo "✅ Data restored"
```

### Option B: USB Drive
Copy `darrian_budget_data_TRANSFER.tar.gz` to a USB → plug into new Mac → run the tar command above.

### Option C: Direct scp over WiFi (both Macs on same network)
```bash
# Run this on the NEW Mac (replace OLD_MAC_IP with actual IP)
scp -r darrianbelcher@OLD_MAC_IP:~/Downloads/darrian-budget/data ~/Downloads/darrian-budget/
```

---

## PHASE 5 — VS Code Setup

### 5a. Open VS Code on new Mac
```bash
code ~/Downloads/darrian-budget
```

### 5b. Sign in to Settings Sync (restores all your extensions + settings)
- VS Code → Manage (gear icon, bottom left) → Turn on Settings Sync
- Sign in with GitHub account
- All your extensions, themes, keybindings restore automatically

### 5c. Install Cline extension (if not restored by sync)
- Extensions (⌘⇧X) → search "Cline" → Install
- Cline Settings → set your Anthropic API key:
  `sk-ant-api03-...` (from your budget.db app_settings)

### 5d. Set VS Code default terminal to zsh
- ⌘⇧P → "Terminal: Select Default Profile" → zsh

---

## PHASE 6 — Claude Desktop + MCP

### 6a. Download Claude Desktop
```
https://claude.ai/download
```
Install → open → sign in → Claude Pro plan

### 6b. Configure MCP (gives Claude access to your files)
```bash
mkdir -p ~/Library/Application\ Support/Claude
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/darrianbelcher/Downloads/darrian-budget",
        "/Users/darrianbelcher/Documents",
        "/Users/darrianbelcher/Desktop"
      ]
    }
  }
}
EOF
echo "✅ Claude Desktop MCP configured"
```

### 6c. Set up Claude Projects
Open Claude Desktop → sidebar → New Project for each:
- **🍑 Darrian — Master** → paste content from `CLAUDE_DESKTOP_SETUP.md` Step 5
- **🎬 CC Content Creator** → paste `.claude/agents/cc-content-creator.md`
- **👟 SoleOps Intel** → paste `.claude/agents/soleops-intel.md`
- **💼 Business Strategist** → paste `.claude/agents/business-strategist.md`

---

## PHASE 7 — Bookmarks

### Safari (via iCloud — should be automatic after Phase 1a)
- If not auto-synced: Safari → File → Import From → Bookmarks HTML File
- Use: `~/Downloads/darrian-budget/PEACH_STATE_BOOKMARKS.html`

### Chrome
- Sign in to Chrome with your Google account → all bookmarks sync automatically
- Or: Chrome → Bookmarks → Import Bookmarks → select `PEACH_STATE_BOOKMARKS.html`

---

## PHASE 8 — Tailscale (access your homelab from anywhere)

```bash
# Tailscale was installed in Phase 1d
# Open it from the menu bar → Log In
# Sign in with Google/GitHub → authorize this new Mac
# Your homelab (100.95.125.112) should appear automatically
```

Test homelab connection:
```bash
ssh root@100.95.125.112
```

---

## PHASE 9 — Run Peach State Savings Locally

```bash
cd ~/Downloads/darrian-budget
source venv/bin/activate
streamlit run app.py
```
→ Opens at http://localhost:8501
→ Log in with darrianebelcher@gmail.com

---

## PHASE 10 — Quick Wins (optional but recommended)

### Wispr Flow (voice → text anywhere)
- Download: https://wisprflow.ai
- Install → grant accessibility permissions
- Double-tap right Option key to dictate anywhere

### Claude Code (terminal AI agent)
```bash
npm install -g @anthropic-ai/claude-code
# Then in any repo dir:
claude
```

### macOS Productivity Tweaks
```bash
# Show hidden files in Finder
defaults write com.apple.finder AppleShowAllFiles YES && killall Finder

# Faster key repeat (better for coding)
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Screenshot location → Desktop
defaults write com.apple.screencapture location ~/Desktop
```

---

## ✅ Setup Verification Checklist

Run this after completing all phases:

```bash
cd ~/Downloads/darrian-budget
source venv/bin/activate
python3 -m py_compile app.py && echo "✅ App syntax OK"
python3 -c "import sqlite3; conn = sqlite3.connect('data/budget.db'); print('✅ DB connected:', conn.execute('SELECT COUNT(*) FROM users').fetchone()[0], 'users')"
git remote -v && echo "✅ Git remote OK"
ssh -T git@github.com 2>&1 | grep -q "successfully" && echo "✅ GitHub SSH OK"
tailscale status 2>/dev/null | head -3 && echo "✅ Tailscale connected"
echo ""
echo "🍑 New Mac setup complete!"
```

---

## 🔑 API Keys Reference
All your API keys live in `data/budget.db` → `app_settings` table.
They transfer automatically when you copy the data folder.

| Key | Used In |
|-----|---------|
| `anthropic_api_key` | All AI features in PSS, Cline |
| `spotify_client_id/secret` | Media Library page |
| `telegram_bot_token` | Budget bot notifications |
| `ebay_client_id/secret` | SoleOps eBay integration |
| `google_credentials` | Gmail / PA page |

**⚠️ Never commit these to git — they live ONLY in the DB.**
