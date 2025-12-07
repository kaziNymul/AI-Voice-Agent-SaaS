# Local Deployment - Free AI Models

This deployment uses completely free, locally-running AI models. No API keys required!

## What's Included

- **LLM**: TinyLlama (600MB) via Ollama
- **Speech-to-Text**: Whisper Tiny
- **Text-to-Speech**: MMS-TTS
- **Embeddings**: all-MiniLM-L6-v2 (384 dimensions)
- **Vector DB**: Elasticsearch

## System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 5GB free space
- **CPU**: x86_64 or ARM64

## Quick Start

1. Copy `.env.example` to `.env` in the root directory:
   ```bash
   cd /mnt/e/call_center_agent
   cp .env.example .env
   ```

2. Edit `.env` and set:
   ```bash
   DEPLOYMENT=local
   USE_LOCAL_MODELS=true
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

3. Run setup:
   ```bash
   cd deployments/local
   ./setup.sh
   ```

4. Your bot is now running on `http://localhost:8001`

## Configuration

All configuration is in the root `.env` file. Key variables:

```bash
# Core settings
DEPLOYMENT=local
CUSTOMER_ID=1
TELEGRAM_BOT_TOKEN=your_token

# Local AI
USE_LOCAL_MODELS=true
LLM_MODEL=tinyllama
LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Resource limits
VOICE_MEMORY_LIMIT=3g
OLLAMA_MEMORY_LIMIT=2g
ES_MEMORY_LIMIT=512m
BOT_MEMORY_LIMIT=512m
```

## Performance

- **Latency**: 80-140 seconds voice-to-voice
- **Cost**: $0/month (only server costs)
- **Accuracy**: Good for basic customer care

## Containers

This deployment starts 4 containers:
- `test_ollama` - TinyLlama LLM
- `test_voice` - Whisper + MMS-TTS
- `test_elasticsearch` - Vector database
- `test_bot` - Main bot application

## Troubleshooting

**Out of memory?**
Reduce memory limits in `.env`:
```bash
VOICE_MEMORY_LIMIT=2g
OLLAMA_MEMORY_LIMIT=1g
```

**Ollama not responding?**
Check logs:
```bash
docker logs test_ollama
```

**Voice timeout?**
Increase timeouts in `.env`:
```bash
STT_TIMEOUT=180
TTS_TIMEOUT=180
```

## Upgrading to Cloud

To switch to AWS or OpenAI:
1. Change `DEPLOYMENT=aws` or `DEPLOYMENT=openai` in `.env`
2. Add API keys to `.env`
3. Run `cd ../aws && ./setup.sh` or `cd ../openai && ./setup.sh`
