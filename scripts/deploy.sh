#!/bin/bash

# =============================================================================
# ONYX Deployment Script
# =============================================================================
# 
# This script deploys ONYX services to a remote VPS using Docker Compose.
# It's designed to be called from GitHub Actions with proper environment variables.
#
# Usage: ./deploy.sh [staging|production]
# =============================================================================

set -euo pipefail

# Configuration
DEPLOYMENT_ENV=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting ONYX deployment to $DEPLOYMENT_ENV..."

# Validate deployment environment
if [[ "$DEPLOYMENT_ENV" != "staging" && "$DEPLOYMENT_ENV" != "production" ]]; then
    echo "❌ Invalid deployment environment: $DEPLOYMENT_ENV"
    echo "   Usage: $0 [staging|production]"
    exit 1
fi

# Required environment variables
required_vars=(
    "VPS_HOST"
    "VPS_USER"
    "SSH_PRIVATE_KEY"
    "REGISTRY"
    "IMAGE_NAME"
    "COMMIT_SHA"
)

# Check required variables
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

# Create SSH directory and key file
SSH_DIR="$HOME/.ssh"
mkdir -p "$SSH_DIR"
echo "$SSH_PRIVATE_KEY" > "$SSH_DIR/deploy_key"
chmod 600 "$SSH_DIR/deploy_key"

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SSH_DIR/deploy_key"

# Remote deployment directory
REMOTE_DIR="/opt/onyx-$DEPLOYMENT_ENV"

echo "📡 Connecting to VPS: $VPS_USER@$VPS_HOST"

# Prepare remote directory
ssh $SSH_OPTS $VPS_USER@$VPS_HOST << EOF
    set -euo pipefail
    
    echo "📁 Preparing deployment directory..."
    sudo mkdir -p $REMOTE_DIR
    sudo chown $VPS_USER:$VPS_USER $REMOTE_DIR
    
    # Create docker-compose override file
    cat > $REMOTE_DIR/docker-compose.override.yml << 'EOL'
version: '3.8'
services:
  suna:
    image: ${REGISTRY}/${IMAGE_NAME}/suna:${DEPLOYMENT_ENV}-${COMMIT_SHA}
    restart: unless-stopped
    
  onyx-core:
    image: ${REGISTRY}/${IMAGE_NAME}/onyx-core:${DEPLOYMENT_ENV}-${COMMIT_SHA}
    restart: unless-stopped
    
  nginx:
    image: ${REGISTRY}/${IMAGE_NAME}/nginx:${DEPLOYMENT_ENV}-${COMMIT_SHA}
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
EOL

    echo "🐳 Pulling latest images..."
    cd $REMOTE_DIR
    docker compose -f docker-compose.yml -f docker-compose.override.yml pull
    
    echo "🔄 Restarting services..."
    docker compose -f docker-compose.yml -f docker-compose.override.yml down
    docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
    
    echo "🧹 Cleaning up old images..."
    docker image prune -f
    
    echo "✅ Deployment completed successfully!"
EOF

# Health check
echo "🏥 Performing health check..."
sleep 10

HEALTH_CHECK_URL="http://$VPS_HOST/health"
if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
    echo "✅ Health check passed - deployment is healthy!"
else
    echo "❌ Health check failed - deployment may have issues"
    exit 1
fi

# Cleanup SSH key
rm -f "$SSH_DIR/deploy_key"

echo "🎉 ONYX deployment to $DEPLOYMENT_ENV completed successfully!"