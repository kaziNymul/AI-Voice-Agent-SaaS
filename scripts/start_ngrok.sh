#!/bin/bash
# Quick start ngrok tunnel for local testing
# Exposes localhost:8000 with a public HTTPS URL

PORT=${1:-8000}

if ! command -v ngrok &> /dev/null; then
    echo "❌ Ngrok not installed!"
    echo "Run: ./scripts/setup_ngrok.sh for installation guide"
    exit 1
fi

echo "🌐 Starting ngrok tunnel for localhost:$PORT"
echo ""
echo "Your app will be available at: https://XXXXX.ngrok.io"
echo ""
echo "Use this URL for:"
echo "  • Telegram webhook: https://XXXXX.ngrok.io/telegram/webhook"
echo "  • Twilio webhook: https://XXXXX.ngrok.io/phone/call"
echo ""
echo "Press Ctrl+C to stop..."
echo ""

ngrok http $PORT
