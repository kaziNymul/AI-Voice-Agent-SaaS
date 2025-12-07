# OpenAI Deployment - GPT-4 & Advanced Models

This deployment uses OpenAI's API for best-in-class AI performance.

## What's Included

- **LLM**: GPT-4, GPT-4 Turbo, or GPT-3.5 Turbo
- **Speech-to-Text**: Whisper (large-v3)
- **Text-to-Speech**: TTS-1 or TTS-1-HD
- **Embeddings**: text-embedding-3-large (3072 dimensions)
- **Vector DB**: Elasticsearch (local)

## Quick Start

1. Get an OpenAI API key from https://platform.openai.com/api-keys

2. Copy `.env.example` to `.env` in the root directory:
   ```bash
   cd /mnt/e/call_center_agent
   cp .env.example .env
   ```

3. Edit `.env` and configure OpenAI:
   ```bash
   DEPLOYMENT=openai
   USE_OPENAI=true
   
   OPENAI_API_KEY=sk-your-api-key
   OPENAI_MODEL=gpt-4
   OPENAI_EMBEDDING_MODEL=text-embedding-3-large
   
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

4. Run setup:
   ```bash
   cd deployments/openai
   ./setup.sh
   ```

5. Your bot is now running on `http://localhost:8001`

## Configuration

Key OpenAI variables in `.env`:

```bash
# Core
DEPLOYMENT=openai
USE_OPENAI=true

# API Key
OPENAI_API_KEY=sk-...

# LLM
OPENAI_MODEL=gpt-4                 # or gpt-4-turbo, gpt-3.5-turbo

# TTS
OPENAI_TTS_MODEL=tts-1             # or tts-1-hd
OPENAI_TTS_VOICE=alloy             # alloy, echo, fable, onyx, nova, shimmer

# STT
OPENAI_WHISPER_MODEL=whisper-1

# Embeddings
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSIONS=3072   # or 1536 for smaller
```

## Performance

- **Latency**: 4-6 seconds voice-to-voice
- **Cost**: ~$0.02 per call (GPT-4)
- **Accuracy**: Best-in-class

### Cost Breakdown (per 1000 calls)

| Service | Usage | Cost |
|---------|-------|------|
| GPT-4 | 150K tokens | $1.80 |
| Whisper | 50 mins audio | $0.30 |
| TTS-1 | 100K chars | $1.50 |
| Embeddings | 50K tokens | $0.007 |
| **Total** | | **~$3.60/1K calls** |

## Available Models

### LLMs
- `gpt-4` - Best reasoning ($30/$60 per 1M tokens)
- `gpt-4-turbo` - Faster GPT-4 ($10/$30 per 1M tokens)
- `gpt-3.5-turbo` - Fast & cheap ($0.50/$1.50 per 1M tokens)

### TTS Voices
- `alloy` - Neutral
- `echo` - Warm, conversational
- `fable` - British accent
- `onyx` - Deep, authoritative
- `nova` - Friendly
- `shimmer` - Soft, clear

### Embedding Models
- `text-embedding-3-large` - 3072 dims, $0.13/1M tokens (recommended)
- `text-embedding-3-small` - 1536 dims, $0.02/1M tokens
- `text-embedding-ada-002` - 1536 dims, $0.10/1M tokens (legacy)

## Advanced: Realtime API

For ultra-low latency (<2 seconds), use OpenAI's Realtime API:

1. Create `deployments/openai-realtime/` (not included by default)
2. Set environment:
   ```bash
   USE_OPENAI_REALTIME=true
   OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
   ```
3. Cost: ~$0.07 per call (5x more than standard)

## Monitoring

View usage in OpenAI dashboard: https://platform.openai.com/usage

Or via API:
```bash
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"
```

## Troubleshooting

**"Insufficient quota"?**
Add credits to your OpenAI account or upgrade to paid tier.

**High costs?**
- Switch to `gpt-3.5-turbo` (10x cheaper)
- Use `tts-1` instead of `tts-1-hd`
- Reduce `OPENAI_EMBEDDING_DIMENSIONS` to 1536

**Rate limits?**
Upgrade your OpenAI tier or implement request throttling.

## Embeddings Comparison

| Model | Dimensions | Cost | Quality |
|-------|-----------|------|---------|
| text-embedding-3-large | 3072 | $0.13/1M | Best |
| text-embedding-3-small | 1536 | $0.02/1M | Good |
| Local (MiniLM) | 384 | Free | Basic |

Higher dimensions = better retrieval accuracy for complex queries.
