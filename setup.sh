#!/bin/bash

# AI Voice Customer Care - Interactive Setup Wizard
# One script to rule them all!

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        AI Voice Customer Care - Setup Wizard             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BOLD}Welcome!${NC} Let's set up your AI voice customer care system."
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists.${NC}"
    read -p "Do you want to reconfigure? (y/N): " reconfigure
    if [[ ! $reconfigure =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Using existing .env file...${NC}"
        RECONFIGURE=false
    else
        RECONFIGURE=true
    fi
else
    RECONFIGURE=true
fi

if [ "$RECONFIGURE" = true ]; then
    echo ""
    echo -e "${BOLD}Step 1: Choose Your Deployment${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1) Single Bot - Local AI (FREE)"
    echo "   • TinyLlama, Whisper, MMS-TTS"
    echo "   • 4GB RAM, no API keys needed"
    echo "   • Best for: Development, testing"
    echo ""
    echo "2) Single Bot - AWS Services (Production)"
    echo "   • Bedrock, Transcribe, Polly"
    echo "   • ~$0.02/call, 10-17s latency"
    echo "   • Best for: Enterprise, scalability"
    echo ""
    echo "3) Single Bot - OpenAI (Best Quality)"
    echo "   • GPT-4, Whisper, TTS-1"
    echo "   • ~$0.02/call, 4-6s latency"
    echo "   • Best for: Production, quality"
    echo ""
    echo "4) Multi-Tenant SaaS Platform"
    echo "   • Customer management dashboard"
    echo "   • Auto-provisions customer bots"
    echo "   • PostgreSQL + Elasticsearch"
    echo "   • Best for: SaaS business, hosting"
    echo ""
    
    while true; do
        read -p "Enter your choice (1-4): " DEPLOYMENT_CHOICE
        case $DEPLOYMENT_CHOICE in
            1)
                DEPLOYMENT_TYPE="local"
                DEPLOYMENT_NAME="Local AI"
                break
                ;;
            2)
                DEPLOYMENT_TYPE="aws"
                DEPLOYMENT_NAME="AWS Services"
                break
                ;;
            3)
                DEPLOYMENT_TYPE="openai"
                DEPLOYMENT_NAME="OpenAI"
                break
                ;;
            4)
                DEPLOYMENT_TYPE="saas"
                DEPLOYMENT_NAME="SaaS Platform"
                break
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1-4.${NC}"
                ;;
        esac
    done
    
    echo ""
    echo -e "${GREEN}✓${NC} Selected: ${BOLD}$DEPLOYMENT_NAME${NC}"
    echo ""
    
    # Create .env from template
    echo -e "${BLUE}Creating .env file from template...${NC}"
    cp .env.example .env
    
    # Set deployment type
    if [ "$DEPLOYMENT_TYPE" != "saas" ]; then
        sed -i "s/DEPLOYMENT=local/DEPLOYMENT=$DEPLOYMENT_TYPE/" .env
    fi
    
    echo ""
    echo -e "${BOLD}Step 2: Configure Settings${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Common: Telegram Bot Token
    echo -e "${CYAN}Telegram Bot Token${NC}"
    echo "Get it from @BotFather on Telegram (https://t.me/BotFather)"
    read -p "Enter Telegram Bot Token: " TELEGRAM_TOKEN
    if [ -n "$TELEGRAM_TOKEN" ]; then
        sed -i "s|TELEGRAM_BOT_TOKEN=|TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN|" .env
    fi
    echo ""
    
    # Phone Integration (optional)
    echo -e "${CYAN}Phone Integration (Optional)${NC}"
    echo "Do you want to enable phone calls?"
    echo "  1) No - Telegram only"
    echo "  2) Yes - Twilio"
    echo "  3) Yes - SIP Trunk (Telia/DNA/Elisa)"
    read -p "Choose (1-3, default: 1): " PHONE_CHOICE
    
    case ${PHONE_CHOICE:-1} in
        2)
            echo ""
            echo -e "${CYAN}Twilio Configuration${NC}"
            read -p "Twilio Account SID: " TWILIO_SID
            read -p "Twilio Auth Token: " TWILIO_TOKEN
            read -p "Twilio Phone Number (e.g., +1234567890): " TWILIO_NUMBER
            
            sed -i "s/PHONE_PROVIDER=none/PHONE_PROVIDER=twilio/" .env
            sed -i "s|TWILIO_ACCOUNT_SID=|TWILIO_ACCOUNT_SID=$TWILIO_SID|" .env
            sed -i "s|TWILIO_AUTH_TOKEN=|TWILIO_AUTH_TOKEN=$TWILIO_TOKEN|" .env
            sed -i "s|TWILIO_PHONE_NUMBER=|TWILIO_PHONE_NUMBER=$TWILIO_NUMBER|" .env
            ;;
        3)
            echo ""
            echo -e "${CYAN}SIP Trunk Configuration${NC}"
            echo "Choose your provider:"
            echo "  1) Telia"
            echo "  2) DNA"
            echo "  3) Elisa"
            echo "  4) Custom"
            read -p "Choose (1-4): " SIP_CHOICE
            
            case ${SIP_CHOICE:-1} in
                1) SIP_PROVIDER="telia" ;;
                2) SIP_PROVIDER="dna" ;;
                3) SIP_PROVIDER="elisa" ;;
                *) SIP_PROVIDER="custom" ;;
            esac
            
            read -p "SIP Username: " SIP_USER
            read -p "SIP Password: " SIP_PASS
            read -p "SIP Domain: " SIP_DOM
            read -p "SIP Proxy (optional): " SIP_PROX
            
            sed -i "s/PHONE_PROVIDER=none/PHONE_PROVIDER=sip/" .env
            sed -i "s|SIP_PROVIDER=|SIP_PROVIDER=$SIP_PROVIDER|" .env
            sed -i "s|SIP_USERNAME=|SIP_USERNAME=$SIP_USER|" .env
            sed -i "s|SIP_PASSWORD=|SIP_PASSWORD=$SIP_PASS|" .env
            sed -i "s|SIP_DOMAIN=|SIP_DOMAIN=$SIP_DOM|" .env
            if [ -n "$SIP_PROX" ]; then
                sed -i "s|SIP_PROXY=|SIP_PROXY=$SIP_PROX|" .env
            fi
            ;;
        *)
            sed -i "s/PHONE_PROVIDER=none/PHONE_PROVIDER=none/" .env
            ;;
    esac
    echo ""
    
    # Deployment-specific configuration
    case $DEPLOYMENT_TYPE in
        local)
            echo -e "${GREEN}✓${NC} Local AI requires no additional API keys!"
            sed -i "s/USE_LOCAL_MODELS=true/USE_LOCAL_MODELS=true/" .env
            ;;
            
        aws)
            echo -e "${CYAN}AWS Credentials${NC}"
            read -p "AWS Access Key ID: " AWS_KEY
            read -p "AWS Secret Access Key: " AWS_SECRET
            read -p "AWS Region (default: us-east-1): " AWS_REGION
            AWS_REGION=${AWS_REGION:-us-east-1}
            
            read -p "OpenSearch Endpoint (e.g., https://...es.amazonaws.com): " OPENSEARCH_ENDPOINT
            
            echo ""
            echo "Available Bedrock Models:"
            echo "  1) Claude 3 Haiku (fast, cheap)"
            echo "  2) Claude 3 Sonnet (balanced)"
            echo "  3) Claude 3 Opus (best quality)"
            read -p "Choose model (1-3, default: 1): " MODEL_CHOICE
            case ${MODEL_CHOICE:-1} in
                2) BEDROCK_MODEL="anthropic.claude-3-sonnet-20240229-v1:0" ;;
                3) BEDROCK_MODEL="anthropic.claude-3-opus-20240229-v1:0" ;;
                *) BEDROCK_MODEL="anthropic.claude-3-haiku-20240307-v1:0" ;;
            esac
            
            sed -i "s/USE_AWS_SERVICES=false/USE_AWS_SERVICES=true/" .env
            sed -i "s|AWS_ACCESS_KEY_ID=|AWS_ACCESS_KEY_ID=$AWS_KEY|" .env
            sed -i "s|AWS_SECRET_ACCESS_KEY=|AWS_SECRET_ACCESS_KEY=$AWS_SECRET|" .env
            sed -i "s|AWS_REGION=us-east-1|AWS_REGION=$AWS_REGION|" .env
            sed -i "s|AWS_BEDROCK_MODEL_ID=.*|AWS_BEDROCK_MODEL_ID=$BEDROCK_MODEL|" .env
            sed -i "s|AWS_OPENSEARCH_ENDPOINT=|AWS_OPENSEARCH_ENDPOINT=$OPENSEARCH_ENDPOINT|" .env
            ;;
            
        openai)
            echo -e "${CYAN}OpenAI Configuration${NC}"
            read -p "OpenAI API Key (sk-...): " OPENAI_KEY
            
            echo ""
            echo "Available Models:"
            echo "  1) GPT-4 (best quality)"
            echo "  2) GPT-4 Turbo (faster)"
            echo "  3) GPT-3.5 Turbo (cheaper)"
            read -p "Choose model (1-3, default: 1): " MODEL_CHOICE
            case ${MODEL_CHOICE:-1} in
                2) OPENAI_MODEL="gpt-4-turbo" ;;
                3) OPENAI_MODEL="gpt-3.5-turbo" ;;
                *) OPENAI_MODEL="gpt-4" ;;
            esac
            
            sed -i "s/USE_OPENAI=false/USE_OPENAI=true/" .env
            sed -i "s|OPENAI_API_KEY=|OPENAI_API_KEY=$OPENAI_KEY|" .env
            sed -i "s|OPENAI_MODEL=gpt-4|OPENAI_MODEL=$OPENAI_MODEL|" .env
            ;;
            
        saas)
            echo -e "${CYAN}SaaS Platform Configuration${NC}"
            
            # Generate secure passwords
            POSTGRES_PASS=$(openssl rand -hex 16)
            SECRET_KEY=$(openssl rand -hex 32)
            JWT_KEY=$(openssl rand -hex 32)
            
            echo -e "${GREEN}✓${NC} Generated secure passwords automatically"
            
            sed -i "s|POSTGRES_PASSWORD=|POSTGRES_PASSWORD=$POSTGRES_PASS|" .env
            sed -i "s|SECRET_KEY=|SECRET_KEY=$SECRET_KEY|" .env
            sed -i "s|JWT_SECRET_KEY=|JWT_SECRET_KEY=$JWT_KEY|" .env
            sed -i "s/USE_SAAS=false/USE_SAAS=true/" .env
            
            echo ""
            echo "Customer bots will use which AI provider?"
            echo "  1) Local AI (free)"
            echo "  2) AWS Services"
            echo "  3) OpenAI"
            read -p "Choose (1-3, default: 1): " BOT_PROVIDER
            
            case ${BOT_PROVIDER:-1} in
                2)
                    sed -i "s/DEPLOYMENT=local/DEPLOYMENT=aws/" .env
                    echo ""
                    echo -e "${CYAN}AWS Credentials (for customer bots)${NC}"
                    read -p "AWS Access Key ID: " AWS_KEY
                    read -p "AWS Secret Access Key: " AWS_SECRET
                    sed -i "s|AWS_ACCESS_KEY_ID=|AWS_ACCESS_KEY_ID=$AWS_KEY|" .env
                    sed -i "s|AWS_SECRET_ACCESS_KEY=|AWS_SECRET_ACCESS_KEY=$AWS_SECRET|" .env
                    ;;
                3)
                    sed -i "s/DEPLOYMENT=local/DEPLOYMENT=openai/" .env
                    echo ""
                    echo -e "${CYAN}OpenAI API Key (for customer bots)${NC}"
                    read -p "OpenAI API Key: " OPENAI_KEY
                    sed -i "s|OPENAI_API_KEY=|OPENAI_API_KEY=$OPENAI_KEY|" .env
                    ;;
                *)
                    sed -i "s/DEPLOYMENT=local/DEPLOYMENT=local/" .env
                    ;;
            esac
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}✓${NC} Configuration saved to .env"
fi

