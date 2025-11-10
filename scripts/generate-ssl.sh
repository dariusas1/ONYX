#!/bin/bash

# SSL Certificate Generation Script for ONYX Development
# Generates self-signed SSL certificates for localhost development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SSL_DIR="nginx/ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"
COUNTRY="US"
STATE="CA"
CITY="San Francisco"
ORGANIZATION="ONYX"
ORG_UNIT="Development"
COMMON_NAME="localhost"
DAYS_VALID=365

echo -e "${GREEN}🔐 ONYX SSL Certificate Generation Script${NC}"
echo "=================================="

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ Error: OpenSSL is not installed or not in PATH${NC}"
    echo "Please install OpenSSL before running this script."
    exit 1
fi

# Create SSL directory if it doesn't exist
if [ ! -d "$SSL_DIR" ]; then
    echo -e "${YELLOW}📁 Creating SSL directory: $SSL_DIR${NC}"
    mkdir -p "$SSL_DIR"
fi

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}⚠️  SSL certificates already exist!${NC}"
    read -p "Do you want to overwrite them? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "SSL certificate generation cancelled."
        exit 0
    fi
fi

echo -e "${YELLOW}🔑 Generating self-signed SSL certificate...${NC}"

# Generate the certificate
openssl req -x509 -nodes -days "$DAYS_VALID" -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORG_UNIT/CN=$COMMON_NAME"

# Set appropriate permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo -e "${GREEN}✅ SSL certificates generated successfully!${NC}"
echo
echo "Certificate details:"
echo "  📁 Directory: $SSL_DIR"
echo "  🔒 Private Key: $KEY_FILE"
echo "  📜 Certificate: $CERT_FILE"
echo "  ⏰ Valid for: $DAYS_VALID days"
echo "  🌐 Common Name: $COMMON_NAME"
echo
echo -e "${YELLOW}📋 Certificate Information:${NC}"
openssl x509 -in "$CERT_FILE" -text -noout | grep -A 2 "Subject:"
echo
echo -e "${GREEN}🚀 Ready for HTTPS development!${NC}"
echo "You can now access your ONYX application via https://localhost"
echo
echo -e "${YELLOW}⚠️  Note: This is a self-signed certificate for development only.${NC}"
echo "Your browser will show a security warning - this is expected and safe for development."