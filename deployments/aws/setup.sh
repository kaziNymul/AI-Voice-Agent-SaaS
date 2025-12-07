#!/bin/bash

# AWS Setup Script - All configuration from .env file
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Setting up AWS-based AI Customer Care..."
echo ""

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load .env
export $(cat "$ROOT_DIR/.env" | grep -v '^#' | xargs)

# Validate AWS credentials in .env
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS credentials not found in .env"
    echo "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "❌ AWS_REGION not set in .env"
    exit 1
fi

echo "✓ Configuration loaded from .env"
echo "  Region: $AWS_REGION"
echo "  Bedrock Model: ${AWS_BEDROCK_MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0}"
echo ""

# Check AWS CLI (optional)
if command -v aws &> /dev/null; then
    echo "✓ AWS CLI found, testing credentials..."
    aws sts get-caller-identity --region $AWS_REGION || {
        echo "⚠️  AWS credentials test failed"
        echo "Continuing anyway (will use env vars)..."
    }
else
    echo "ℹ️  AWS CLI not found (optional)"
fi

echo ""
echo "Building Docker image..."
cd "$SCRIPT_DIR"
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "✅ AWS setup complete!"
echo ""
echo "Services:"
docker-compose ps

echo ""
echo "Bot container: ${CUSTOMER_ID:-customer}_aws"
echo "Port: ${BOT_PORT:-8000}"
echo ""
echo "To view logs: docker-compose -f $SCRIPT_DIR/docker-compose.yml logs -f"
echo "To stop: docker-compose -f $SCRIPT_DIR/docker-compose.yml down"
