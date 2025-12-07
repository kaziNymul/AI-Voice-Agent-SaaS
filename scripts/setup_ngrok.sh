#!/bin/bash
# Setup ngrok for local development and testing
# This creates a public HTTPS URL for your localhost:8000

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🌐 Ngrok Setup for Local Testing"
echo "================================"
echo ""
echo "Ngrok creates a public HTTPS URL for your local application."
echo "Use cases:"
echo "  • Telegram webhook testing (requires HTTPS)"
echo "  • Twilio webhook testing (requires public URL)"
echo "  • SIP trunk testing with external providers"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ Ngrok not found!"
    echo ""
    echo "📥 Install ngrok:"
    echo ""
    echo "Option 1 - Download binary:"
    echo "  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
    echo "  sudo tar xvzf ngrok-v3-stable-linux-amd64.tgz -C /usr/local/bin"
    echo ""
    echo "Option 2 - Snap (Ubuntu/Debian):"
    echo "  sudo snap install ngrok"
    echo ""
    echo "Option 3 - Homebrew (macOS):"
    echo "  brew install ngrok/ngrok/ngrok"
    echo ""
    echo "Then get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "And run: ngrok config add-authtoken <your-token>"
    exit 1
fi

# Check if ngrok is authenticated
if ! ngrok config check &> /dev/null; then
    echo "⚠️  Ngrok is not authenticated!"
    echo ""
    echo "Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "Then run: ngrok config add-authtoken <your-token>"
    echo ""
    read -p "Do you have your auth token? (y/n): " has_token
    if [[ "$has_token" == "y" ]]; then
        read -p "Enter your ngrok auth token: " auth_token
        ngrok config add-authtoken "$auth_token"
        echo "✅ Auth token saved!"
    else
        exit 1
    fi
fi

echo "✅ Ngrok is installed and configured!"
echo ""

# Ask which port to expose
read -p "Which port is your application running on? (default: 8000): " app_port
app_port=${app_port:-8000}

echo ""
echo "🚀 Starting ngrok tunnel..."
echo ""
echo "Exposing localhost:$app_port to the internet..."
echo ""
echo "⚠️  IMPORTANT: Keep this terminal open!"
echo "Press Ctrl+C to stop the tunnel when done testing."
echo ""
echo "═══════════════════════════════════════════════════════════"

# Start ngrok
ngrok http $app_port --log=stdout --log-level=info

# This will run until Ctrl+C
echo ""
echo "Ngrok tunnel stopped."
