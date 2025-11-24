#!/bin/bash
# start_chrome_debug.sh - Start Chrome with remote debugging (Mac/Linux)

echo "🚀 Starting Chrome with remote debugging..."
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROFILE_DIR="$PROJECT_DIR/chrome-profile"

echo "📁 Profile directory: $PROFILE_DIR"
echo ""

# Kill existing Chrome processes
echo "Closing existing Chrome instances..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected: macOS"
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try to find Chrome
    echo "Detected: Linux"
    
    if command -v google-chrome &> /dev/null; then
        google-chrome --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
    elif command -v google-chrome-stable &> /dev/null; then
        google-chrome-stable --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
    elif command -v chromium &> /dev/null; then
        chromium --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
    elif command -v chromium-browser &> /dev/null; then
        chromium-browser --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
    else
        echo "❌ Chrome/Chromium not found!"
        echo "Please install Chrome or run manually"
        exit 1
    fi
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "Please run Chrome manually with: --remote-debugging-port=9222"
    exit 1
fi

sleep 3

echo ""
echo "✅ Chrome started with remote debugging on port 9222"
echo ""
echo "Next steps:"
echo "  1. Log in to ChatGPT in this Chrome window"
echo "  2. Go to https://chatgpt.com/gpts"
echo "  3. Run: python3 gpt_tracker_chrome.py"
echo ""
echo "To stop Chrome: pkill -f 'Google Chrome'"
