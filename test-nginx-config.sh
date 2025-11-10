#!/bin/bash

# Test script for nginx reverse proxy configuration
# This script tests the nginx configuration and SSL certificates

echo "=== Testing Nginx Reverse Proxy Configuration ==="
echo

# Test 1: Check SSL certificates
echo "1. Testing SSL certificates..."
if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/key.pem" ]; then
    echo "✅ SSL certificate files exist"
    
    # Check certificate validity
    if openssl x509 -in nginx/ssl/cert.pem -checkend 86400 -noout; then
        echo "✅ SSL certificate is valid for at least 24 hours"
    else
        echo "❌ SSL certificate is expired or expires soon"
    fi
    
    # Check certificate subject
    subject=$(openssl x509 -in nginx/ssl/cert.pem -noout -subject | cut -d'=' -f6)
    if [ "$subject" = "localhost" ]; then
        echo "✅ SSL certificate is issued for localhost"
    else
        echo "❌ SSL certificate subject is not localhost: $subject"
    fi
else
    echo "❌ SSL certificate files missing"
fi

echo

# Test 2: Check nginx configuration syntax (structure only)
echo "2. Testing nginx configuration structure..."
if [ -f "nginx/nginx.conf" ]; then
    echo "✅ nginx.conf exists"
    
    # Check for required upstream blocks
    if grep -q "upstream suna_backend" nginx/nginx.conf; then
        echo "✅ suna_backend upstream found"
    else
        echo "❌ suna_backend upstream missing"
    fi
    
    if grep -q "upstream novnc_backend" nginx/nginx.conf; then
        echo "✅ novnc_backend upstream found"
    else
        echo "❌ novnc_backend upstream missing"
    fi
    
    # Check for location blocks
    if grep -q "location /chat/" nginx/nginx.conf; then
        echo "✅ /chat/ location block found"
    else
        echo "❌ /chat/ location block missing"
    fi
    
    if grep -q "location /api/" nginx/nginx.conf; then
        echo "✅ /api/ location block found"
    else
        echo "❌ /api/ location block missing"
    fi
    
    if grep -q "location /vnc/" nginx/nginx.conf; then
        echo "✅ /vnc/ location block found"
    else
        echo "❌ /vnc/ location block missing"
    fi
    
    # Check for SSL configuration
    if grep -q "listen 443 ssl" nginx/nginx.conf; then
        echo "✅ HTTPS listener found"
    else
        echo "❌ HTTPS listener missing"
    fi
    
    # Check for CORS headers
    if grep -q "Access-Control-Allow-Origin" nginx/nginx.conf; then
        echo "✅ CORS headers configured"
    else
        echo "❌ CORS headers missing"
    fi
    
    # Check for rate limiting
    if grep -q "limit_req_zone" nginx/nginx.conf; then
        echo "✅ Rate limiting configured"
    else
        echo "❌ Rate limiting missing"
    fi
    
    # Check for gzip compression
    if grep -q "gzip on" nginx/nginx.conf; then
        echo "✅ Gzip compression enabled"
    else
        echo "❌ Gzip compression missing"
    fi
else
    echo "❌ nginx.conf missing"
fi

echo

# Test 3: Check Docker Compose configuration
echo "3. Testing Docker Compose configuration..."
if [ -f "docker-compose.yaml" ]; then
    echo "✅ docker-compose.yaml exists"
    
    # Check for nginx service
    if grep -q "nginx:" docker-compose.yaml; then
        echo "✅ nginx service found"
    else
        echo "❌ nginx service missing"
    fi
    
    # Check for SSL volume mount
    if grep -q "./nginx/ssl:/etc/nginx/ssl" docker-compose.yaml; then
        echo "✅ SSL volume mount found"
    else
        echo "❌ SSL volume mount missing"
    fi
    
    # Check for port mappings
    if grep -q "80:80" docker-compose.yaml && grep -q "443:443" docker-compose.yaml; then
        echo "✅ HTTP and HTTPS ports mapped"
    else
        echo "❌ Port mappings incomplete"
    fi
else
    echo "❌ docker-compose.yaml missing"
fi

echo
echo "=== Test Summary ==="
echo "Run this script after starting the services to test actual functionality:"
echo "curl -k https://localhost/health"
echo "curl -k https://localhost/api/health"
echo "curl -I -k https://localhost/vnc/"