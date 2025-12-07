# AWS Deployment - Cloud AI Services

This deployment uses AWS managed AI services for production-grade performance.

## What's Included

- **LLM**: Amazon Bedrock (Claude 3 Haiku/Sonnet)
- **Speech-to-Text**: Amazon Transcribe (streaming)
- **Text-to-Speech**: Amazon Polly (neural voices)
- **Embeddings**: Bedrock Titan Embeddings
- **Vector DB**: Amazon OpenSearch

## AWS Setup

### 1. IAM Permissions

Create an IAM user with these policies:
- `AmazonBedrockFullAccess`
- `AmazonTranscribeFullAccess`
- `AmazonPollyFullAccess`
- `AmazonOpenSearchServiceFullAccess`

### 2. Enable Bedrock Models

Go to AWS Bedrock console → Model access → Request access for:
- Claude 3 Haiku
- Claude 3 Sonnet (optional)
- Titan Embeddings G1

### 3. Create OpenSearch Domain

```bash
aws opensearch create-domain \
  --domain-name customer-qa \
  --engine-version OpenSearch_2.7 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1 \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=20
```

## Quick Start

1. Copy `.env.example` to `.env` in the root directory:
   ```bash
   cd /mnt/e/call_center_agent
   cp .env.example .env
   ```

2. Edit `.env` and configure AWS:
   ```bash
   DEPLOYMENT=aws
   USE_AWS_SERVICES=true
   
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   
   AWS_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
   AWS_OPENSEARCH_ENDPOINT=https://your-domain.us-east-1.es.amazonaws.com
   AWS_POLLY_VOICE_ID=Joanna
   
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

3. Run setup:
   ```bash
   cd deployments/aws
   ./setup.sh
   ```

4. Your bot is now running on `http://localhost:8001`

## Configuration

Key AWS variables in `.env`:

```bash
# Core
DEPLOYMENT=aws
USE_AWS_SERVICES=true

# Credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Bedrock LLM
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_MAX_TOKENS=1024
BEDROCK_TEMPERATURE=0.7

# Transcribe STT
AWS_TRANSCRIBE_LANGUAGE=en-US

# Polly TTS
AWS_POLLY_VOICE_ID=Joanna
AWS_POLLY_ENGINE=neural

# OpenSearch
AWS_OPENSEARCH_ENDPOINT=https://...
AWS_OPENSEARCH_INDEX=customer_qa
```

## Performance

- **Latency**: 10-17 seconds voice-to-voice
- **Cost**: ~$0.01-0.03 per call
- **Accuracy**: Production-grade

### Cost Breakdown (per 1000 calls)

| Service | Usage | Cost |
|---------|-------|------|
| Bedrock (Haiku) | 150K tokens | $0.04 |
| Transcribe | 50 mins | $1.20 |
| Polly | 100K chars | $1.60 |
| OpenSearch | t3.small | $43/month |
| **Total** | | **$46/month + $2.84/1K calls** |

## Available Models

### Bedrock LLMs
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast, cheap ($0.25/$1.25 per 1M tokens)
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced ($3/$15 per 1M tokens)
- `anthropic.claude-3-opus-20240229-v1:0` - Best quality ($15/$75 per 1M tokens)

### Polly Voices (Neural)
English: Joanna (F), Matthew (M), Ivy (F, child), Kevin (M, child)
Spanish: Lupe (F), Pedro (M)
French: Léa (F), Rémi (M)
German: Vicki (F), Daniel (M)
Japanese: Takumi (M), Kazuha (F)

## Monitoring

View CloudWatch metrics:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Troubleshooting

**"AccessDeniedException"?**
Check IAM permissions and Bedrock model access.

**High latency?**
Try a faster region or upgrade OpenSearch instance.

**High costs?**
Switch to Claude 3 Haiku for cheaper inference.
