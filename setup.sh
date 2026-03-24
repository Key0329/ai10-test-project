#!/bin/bash
set -e

echo "========================================"
echo "  Claude Remote Agent — Setup"
echo "========================================"
echo ""

# ── Check prerequisites ──
check() { command -v "$1" &>/dev/null && echo "  ✅ $1 found" || { echo "  ❌ $1 not found — $2"; MISSING=1; }; }

MISSING=0
echo "Checking prerequisites..."
check python3 "brew install python3"
check node "brew install node"
check git "brew install git"
check gh "brew install gh && gh auth login"
check claude "npm install -g @anthropic-ai/claude-code"

if [ "$MISSING" -eq 1 ]; then
  echo ""
  echo "⚠️  Some prerequisites are missing. Install them first."
  exit 1
fi

echo ""

# ── Python venv & deps ──
echo "Setting up Python backend..."
cd "$(dirname "$0")"
cd backend && uv sync && cd ..
echo "  ✅ Python dependencies installed"

# ── Frontend build ──
echo "Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..
echo "  ✅ Frontend built to frontend/dist/"

# ── .env ──
if [ ! -f ".env" ]; then
  cp .env.example .env
  # Generate random token
  TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  sed -i '' "s/change-me-to-a-strong-random-string/$TOKEN/" .env 2>/dev/null || \
  sed -i "s/change-me-to-a-strong-random-string/$TOKEN/" .env
  echo "  ✅ .env created with random token: $TOKEN"
  echo ""
  echo "  ⚠️  Save this token — your team needs it to connect:"
  echo "     $TOKEN"
else
  echo "  ✅ .env already exists"
fi

# ── Workspace dir ──
mkdir -p ~/claude-workspace/.db ~/claude-workspace/.logs
echo "  ✅ Workspace directory created"

# ── LaunchAgent (macOS auto-start) ──
PLIST_PATH="$HOME/Library/LaunchAgents/com.claude-remote-agent.plist"
SCRIPT_DIR="$(pwd)"
VENV_PYTHON="$SCRIPT_DIR/backend/.venv/bin/python"

if [ ! -f "$PLIST_PATH" ]; then
  cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude-remote-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PYTHON</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
        <string>--http</string>
        <string>h11</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}/backend</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/claude-workspace/.logs/server-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/claude-workspace/.logs/server-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
  echo "  ✅ LaunchAgent plist created"
else
  echo "  ✅ LaunchAgent plist already exists"
fi

echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "  Quick start:"
echo "    cd backend"
echo "    source .venv/bin/activate"
echo "    uvicorn main:app --host 0.0.0.0 --port 8000 --http h11"
echo ""
echo "  Auto-start on boot:"
echo "    launchctl load $PLIST_PATH"
echo ""
echo "  Then open: http://\$(ipconfig getifaddr en0):8000"
echo ""
