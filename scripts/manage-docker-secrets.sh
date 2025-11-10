#!/bin/bash

# =============================================================================
# ONYX Docker Secrets Management Script
# =============================================================================
# This script helps manage Docker secrets for production deployment
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 ONYX Docker Secrets Management${NC}"
echo "=================================="

# Function to generate secure random values
generate_secure_value() {
    local type="$1"
    local length="$2"
    
    case "$type" in
        "hex")
            openssl rand -hex "$length" 2>/dev/null || head -c "$((length * 2))" /dev/urandom | xxd -p | tr -d '\n'
            ;;
        "base64")
            openssl rand -base64 "$length" 2>/dev/null || head -c "$length" /dev/urandom | base64 | tr -d '\n'
            ;;
        "password")
            # Generate a strong password with special characters
            openssl rand -base64 32 2>/dev/null | tr -d '=+/' | cut -c1-25
            ;;
        *)
            echo "Unknown type: $type"
            return 1
            ;;
    esac
}

# Function to create Docker secrets
create_secrets() {
    echo -e "\n${YELLOW}🔧 Creating Docker secrets...${NC}"
    
    # Check if Docker is running and we're in a Docker Swarm
    if ! docker info | grep -q "Swarm: active"; then
        echo -e "${RED}❌ Docker Swarm is not active. Initialize with: docker swarm init${NC}"
        return 1
    fi
    
    # Define secrets with their generation methods
    declare -A secrets=(
        ["postgres_password"]="password:32"
        ["redis_password"]="password:32"
        ["qdrant_api_key"]="base64:32"
        ["together_api_key"]="base64:64"
        ["deepseek_api_key"]="base64:64"
        ["google_client_id"]="base64:64"
        ["google_client_secret"]="base64:64"
        ["encryption_key"]="hex:32"
        ["session_secret"]="base64:64"
        ["grafana_password"]="password:32"
    )
    
    local created=0
    local updated=0
    
    for secret_name in "${!secrets[@]}"; do
        local config="${secrets[$secret_name]}"
        local type="${config%%:*}"
        local length="${config##*:}"
        
        echo -n "Creating secret: $secret_name ... "
        
        # Check if secret already exists
        if docker secret ls | grep -q "$secret_name"; then
            echo -e "${YELLOW}EXISTS${NC}"
            read -p "  Update existing secret? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Remove existing secret
                docker secret rm "$secret_name" >/dev/null 2>&1 || true
                updated=$((updated + 1))
            else
                continue
            fi
        fi
        
        # Generate the secret value
        local secret_value
        secret_value=$(generate_secure_value "$type" "$length")
        
        if [[ -z "$secret_value" ]]; then
            echo -e "${RED}FAILED to generate value${NC}"
            continue
        fi
        
        # Create the secret
        if echo "$secret_value" | docker secret create "$secret_name" - >/dev/null 2>&1; then
            echo -e "${GREEN}CREATED${NC}"
            created=$((created + 1))
        else
            echo -e "${RED}FAILED${NC}"
        fi
    done
    
    echo -e "\n${GREEN}✅ Created $created new secrets, updated $updated existing secrets${NC}"
}

# Function to list existing secrets
list_secrets() {
    echo -e "\n${YELLOW}📋 Existing Docker secrets:${NC}"
    
    if ! docker info | grep -q "Swarm: active"; then
        echo -e "${RED}❌ Docker Swarm is not active${NC}"
        return 1
    fi
    
    docker secret ls --format "table {{.Name}}\t{{.Created}}\t{{.UpdatedAt}}"
}

# Function to remove secrets
remove_secrets() {
    echo -e "\n${YELLOW}🗑️  Removing Docker secrets...${NC}"
    
    if ! docker info | grep -q "Swarm: active"; then
        echo -e "${RED}❌ Docker Swarm is not active${NC}"
        return 1
    fi
    
    # List of ONYX secrets
    local onyx_secrets=(
        "postgres_password"
        "redis_password"
        "qdrant_api_key"
        "together_api_key"
        "deepseek_api_key"
        "google_client_id"
        "google_client_secret"
        "encryption_key"
        "session_secret"
        "grafana_password"
    )
    
    local removed=0
    
    for secret_name in "${onyx_secrets[@]}"; do
        if docker secret ls | grep -q "$secret_name"; then
            echo -n "Removing secret: $secret_name ... "
            if docker secret rm "$secret_name" >/dev/null 2>&1; then
                echo -e "${GREEN}REMOVED${NC}"
                removed=$((removed + 1))
            else
                echo -e "${RED}FAILED${NC}"
            fi
        fi
    done
    
    echo -e "\n${GREEN}✅ Removed $removed secrets${NC}"
}

