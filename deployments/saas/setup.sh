#!/bin/bash

# SaaS Dashboard Setup Script
# Reads all configuration from root .env file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== SaaS Dashboard Setup ===${NC}"
echo ""

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found in root directory${NC}"
    echo ""
    echo "Please create .env file:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    echo "Required variables for SaaS deployment:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - SECRET_KEY"
    echo "  - JWT_SECRET_KEY"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - DEPLOYMENT (local, aws, or openai)"
    exit 1
fi

# Load environment variables
echo -e "${BLUE}Loading configuration from .env...${NC}"
export $(cat "$ROOT_DIR/.env" | grep -v '^#' | xargs)

# Validate required variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD:Database password"
    "SECRET_KEY:Flask secret key"
    "JWT_SECRET_KEY:JWT secret key"
)

MISSING_VARS=()
for var_info in "${REQUIRED_VARS[@]}"; do
    var_name="${var_info%%:*}"
    var_desc="${var_info##*:}"
    
    if [ -z "${!var_name}" ]; then
        MISSING_VARS+=("  - $var_name ($var_desc)")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required variables in .env:${NC}"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo ""
    echo "Add these to your .env file:"
    echo "  POSTGRES_PASSWORD=your_secure_password"
    echo "  SECRET_KEY=\$(openssl rand -hex 32)"
    echo "  JWT_SECRET_KEY=\$(openssl rand -hex 32)"
    exit 1
fi

# Validate deployment type
if [ -z "$DEPLOYMENT" ]; then
    echo -e "${YELLOW}⚠️  DEPLOYMENT not set, defaulting to 'local'${NC}"
    export DEPLOYMENT=local
fi

if [ "$DEPLOYMENT" != "local" ] && [ "$DEPLOYMENT" != "aws" ] && [ "$DEPLOYMENT" != "openai" ]; then
    echo -e "${RED}❌ Invalid DEPLOYMENT value: $DEPLOYMENT${NC}"
    echo "Must be: local, aws, or openai"
    exit 1
fi

# Deployment-specific validation
case "$DEPLOYMENT" in
    aws)
        if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
            echo -e "${RED}❌ AWS credentials required for DEPLOYMENT=aws${NC}"
            exit 1
        fi
        ;;
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo -e "${RED}❌ OPENAI_API_KEY required for DEPLOYMENT=openai${NC}"
            exit 1
        fi
        ;;
esac

echo -e "${GREEN}✅ Configuration validated${NC}"
echo ""
echo "SaaS Platform Settings:"
echo "  - Deployment: $DEPLOYMENT"
echo "  - Platform Domain: ${PLATFORM_DOMAIN:-localhost}"
echo "  - Dashboard Port: ${DASHBOARD_PORT:-5000}"
echo "  - Database: PostgreSQL"
echo "  - Vector DB: Elasticsearch"
echo ""

# Stop existing containers
echo -e "${YELLOW}Stopping existing SaaS containers...${NC}"
cd "$SCRIPT_DIR"
docker-compose down 2>/dev/null || true
echo ""

# Build and start services
echo -e "${BLUE}Building and starting SaaS platform...${NC}"
docker-compose up -d --build

echo ""
echo -e "${GREEN}✅ SaaS Dashboard deployed successfully!${NC}"
echo ""
echo "Access points:"
echo "  - Dashboard: http://localhost:${DASHBOARD_PORT:-5000}"
echo "  - PostgreSQL: localhost:${POSTGRES_PORT:-5432}"
echo "  - Elasticsearch: http://localhost:${ES_PORT:-9200}"
echo ""
echo "Next steps:"
echo "  1. Initialize database: docker exec saas_dashboard python -c 'from saas_dashboard.app import db; db.create_all()'"
echo "  2. Access dashboard at http://localhost:${DASHBOARD_PORT:-5000}"
echo "  3. Create customers and provision bots"
echo ""
echo "View logs:"
echo "  docker logs -f saas_dashboard"
echo ""
