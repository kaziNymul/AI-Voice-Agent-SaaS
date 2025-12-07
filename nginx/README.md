# Nginx Configuration Files

This directory contains Nginx configuration for production deployment.

## Files

- **`customer-care.conf`** - Template configuration (manual editing required)
- **`customer-care-generated.conf`** - Auto-generated from your BASE_URL (recommended)
- **`saas-platform.conf`** - Template for SaaS multi-tenant deployment
- **`setup_nginx.sh`** - Automated setup script

## Quick Setup

### Method 1: Auto-Generated (Recommended)

When you use the **Web UI setup wizard** and provide a Server URL, an nginx configuration is automatically generated:

```bash
# 1. Run web UI and enter your domain
make web-ui
# Enter your domain in Step 2: e.g., https://callcenter.mycompany.com

# 2. Generated file will be at: nginx/customer-care-generated.conf

# 3. Copy to your server
scp nginx/customer-care-generated.conf user@yourserver:/tmp/

# 4. On server, install and configure
sudo mv /tmp/customer-care-generated.conf /etc/nginx/sites-available/customer-care
sudo ln -s /etc/nginx/sites-available/customer-care /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 5. If using HTTPS, obtain SSL certificate
sudo certbot --nginx -d yourdomain.com
```

Or manually generate the config:

```bash
./scripts/generate_nginx_config.sh
```

### Method 2: Automated Setup Script

```bash
sudo chmod +x nginx/setup_nginx.sh
sudo ./nginx/setup_nginx.sh
```

The script will:
1. Install Nginx and Certbot
2. Create configuration
3. Obtain SSL certificate from Let's Encrypt
4. Configure HTTPS with security headers
5. Set up rate limiting

### Manual Setup

```bash
# 1. Install Nginx and Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 2. Copy configuration
sudo cp nginx/customer-care.conf /etc/nginx/sites-available/customer-care

# 3. Edit domain name
sudo nano /etc/nginx/sites-available/customer-care
# Replace "yourdomain.com" with your actual domain

# 4. Enable site
sudo ln -s /etc/nginx/sites-available/customer-care /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site

# 5. Test configuration
sudo nginx -t

# 6. Restart Nginx
sudo systemctl restart nginx

# 7. Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Configuration Features

✅ **HTTPS/SSL** - Automatic Let's Encrypt certificates  
✅ **HTTP/2** - Faster page loads  
✅ **Security Headers** - HSTS, X-Frame-Options, etc.  
✅ **Rate Limiting** - Prevent abuse  
✅ **Webhook Optimization** - Higher limits for Telegram/Twilio  
✅ **Health Check** - No rate limit for monitoring  
✅ **Gzip Compression** - Reduce bandwidth  

## Important Endpoints

| Path | Rate Limit | Purpose |
|------|------------|---------|
| `/` | 10 req/s | General API |
| `/telegram/` | 30 req/s | Telegram webhooks |
| `/twilio/` | 30 req/s | Twilio webhooks |
| `/health` | Unlimited | Health checks |
| `/admin/` | 5 req/s | Admin panel |

## Testing

```bash
# Test health endpoint
curl https://yourdomain.com/health

# Test SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check Nginx status
sudo systemctl status nginx

# View logs
sudo tail -f /var/log/nginx/customer-care-access.log
sudo tail -f /var/log/nginx/customer-care-error.log
```

## SSL Certificate Renewal

Certificates auto-renew. Test renewal:

```bash
sudo certbot renew --dry-run
```

Certbot adds a cron job automatically.

## Firewall

Make sure these ports are open:

```bash
sudo ufw allow 80/tcp   # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 22/tcp   # SSH
sudo ufw enable
```

## Troubleshooting

### Port already in use
```bash
# Check what's using port 80/443
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # if Apache is running
```

### SSL certificate failed
```bash
# Make sure domain points to your server
dig +short yourdomain.com

# Should return your server's IP
```

### 502 Bad Gateway
```bash
# Check if app is running
docker-compose ps

# Check app logs
docker-compose logs app

# Restart app
docker-compose restart app
```

### Rate limit errors
Edit `/etc/nginx/sites-available/customer-care` and increase:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;  # Increase from 10r/s
```

Then reload:
```bash
sudo nginx -s reload
```

## Production Recommendations

1. **Monitor logs** - Set up log rotation
2. **Use Fail2ban** - Block brute force attacks
3. **CloudFlare** - Add CDN layer (optional)
4. **Backup** - Backup `/etc/nginx/sites-available/`
5. **Monitoring** - Use UptimeRobot or similar

## Need Help?

See `SERVER_INFRASTRUCTURE.md` for complete deployment guide.