# Function to generate .env file from secrets
generate_env_from_secrets() {
    echo -e "\n${YELLOW}📝 Generating .env file template from secrets...${NC}"
    
    local env_file=".env.from-secrets"
    
    cat > "$env_file" << 'EOF'
# =============================================================================
# ONYX Environment Variables (Generated from Docker Secrets)
# =============================================================================
# This file is generated from Docker secrets for development/testing
# For production, use docker-compose.secrets.yaml with actual Docker secrets
# =============================================================================

# Database Configuration
POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
DATABASE_URL=postgresql://manus:${POSTGRES_PASSWORD}@postgres:5432/manus

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD_FILE=/run/secrets/redis_password

# Qdrant Vector Database
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY_FILE=/run/secrets/qdrant_api_key

# LLM API Keys
TOGETHER_API_KEY_FILE=/run/secrets/together_api_key
DEEPSEEK_API_KEY_FILE=/run/secrets/deepseek_api_key

# Google OAuth2 Configuration
GOOGLE_CLIENT_ID_FILE=/run/secrets/google_client_id
GOOGLE_CLIENT_SECRET_FILE=/run/secrets/google_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/callback/google

# Encryption
ENCRYPTION_KEY_FILE=/run/secrets/encryption_key

# Session Management
SESSION_SECRET_FILE=/run/secrets/session_secret

# Monitoring
GRAFANA_PASSWORD_FILE=/run/secrets/grafana_password

# Non-sensitive configuration (can be set normally)
NODE_ENV=production
PYTHONPATH=/app
LOG_FORMAT=json
NEXT_PUBLIC_API_BASE="/"
NEXT_PUBLIC_SERVICE_NAME=suna-frontend
NEXT_PUBLIC_ENABLE_REMOTE_LOGGING="true"
LITELLM_URL=http://litellm-proxy:4000
SSL_CERT_PATH=./nginx/ssl/cert.pem
SSL_KEY_PATH=./nginx/ssl/key.pem
EOF

    echo -e "${GREEN}✅ Generated environment file: $env_file${NC}"
    echo -e "${YELLOW}⚠️  This file uses Docker secrets file paths, not actual values${NC}"
}

# Function to show deployment instructions
show_deployment_instructions() {
    echo -e "\n${YELLOW}🚀 Production Deployment Instructions${NC}"
    echo "======================================"
    echo
    echo "1. Initialize Docker Swarm (if not already done):"
    echo "   docker swarm init"
    echo
    echo "2. Create Docker secrets:"
    echo "   $0 create-secrets"
    echo
    echo "3. Deploy with secrets:"
    echo "   docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml up -d"
    echo
    echo "4. Verify deployment:"
    echo "   docker compose ps"
    echo "   docker compose logs"
    echo
    echo "5. Clean up secrets when needed:"
    echo "   $0 remove-secrets"
    echo
    echo "📚 For more information, see:"
    echo "   - Docker Secrets documentation: https://docs.docker.com/engine/swarm/secrets/"
    echo "   - Docker Compose with secrets: https://docs.docker.com/compose/use-secrets/"
}

# Main function
main() {
    case "${1:-help}" in
        "create-secrets")
            create_secrets
            ;;
        "list")
            list_secrets
            ;;
        "remove-secrets")
            remove_secrets
            ;;
        "generate-env")
            generate_env_from_secrets
            ;;
        "deploy")
            show_deployment_instructions
            ;;
        "help"|*)
            echo "Usage: $0 {create-secrets|list|remove-secrets|generate-env|deploy|help}"
            echo
            echo "Commands:"
            echo "  create-secrets  Create all required Docker secrets"
            echo "  list           List existing Docker secrets"
            echo "  remove-secrets Remove all ONYX Docker secrets"
            echo "  generate-env   Generate .env file template from secrets"
            echo "  deploy         Show deployment instructions"
            echo "  help           Show this help message"
            ;;
    esac
}

# Run main function
main "$@"