# 🤖 AI Customer Care Agent

**Intelligent multi-channel customer support with voice & text capabilities**

A production-ready AI customer care system that handles customer inquiries via Telegram, phone calls (Twilio/SIP), with support for local AI models, AWS cloud services, or OpenAI. Includes optional multi-tenant SaaS platform with customer data upload dashboard.

---

## 🌟 Features

### Core Capabilities
- 💬 **Multi-Channel Support**: Telegram chat, Twilio phone calls, or SIP trunk integration
- 🎤 **Voice Processing**: Automatic speech-to-text and text-to-speech
- 🧠 **AI Conversation**: Natural language understanding with context awareness
- 📚 **RAG (Retrieval Augmented Generation)**: Upload custom knowledge bases (PDFs, CSVs, text)
- 🔄 **Auto-Learning**: Continuously improves from customer interactions
- 🌍 **Multi-Language**: Supports multiple languages for global customers

### Deployment Options
- **💻 Local AI**: Free open-source models (TinyLlama, Whisper, MMS-TTS) - $0/month
- **☁️ AWS Cloud**: Amazon Bedrock, Transcribe, Polly - ~$0.02/call
- **🚀 OpenAI**: GPT-4, Whisper API, TTS-1 HD - ~$0.02/call

### SaaS Platform (Optional)
- 🏢 Multi-tenant architecture with customer isolation
- 📊 Web dashboard for customer management (port 5000)
- 📤 Customer self-service data upload (PDFs, CSVs, text files)
- 🗄️ PostgreSQL for accounts, vector DB for knowledge base
- 🔐 Auto-generated secure passwords or custom credentials

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- **Linux/WSL2** (Ubuntu 20.04+ recommended)
- **Docker & Docker Compose** (20.10+)
- **Python 3.8+** (for web UI only)
- **4GB RAM minimum** (8GB+ recommended for local AI)

### Option 1: Web UI Setup (Recommended)

**Step 1**: Start the setup wizard
```bash
cd /path/to/call_center_agent
make web-ui
```

**Step 2**: Open your browser
```
http://localhost:8080
```

**Step 3**: Follow the interactive wizard:
1. Choose AI model (Local/AWS/OpenAI)
2. Select communication channel (Telegram/Twilio/SIP)
3. Enable SaaS platform (optional)
4. Configure credentials
5. Click "🚀 Deploy Now"

**That's it!** The system will deploy automatically.

### Option 2: Command Line Setup

```bash
# Interactive CLI wizard
./setup.sh

# Or manual deployment
cp .env.example .env
nano .env  # Edit configuration
make local  # or: make aws, make openai
```

---

## 📋 Configuration Guide

