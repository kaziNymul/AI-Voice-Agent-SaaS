#!/bin/bash
# Setup Nginx with SSL for Customer Care System
# Run this script on your server after deploying the app

set -e

echo "================================================"
echo "Setting up Nginx + SSL for Customer Care"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./setup_nginx.sh)"
    exit 1
fi

# Get domain from environment variable or prompt
if [ -z "$DOMAIN" ]; then
    echo ""
    echo "IMPORTANT: You need a domain name that points to this server!"
    echo "See DOMAIN_SETUP.md for instructions on buying and configuring a domain."
    echo ""
    read -p "Enter your domain name (e.g., customercare.example.com): " DOMAIN
fi

if [ -z "$EMAIL" ]; then
    read -p "Enter your email for SSL certificate (for Let's Encrypt): " EMAIL
fi

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Domain and email are required!"
    exit 1
fi

# Verify DNS is configured
echo ""
echo "Checking DNS configuration for $DOMAIN..."
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short "$DOMAIN" | tail -n1)

if [ -z "$DOMAIN_IP" ]; then
    echo "⚠️  WARNING: Domain $DOMAIN does not resolve to any IP!"
    echo "You need to configure DNS first. See DOMAIN_SETUP.md"
    echo ""
    echo "Current server IP: $SERVER_IP"
    echo "DNS should point to: $SERVER_IP"
    echo ""
    read -p "Continue anyway? (not recommended) [y/N]: " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
elif [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    echo "⚠️  WARNING: DNS mismatch!"
    echo "Domain $DOMAIN points to: $DOMAIN_IP"
    echo "This server's IP is: $SERVER_IP"
    echo ""
    echo "SSL certificate will fail if DNS is wrong."
    echo "Update DNS A record to point to $SERVER_IP"
    echo ""
    read -p "Continue anyway? (not recommended) [y/N]: " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
else
    echo "✅ DNS configured correctly: $DOMAIN → $SERVER_IP"
fi

echo ""
echo "Installing Nginx and Certbot..."
apt update
apt install -y nginx certbot python3-certbot-nginx

echo ""
echo "Creating Nginx configuration..."

# Create config file
cat > /etc/nginx/sites-available/customer-care << EOF
# Rate limiting zones
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=webhook_limit:10m rate=30r/s;

# Upstream - Docker app
upstream customer_care_app {
    server localhost:8000;
    keepalive 32;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Logging
    access_log /var/log/nginx/customer-care-access.log;
    error_log /var/log/nginx/customer-care-error.log warn;
    
    # Max upload size
    client_max_body_size 25M;
    
    # Main location
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
    
    # Webhooks - higher rate limit
    location ~ ^/(telegram|twilio)/ {
        limit_req zone=webhook_limit burst=50 nodelay;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Health check - no rate limit
    location /health {
        proxy_pass http://customer_care_app/health;
        access_log off;
        proxy_connect_timeout 5s;
    }
}
EOF

echo ""
echo "Enabling site..."
ln -sf /etc/nginx/sites-available/customer-care /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test config
echo ""
echo "Testing Nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    echo "Nginx configuration test failed!"
    exit 1
fi

# Create certbot directory
mkdir -p /var/www/certbot

# Restart Nginx
echo ""
echo "Restarting Nginx..."
systemctl restart nginx

# Get SSL certificate
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo "This will ask you to agree to the Terms of Service."
echo ""

certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ SUCCESS! Nginx + SSL configured"
    echo "================================================"
    echo ""
    echo "Your site is now available at:"
    echo "  https://$DOMAIN"
    echo ""
    echo "SSL certificate will auto-renew."
    echo "Check renewal: sudo certbot renew --dry-run"
    echo ""
    echo "Next steps:"
    echo "  1. Make sure your app is running (docker-compose ps)"
    echo "  2. Test: curl https://$DOMAIN/health"
    echo "  3. Configure Telegram/Twilio webhook to https://$DOMAIN"
    echo ""
else
    echo ""
    echo "SSL certificate installation failed!"
    echo "Make sure:"
    echo "  1. Domain $DOMAIN points to this server's IP"
    echo "  2. Ports 80 and 443 are open in firewall"
    echo "  3. No other web server is running"
    exit 1
fi