# Display summary
echo ""
echo -e "${BOLD}Step 3: Deployment Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Read current deployment type
if [ -f .env ]; then
    source .env
    if [ "$USE_SAAS" = "true" ]; then
        DEPLOYMENT_TYPE="saas"
    else
        DEPLOYMENT_TYPE=${DEPLOYMENT:-local}
    fi
fi

case $DEPLOYMENT_TYPE in
    local)
        echo -e "${BOLD}Deployment:${NC} Single Bot - Local AI"
        echo -e "${BOLD}Cost:${NC} FREE (only server costs)"
        echo -e "${BOLD}Latency:${NC} 80-140 seconds"
        echo -e "${BOLD}Components:${NC} Ollama, Whisper, MMS-TTS, Elasticsearch"
        ;;
    aws)
        echo -e "${BOLD}Deployment:${NC} Single Bot - AWS Services"
        echo -e "${BOLD}Cost:${NC} ~$0.02 per call"
        echo -e "${BOLD}Latency:${NC} 10-17 seconds"
        echo -e "${BOLD}Components:${NC} Bedrock, Transcribe, Polly, OpenSearch"
        ;;
    openai)
        echo -e "${BOLD}Deployment:${NC} Single Bot - OpenAI"
        echo -e "${BOLD}Cost:${NC} ~$0.02 per call"
        echo -e "${BOLD}Latency:${NC} 4-6 seconds"
        echo -e "${BOLD}Components:${NC} GPT-4, Whisper, TTS-1, Elasticsearch"
        ;;
    saas)
        echo -e "${BOLD}Deployment:${NC} Multi-Tenant SaaS Platform"
        echo -e "${BOLD}Cost:${NC} Varies by customer count"
        echo -e "${BOLD}Components:${NC} PostgreSQL, Elasticsearch, Dashboard, Customer Bots"
        ;;