### 1. Telegram Bot Setup

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Paste token in web UI or add to `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

### 2. Phone Integration (Optional)

#### Twilio Setup
1. Create account at [twilio.com](https://www.twilio.com)
2. Get Account SID, Auth Token, and Phone Number
3. Configure in web UI or `.env`:
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxx...
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

#### SIP Trunk Setup
1. Get SIP credentials from your provider (Telia, DNA, Elisa, etc.)
2. Configure in web UI or `.env`:
   ```bash
   SIP_DOMAIN=sip.yourdomain.com
   SIP_USERNAME=your_username
   SIP_PASSWORD=your_password
   ```

### 3. AI Model Configuration

#### Local AI (Free)
- No API keys required
- Runs on your machine
- Models: TinyLlama (1GB), Whisper (base), Elasticsearch
- Best for: Testing, development, privacy-focused

#### AWS Cloud
- Requires AWS account with Bedrock access
- Configure in `.env`:
  ```bash
  AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/...
  AWS_REGION=us-east-1
  ```
- Best for: Production, scalability, enterprise

#### OpenAI
- Requires OpenAI API key from [platform.openai.com](https://platform.openai.com)
- Configure in `.env`:
  ```bash
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4
  ```
- Best for: Best quality, fastest responses

### 4. SaaS Platform (Optional)

Enable multi-tenant mode for multiple customers:

```bash
ENABLE_SAAS=true
POSTGRES_PASSWORD=your_secure_password  # Auto-generated if blank
ADMIN_PASSWORD=your_admin_password      # Auto-generated if blank
```

**SaaS Dashboard**: http://localhost:5000
- Customer signup and management
- Self-service data upload (PDFs, CSVs, text)
- Isolated data per customer
- Vector database storage based on AI model

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Communication Layer                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Telegram │    │  Twilio  │    │SIP Trunk │             │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘             │
└───────┼──────────────┼──────────────┼────────────────────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      Bot Service (Flask)     │
        │   - Message routing          │
        │   - Session management       │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    Voice Service (FastAPI)   │
        │   - Speech-to-Text           │
        │   - Text-to-Speech           │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       AI Provider            │
        │  ┌─────────────────────────┐ │
        │  │ Local: Ollama/Whisper   │ │
        │  │ AWS: Bedrock/Transcribe │ │
        │  │ OpenAI: GPT-4/Whisper   │ │
        │  └─────────────────────────┘ │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      Vector Database         │
        │  - Elasticsearch (Local)     │
        │  - OpenSearch (AWS)          │
        │  - PostgreSQL (OpenAI/SaaS)  │
        └──────────────────────────────┘
```

---

## 📁 Project Structure

```
call_center_agent/
├── setup_web_ui.py              # Web-based setup wizard (port 8080)
├── setup.sh                      # CLI setup wizard
├── Makefile                      # Quick commands
├── .env.example                  # Configuration template
│
├── deployments/                  # Modular deployment configs
│   ├── local/                    # Local AI setup
│   │   ├── docker-compose.yml
│   │   ├── setup.sh
│   │   └── README.md
│   ├── aws/                      # AWS cloud setup
│   ├── openai/                   # OpenAI setup
│   └── saas/                     # Multi-tenant SaaS platform
│
├── app/                          # Core application code
│   ├── bot/                      # Telegram bot logic
│   ├── voice/                    # Voice processing service
│   ├── clients/                  # AI model clients
│   └── services/                 # Business logic
│
├── saas_dashboard/               # Multi-tenant dashboard
│   ├── app.py                    # Flask dashboard app
│   ├── templates/                # HTML templates
│   └── static/                   # CSS, JS assets
│
└── setup_ui/                     # Web setup UI templates
    ├── templates/
    └── static/
```

---

## 🛠️ Available Commands

### Setup
```bash
make web-ui         # Launch web-based setup wizard (recommended)
./setup.sh          # Launch CLI setup wizard
```

### Deployment
```bash
make local          # Deploy with local AI models
make aws            # Deploy with AWS services
make openai         # Deploy with OpenAI services
```

### Management
```bash
make logs           # View logs for running services
make stop           # Stop all services
make clean          # Remove all containers and volumes
```

### Testing
```bash
make test-local     # Test local AI setup
make test-rag       # Test RAG knowledge base
```

---

## 🔧 Advanced Configuration

### Custom AI Models

**Local Ollama Models:**
```bash
# Available models:
OLLAMA_MODEL=tinyllama   # Fast, 1GB (default)
OLLAMA_MODEL=phi         # Balanced, 2GB
OLLAMA_MODEL=mistral     # Better quality, 4GB
```

**Whisper Models:**
```bash
WHISPER_MODEL=base       # 140MB, 90-95% accuracy (default)
WHISPER_MODEL=small      # 460MB, 93-95% accuracy
WHISPER_MODEL=medium     # 1.4GB, 95-97% accuracy
```

### Vector Database Storage

Data storage locations:
- **Local**: `/var/lib/docker/volumes/elasticsearch_data`
- **AWS**: Amazon OpenSearch Service
- **OpenAI**: PostgreSQL + OpenAI embeddings
- **SaaS**: PostgreSQL `/var/lib/docker/volumes/postgres_data`

