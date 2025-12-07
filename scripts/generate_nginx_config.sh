#!/bin/bash
# Generate nginx configuration from BASE_URL in .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Load BASE_URL from .env
BASE_URL=$(grep "^BASE_URL=" "$ENV_FILE" | cut -d '=' -f 2- | tr -d '"' | tr -d "'")

if [ -z "$BASE_URL" ]; then
    echo "⚠️  No BASE_URL found in .env"
    echo "Nginx configuration not generated (not required for local deployment)"
    exit 0
fi

# Extract domain from BASE_URL
DOMAIN=$(echo "$BASE_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||' -e 's|:.*$||')

if [ -z "$DOMAIN" ]; then
    echo "❌ Could not extract domain from BASE_URL: $BASE_URL"
    exit 1
fi

echo "📝 Generating nginx configuration for domain: $DOMAIN"

# Determine if HTTP or HTTPS
if [[ "$BASE_URL" == https://* ]]; then
    USE_HTTPS=true
else
    USE_HTTPS=false
fi

# Generate nginx config
OUTPUT_FILE="$ROOT_DIR/nginx/customer-care-generated.conf"

cat > "$OUTPUT_FILE" << EOF
# Nginx Configuration for AI Customer Care System
# Auto-generated from BASE_URL: $BASE_URL
# 
# To use this configuration:
# 1. Copy to your server: scp nginx/customer-care-generated.conf user@server:/tmp/
# 2. Move to nginx: sudo mv /tmp/customer-care-generated.conf /etc/nginx/sites-available/customer-care
# 3. Create symlink: sudo ln -s /etc/nginx/sites-available/customer-care /etc/nginx/sites-enabled/
# 4. Test config: sudo nginx -t
# 5. Reload nginx: sudo systemctl reload nginx

# Rate limiting zone - prevents abuse
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=webhook_limit:10m rate=30r/s;

# Upstream - your Docker app
upstream customer_care_app {
    server localhost:8000;
    keepalive 32;
}

EOF

if [ "$USE_HTTPS" = true ]; then
    # HTTPS configuration
    cat >> "$OUTPUT_FILE" << EOF
# HTTP server - redirect all to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    
    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other requests to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL certificates (obtain with: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL configuration - Mozilla Intermediate
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Logging
    access_log /var/log/nginx/customer-care-access.log;
    error_log /var/log/nginx/customer-care-error.log warn;
    
    # Max upload size (for audio files)
    client_max_body_size 25M;
    
    # Root location - general API endpoints
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        
        # Proxy headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering off;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Telegram webhook - higher rate limit
    location /telegram/ {
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
    
    # Twilio/Phone webhook - higher rate limit
    location /phone/ {
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
    
    # Health check endpoint - no rate limit, no logging
    location /health {
        proxy_pass http://customer_care_app/health;
        access_log off;
        
        proxy_set_header Host \$host;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # Admin endpoints - stricter rate limit
    location /admin/ {
        limit_req zone=api_limit burst=5 nodelay;
        
        # Optional: Restrict to specific IPs
        # allow 123.45.67.89;  # Your office IP
        # deny all;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
else
    # HTTP only configuration (for IP addresses or local testing)
    cat >> "$OUTPUT_FILE" << EOF
# HTTP server (no SSL)
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN _;
    
    # Logging
    access_log /var/log/nginx/customer-care-access.log;
    error_log /var/log/nginx/customer-care-error.log warn;
    
    # Max upload size (for audio files)
    client_max_body_size 25M;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Root location - general API endpoints
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        
        # Proxy headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering off;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Telegram webhook - higher rate limit
    location /telegram/ {
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
    
    # Twilio/Phone webhook - higher rate limit
    location /phone/ {
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
    
    # Health check endpoint - no rate limit, no logging
    location /health {
        proxy_pass http://customer_care_app/health;
        access_log off;
        
        proxy_set_header Host \$host;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # Admin endpoints - stricter rate limit
    location /admin/ {
        limit_req zone=api_limit burst=5 nodelay;
        
        proxy_pass http://customer_care_app;
        proxy_http_version 1.1;
        
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
fi

chmod +x "$OUTPUT_FILE"

echo "✅ Nginx configuration generated: $OUTPUT_FILE"
echo ""
echo "📋 Next steps:"
echo "1. Copy to server: scp $OUTPUT_FILE user@$DOMAIN:/tmp/customer-care.conf"
echo "2. On server, move to nginx: sudo mv /tmp/customer-care.conf /etc/nginx/sites-available/customer-care"
echo "3. Create symlink: sudo ln -s /etc/nginx/sites-available/customer-care /etc/nginx/sites-enabled/"

if [ "$USE_HTTPS" = true ]; then
    echo "4. Obtain SSL certificate: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
    echo "5. Test config: sudo nginx -t"
    echo "6. Reload nginx: sudo systemctl reload nginx"
else
    echo "4. Test config: sudo nginx -t"
    echo "5. Reload nginx: sudo systemctl reload nginx"
fi
