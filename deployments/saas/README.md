# Multi-Tenant SaaS Dashboard Deployment

Deploy a complete multi-tenant SaaS platform for managing customer AI bots.

## What's Included

- **SaaS Dashboard**: Flask web app for customer management
- **PostgreSQL**: Customer metadata and bot configurations
- **Elasticsearch**: Shared vector database for all customer bots
- **Nginx**: Reverse proxy (optional, for production)
- **Docker Socket**: Auto-provisions customer bot containers

## Architecture

```
SaaS Platform
├── Dashboard (Flask) - Customer management UI/API
├── PostgreSQL - Customer accounts & bot configs
├── Elasticsearch - Shared knowledge base
└── Docker Socket - Provisions customer containers

Customer Bots (Auto-provisioned)
├── Customer 1 Bot (local/aws/openai)
├── Customer 2 Bot (local/aws/openai)
└── Customer N Bot (local/aws/openai)
```

## Quick Start

### 1. Configure

```bash
cd /mnt/e/call_center_agent
cp .env.example .env
nano .env
```

Add SaaS-specific variables:
```bash
# SaaS Dashboard
POSTGRES_PASSWORD=your_secure_password
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Dashboard settings
DASHBOARD_PORT=5000
PLATFORM_DOMAIN=localhost

# Customer bot deployment type (all customers use same)
DEPLOYMENT=local   # or aws, or openai

# Telegram
TELEGRAM_BOT_TOKEN=your_token
```

### 2. Deploy

```bash
cd deployments/saas
./setup.sh

# Or use Makefile
make saas
```

### 3. Initialize Database

```bash
docker exec saas_dashboard python -c 'from saas_dashboard.app import db; db.create_all()'
```

### 4. Access Dashboard

Open: `http://localhost:5000`

## Configuration

All settings in root `.env` file:

### Required Variables

```bash
# Database
POSTGRES_PASSWORD=secure_password

# Security
SECRET_KEY=your_flask_secret_key
JWT_SECRET_KEY=your_jwt_secret_key

# Platform
TELEGRAM_BOT_TOKEN=your_telegram_token
```

### Optional Variables

```bash
# Ports
DASHBOARD_PORT=5000
POSTGRES_PORT=5432
ES_PORT=9200

# Database
POSTGRES_DB=saas_db
POSTGRES_USER=saas_user

# Resources
ES_MEMORY_LIMIT=512m

# Network
NETWORK_NAME=saas_network
PLATFORM_DOMAIN=localhost
```

### Customer Bot Deployment

Choose AI provider for ALL customer bots:

**Local AI (Free)**
```bash
DEPLOYMENT=local
USE_LOCAL_MODELS=true
```

**AWS Services**
```bash
DEPLOYMENT=aws
USE_AWS_SERVICES=true
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

**OpenAI**
```bash
DEPLOYMENT=openai
USE_OPENAI=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
```

## Features

### Customer Management
- Sign up new customers via API
- Generate API keys for each customer
- Manage customer quotas and limits
- View customer usage statistics

### Bot Provisioning
- Automatically provisions Docker containers for each customer
- Isolated bot instances per customer
- Shared infrastructure (ES, Voice service if local)
- Dynamic resource allocation

### API Endpoints

#### Public
- `POST /api/signup` - Customer registration
- `POST /api/login` - Customer login
- `GET /api/customers/:id/bot-status` - Check bot status

#### Admin
- `GET /admin/customers` - List all customers
- `POST /admin/customers/:id/provision-bot` - Provision bot
- `DELETE /admin/customers/:id/deprovision-bot` - Remove bot
- `GET /admin/stats` - Platform statistics

## Usage

### Create Customer Account

```bash
curl -X POST http://localhost:5000/api/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "email": "admin@acme.com",
    "password": "secure_password"
  }'
```

### Provision Customer Bot

```bash
curl -X POST http://localhost:5000/admin/customers/1/provision-bot \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Upload Customer Data

```bash
curl -X POST http://localhost:5000/api/customers/1/upload-data \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -F "file=@customer_qa.json"
```

## Resource Requirements

### Minimum (Development)
- **RAM**: 8GB
- **CPU**: 4 cores
- **Disk**: 20GB

### Production (10 customers)
- **RAM**: 16GB+ (depends on customer count)
- **CPU**: 8+ cores
- **Disk**: 100GB+

### Per Customer Bot
- Local: ~4GB RAM (Ollama + Voice + Bot)
- AWS/OpenAI: ~512MB RAM (Bot only)

## Monitoring

### View Dashboard Logs
```bash
docker logs -f saas_dashboard
```

### View All Logs
```bash
cd deployments/saas
docker-compose logs -f
```

### Database Status
```bash
docker exec saas_postgres psql -U saas_user -d saas_db -c "SELECT * FROM customers;"
```

### Elasticsearch Health
```bash
curl http://localhost:9200/_cluster/health?pretty
```

## Scaling

### Horizontal Scaling
For larger deployments, consider:
1. **Separate ES cluster** - Dedicated Elasticsearch nodes
2. **PostgreSQL replica** - Read replicas for dashboard
3. **Multiple hosts** - Spread customer bots across servers
4. **Load balancer** - Nginx/HAProxy for dashboard

### Cost Optimization
- Use AWS/OpenAI for customer bots (cheaper than local hardware)
- Shared voice service for local deployments
- Auto-stop idle customer bots
- Tier-based pricing (basic/pro/enterprise)

## Production Deployment

### 1. HTTPS Setup

Create SSL certificate:
```bash
sudo certbot certonly --standalone -d yourdomain.com
```

Enable nginx in docker-compose:
```bash
docker-compose --profile production up -d
```

### 2. Database Backups

Setup automated backups:
```bash
# Add to crontab
0 2 * * * docker exec saas_postgres pg_dump -U saas_user saas_db > /backups/saas_$(date +\%Y\%m\%d).sql
```

### 3. Monitoring

Install monitoring stack:
- Prometheus + Grafana
- CloudWatch (AWS)
- Elasticsearch monitoring

### 4. Security

- Use strong passwords (`.env`)
- Enable HTTPS only
- Rate limiting on API endpoints
- Regular security updates
- Firewall rules (only expose 80/443)

## Troubleshooting

### Dashboard won't start?
```bash
docker logs saas_dashboard
# Check for missing env vars or database connection issues
```

### Database connection error?
```bash
docker exec saas_postgres pg_isready -U saas_user
```

### Customer bot won't provision?
```bash
# Check Docker socket access
docker exec saas_dashboard ls -la /var/run/docker.sock

# Check dashboard logs
docker logs saas_dashboard | grep provision
```

### Out of memory?
Reduce ES memory or customer bot limits in `.env`:
```bash
ES_MEMORY_LIMIT=256m
BOT_MEMORY_LIMIT=512m
```

## Migration from Old Setup

If you used `setup_ultralight_saas.sh` before:

```bash
# Export customer data
docker exec saas_postgres pg_dump -U saas_user saas_db > backup.sql

# Stop old setup
./cleanup_test_saas.sh

# Deploy new structure
cd deployments/saas
./setup.sh

# Import data
docker exec -i saas_postgres psql -U saas_user -d saas_db < backup.sql
```

## Cost Estimates

### Infrastructure (per month)

| Component | Cost |
|-----------|------|
| VPS (16GB RAM) | $50-100 |
| Domain + SSL | $15 |
| **Total** | **$65-115** |

### Per Customer Bot

| Provider | Cost per 1000 calls |
|----------|---------------------|
| Local | $0 |
| AWS | $20-30 |
| OpenAI | $20 |

---

**Ready to deploy?**
```bash
make saas
```