### Backup & Restore

```bash
# Backup PostgreSQL (SaaS)
docker exec saas_postgres pg_dump -U saas_user saas_db > backup.sql

# Restore PostgreSQL
docker exec -i saas_postgres psql -U saas_user saas_db < backup.sql

# Backup Elasticsearch (Local)
docker exec elasticsearch curl -X PUT "localhost:9200/_snapshot/my_backup"

# Check volumes
docker volume ls
docker volume inspect saas_postgres_data
```

---

## 📊 Performance & Costs

### Response Times
| Deployment | Latency | Quality | Cost/Call |
|------------|---------|---------|-----------|
| Local AI   | 80-140s | Good    | $0        |
| AWS Cloud  | 10-17s  | Great   | ~$0.02    |
| OpenAI     | 4-6s    | Best    | ~$0.02    |

### Resource Requirements
| Component | Local | AWS | OpenAI |
|-----------|-------|-----|--------|
| RAM       | 4-8GB | 2GB | 2GB    |
| CPU       | 4+ cores | 2 cores | 2 cores |
| Storage   | 10GB+ | 5GB | 5GB |

---

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use strong passwords** - Auto-generated by web UI
3. **Rotate API keys regularly** - Every 90 days recommended
4. **Enable HTTPS in production** - Configure nginx reverse proxy
5. **Limit database access** - Use firewall rules
6. **Monitor logs** - Check `make logs` regularly

---

## 🧪 Local Testing with Webhooks

Testing Telegram/Twilio/SIP webhooks locally requires ngrok (creates public HTTPS URL for localhost).

**Quick Start:**
```bash
# Setup ngrok (first time only)
make ngrok-setup

# Start your application
make local

# Start ngrok tunnel (new terminal)
make ngrok
# You'll get: https://abc123.ngrok.io
```

**Configure webhooks with ngrok URL:**
- Telegram: `https://abc123.ngrok.io/telegram/webhook`
- Twilio: `https://abc123.ngrok.io/phone/call`

**📚 Complete guide**: [docs/LOCAL_TESTING.md](docs/LOCAL_TESTING.md)

**Note**: Telegram supports **polling mode** for local testing without ngrok! Just leave `TELEGRAM_WEBHOOK_URL` empty in `.env`.

---

## 🐛 Troubleshooting

### Web UI won't start
```bash
# Check if port 8080 is already in use
lsof -i :8080
pkill -f setup_web_ui.py
python3 setup_web_ui.py
```

### Docker containers won't start
```bash
# Check Docker daemon
sudo systemctl status docker
sudo systemctl start docker

# Check logs
make logs

# Clean restart
make clean
make local  # or aws/openai
```

### Bot not responding
```bash
# Check bot service logs
docker logs -f bot_container_name

# Verify Telegram token
echo $TELEGRAM_BOT_TOKEN

# Test bot manually
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### Out of memory errors
```bash
# Reduce concurrent calls in .env
MAX_CONCURRENT_CALLS=2

# Use smaller models
OLLAMA_MODEL=tinyllama
WHISPER_MODEL=tiny

# Increase Docker memory
# Docker Desktop > Settings > Resources > Memory > 8GB
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Development setup
- Testing requirements

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/call_center_agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/call_center_agent/discussions)
- **Email**: support@yourproject.com

---

## 🗺️ Roadmap

- [ ] Add WhatsApp integration
- [ ] Support for more languages
- [ ] Real-time analytics dashboard
- [ ] A/B testing for responses
- [ ] Sentiment analysis
- [ ] CRM integrations (Salesforce, HubSpot)
- [ ] Kubernetes deployment templates

---

## ⭐ Star History

If this project helps you, please give it a ⭐ on GitHub!

---

**Built with ❤️ for better customer support**
