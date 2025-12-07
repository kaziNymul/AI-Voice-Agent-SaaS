# Local Testing with Ngrok

This guide helps you test Telegram, Twilio, or SIP webhooks on your local machine using ngrok.

## Why Ngrok?

When developing locally (`localhost:8000`), external services like Telegram and Twilio cannot reach your application because:
- **Localhost is not publicly accessible** - It only works on your machine
- **Telegram webhooks require HTTPS** - Telegram only accepts secure connections
- **Twilio webhooks require public URL** - Must be accessible from the internet

**Ngrok creates a secure tunnel** from the internet to your localhost, giving you:
- ✅ Public HTTPS URL (e.g., `https://abc123.ngrok.io`)
- ✅ Works with Telegram webhooks
- ✅ Works with Twilio webhooks
- ✅ Works with SIP trunk testing

## Quick Start

### 1. Install Ngrok

```bash
# Setup ngrok (includes installation guide)
make ngrok-setup

# Or manually:
# Download from https://ngrok.com/download
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
sudo tar xvzf ngrok-v3-stable-linux-amd64.tgz -C /usr/local/bin

# Get auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 2. Start Your Application

```bash
# Deploy locally first
make local

# Verify it's running
curl http://localhost:8000/health
```

### 3. Start Ngrok Tunnel

```bash
# Start ngrok (keep this terminal open)
make ngrok

# You'll see output like:
# Forwarding: https://abc123.ngrok.io -> http://localhost:8000
```

### 4. Configure Webhooks

Use your ngrok URL instead of localhost.

#### For Telegram:

```bash
# Set webhook to your ngrok URL
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok.io/telegram/webhook"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

#### For Twilio:

1. Go to Twilio Console: https://console.twilio.com/
2. Navigate to: **Phone Numbers** → **Manage** → **Active Numbers**
3. Click your phone number
4. Under **Voice Configuration**:
   - **A Call Comes In**: Webhook
   - URL: `https://abc123.ngrok.io/phone/call`
   - HTTP: POST
5. Click **Save**

#### For SIP Trunk:

Configure your SIP provider to send traffic to:
```
SIP URI: https://abc123.ngrok.io/phone/sip/call
```

## Testing Flow

```
┌─────────────────┐
│  Telegram User  │
└────────┬────────┘
         │ Message
         ▼
┌─────────────────┐
│ Telegram Server │
└────────┬────────┘
         │ Webhook POST
         ▼
┌─────────────────┐      ┌──────────────┐
│ Ngrok (Public)  │─────▶│ Your PC      │
│ abc123.ngrok.io │      │ localhost:8000│
└─────────────────┘      └──────────────┘
```

## Common Issues

### Issue 1: "ERR_NGROK_108" - Session Expired

**Problem**: Free ngrok URLs expire after 2 hours or when you restart ngrok.

**Solution**: 
```bash
# Stop ngrok (Ctrl+C)
# Restart to get new URL
make ngrok

# Update webhook with new URL
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://NEW_URL.ngrok.io/telegram/webhook"
```

### Issue 2: Telegram webhook returns 401 Unauthorized

**Problem**: Bot token mismatch.

**Solution**: Verify your token in `.env` matches the webhook:
```bash
grep TELEGRAM_BOT_TOKEN .env
```

### Issue 3: Ngrok dashboard shows 404 errors

**Problem**: Wrong webhook endpoint.

**Solution**: Check endpoints:
- Telegram: `/telegram/webhook` (not `/webhook`)
- Twilio: `/phone/call` (not `/call`)

### Issue 4: "ngrok: command not found"

**Solution**:
```bash
make ngrok-setup
# Follow installation instructions
```

## Ngrok Dashboard

View incoming requests in real-time:
```
Web Interface: http://127.0.0.1:4040
```

This shows:
- All HTTP requests received
- Request/response headers
- Request body
- Response status

Perfect for debugging webhook issues!

## Production Deployment

⚠️ **Ngrok is for TESTING ONLY** - Don't use in production!

For production:
1. Deploy to a cloud server (AWS, DigitalOcean, etc.)
2. Use your actual domain: `https://yourdomain.com`
3. Configure nginx with SSL certificates
4. Update webhooks to production URL

See: [Production Deployment Guide](../README.md#production-deployment)

## Telegram Polling vs Webhooks

**Alternative for local testing**: Use **polling mode** instead of webhooks!

### Polling Mode (No Ngrok Needed)

```python
# In your .env - don't set TELEGRAM_WEBHOOK_URL
TELEGRAM_BOT_TOKEN=your_token_here
# Leave TELEGRAM_WEBHOOK_URL empty or commented out

# The bot will automatically use polling mode
# No ngrok or public URL required!
```

**Polling mode**:
- ✅ Works on localhost without ngrok
- ✅ No webhook configuration needed
- ✅ Perfect for development
- ⚠️ Higher latency (polls every 1-2 seconds)
- ❌ Not recommended for production

**Webhook mode** (requires ngrok locally):
- ✅ Instant message delivery
- ✅ Lower server load
- ✅ Production-ready
- ❌ Requires public HTTPS URL
- ❌ Need ngrok for local testing

### Which to Use?

| Scenario | Recommendation |
|----------|---------------|
| Local development (Telegram only) | **Polling mode** - No ngrok needed |
| Local testing with Twilio | **Webhook mode + ngrok** - Required |
| Local testing with SIP trunk | **Webhook mode + ngrok** - Required |
| Cloud deployment | **Webhook mode** - Best performance |

## Commands Reference

```bash
# Setup ngrok (first time)
make ngrok-setup

# Start ngrok tunnel
make ngrok

# Start on different port
./scripts/start_ngrok.sh 8001

# Check if ngrok is running
curl http://127.0.0.1:4040/api/tunnels

# Stop ngrok
# Press Ctrl+C in the ngrok terminal
```

## Free vs Paid Ngrok

### Free Plan:
- ✅ 1 online ngrok process
- ✅ 4 tunnels per process
- ✅ 40 connections/minute
- ⚠️ Random subdomain (changes on restart)
- ⚠️ Session expires after 2 hours

### Paid Plan ($8/month):
- ✅ Custom subdomain (e.g., `mybot.ngrok.io`)
- ✅ Multiple processes
- ✅ No session timeout
- ✅ Higher rate limits

For casual testing, free plan is sufficient!

## Summary

**Telegram-only local testing**:
```bash
# Use polling mode - no ngrok needed
# Just leave TELEGRAM_WEBHOOK_URL empty in .env
make local
```

**Twilio/SIP local testing**:
```bash
# Requires ngrok for webhooks
make ngrok-setup    # First time only
make local          # Start your app
make ngrok          # Start tunnel (new terminal)
# Configure Twilio with ngrok URL
```

**Production**:
```bash
# Deploy to cloud with real domain
# No ngrok needed
```
