#!/bin/bash

# OpenAI Setup Script - All configuration from .env file
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Setting up OpenAI-based AI Customer Care..."
echo ""

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load .env
export $(cat "$ROOT_DIR/.env" | grep -v '^#' | xargs)

# Validate OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in .env"
    echo "Please set your OpenAI API key"
    exit 1
fi

echo "✓ Configuration loaded from .env"
echo "  Model: ${OPENAI_MODEL:-gpt-4}"
echo "  Embedding: ${OPENAI_EMBEDDING_MODEL:-text-embedding-3-large}"
echo ""

echo "Building Docker image..."
cd "$SCRIPT_DIR"
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "✅ OpenAI setup complete!"
echo ""
echo "Services:"
docker-compose ps

echo ""
echo "Bot container: ${CUSTOMER_ID:-customer}_openai"
echo "Port: ${BOT_PORT:-8000}"
echo ""
echo "To view logs: docker-compose -f $SCRIPT_DIR/docker-compose.yml logs -f"
echo "To stop: docker-compose -f $SCRIPT_DIR/docker-compose.yml down"
