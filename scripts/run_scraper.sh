#!/bin/bash
# run_scraper.sh - One command to rule them all!

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              GPTracker - Quick Run                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Profile directory - save in current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROFILE_DIR="$PROJECT_DIR/chrome-profile"

echo "📁 Profile will be saved to: $PROFILE_DIR"

# Check if first time (no profile exists)
if [ ! -d "$PROFILE_DIR" ]; then
    echo "🆕 First time setup detected!"
    echo ""
    echo "I'll open Chrome for you to log in to ChatGPT."
    echo ""
    echo "IMPORTANT:"
    echo "  1. Log in to ChatGPT"
    echo "  2. ✅ Check 'Remember me' or 'Stay signed in'"
    echo "  3. Go to https://chatgpt.com/gpts to verify"
    echo "  4. Come back here and press Enter"
    echo ""
    read -p "Press Enter to open Chrome..."
fi

# Close existing Chrome
echo "🔄 Closing existing Chrome instances..."
pkill -f "remote-debugging-port=9222" 2>/dev/null || true
sleep 2

# Start Chrome with debugging
echo "🚀 Starting Chrome with remote debugging..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try to find Chrome
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
        exit 1
    fi
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Wait for Chrome to start
echo "⏳ Waiting for Chrome to start..."
sleep 5

# Check if this is first time
if [ ! -f "$PROFILE_DIR/First Run" ] && [ ! -f "$PROFILE_DIR/Cookies" ]; then
    echo ""
    echo "📋 FIRST TIME SETUP:"
    echo "══════════════════════════════════════════════════════════"
    echo "Chrome should now be open."
    echo ""
    echo "Please:"
    echo "  1. Go to https://chatgpt.com"
    echo "  2. Log in"
    echo "  3. ✅ Check 'Remember me'"
    echo "  4. Go to https://chatgpt.com/gpts"
    echo "  5. Verify you can see the GPT Store"
    echo ""
    echo "Then come back here and press Enter."
    echo "══════════════════════════════════════════════════════════"
    echo ""
    read -p "✋ Press Enter after logging in..."
    echo ""
fi

# Verify port is open
if ! curl -s http://localhost:9222/json > /dev/null 2>&1; then
    echo "❌ Chrome debugging port not responding"
    echo "Make sure Chrome started correctly"
    exit 1
fi

echo "✅ Chrome is ready!"
echo ""

# Ask what to run
echo "Choose mode:"
echo "  1) Test mode (10 keywords, 50 GPTs) - 5 min"
echo "  2) Small mode (100 keywords, custom limit)"
echo "  3) Custom"
echo ""
read -p "Enter choice [1-3, default=1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo "🧪 Running TEST mode..."
        python3 gpt_tracker_chrome.py
        ;;
    2)
        echo "📚 Running SMALL mode..."
        python3 gpt_tracker_chrome.py --small
        ;;
    3)
        echo "Running scraper..."
        python3 gpt_tracker_chrome.py
        ;;
    *)
        echo "Invalid choice, running test mode..."
        python3 gpt_tracker_chrome.py
        ;;
esac

echo ""
echo "✅ Done!"
echo ""
echo "Results saved to: data/chrome/"
echo ""
echo "To analyze results:"
echo "  python3 analyze_data.py data/chrome/all_*.json"
echo ""
echo "Chrome is still running. To stop it:"
echo "  pkill -f 'remote-debugging-port=9222'"
echo ""