esac

echo ""
read -p "Proceed with deployment? (Y/n): " proceed
if [[ $proceed =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${YELLOW}Setup cancelled. Your .env file has been saved.${NC}"
    echo "You can run this script again or use: make $DEPLOYMENT_TYPE"
    exit 0
fi

# Deploy
echo ""
echo -e "${BOLD}Step 4: Deploying...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd deployments/$DEPLOYMENT_TYPE
./setup.sh

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║              ✓ DEPLOYMENT SUCCESSFUL!                     ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

case $DEPLOYMENT_TYPE in
    local|aws|openai)
        echo -e "${BOLD}Your bot is now running!${NC}"
        echo ""
        echo "Access points:"
        echo "  • Bot API: http://localhost:8001"
        echo "  • Health check: http://localhost:8001/health"
        echo "  • Telegram: Send voice message to your bot"
        echo ""
        echo "View logs:"
        echo "  make logs"
        ;;
    saas)
        echo -e "${BOLD}Your SaaS platform is now running!${NC}"
        echo ""
        echo "Access points:"
        echo "  • Dashboard: http://localhost:5000"
        echo "  • PostgreSQL: localhost:5432"
        echo "  • Elasticsearch: http://localhost:9200"
        echo ""
        echo "Initialize database:"
        echo "  docker exec saas_dashboard python -c 'from saas_dashboard.app import db; db.create_all()'"
        echo ""
        echo "View logs:"
        echo "  docker logs -f saas_dashboard"
        ;;
esac

echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Test your deployment"
echo "  2. Load your knowledge base data"
echo "  3. Send a test message via Telegram"
echo ""
echo "Need help? Check the documentation:"
echo "  • deployments/$DEPLOYMENT_TYPE/README.md"
echo "  • QUICK_REFERENCE.md"
echo ""
