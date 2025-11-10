#!/bin/bash

# =============================================================================
# ONYX Secrets Masking Test Script
# =============================================================================
# This script tests that secrets are properly masked in docker compose config
# Updated to support Docker secrets and improved masking validation
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎭 ONYX Secrets Masking Test${NC}"
echo "==============================="

# Function to test current masking
test_current_masking() {
    echo -e "\n${YELLOW}🔍 Testing current secrets masking...${NC}"
    
    # List of sensitive variables to check
    SENSITIVE_VARS=(
        "POSTGRES_PASSWORD"
        "TOGETHER_API_KEY"
        "DEEPSEEK_API_KEY"
        "GOOGLE_CLIENT_SECRET"
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
        "GRAFANA_PASSWORD"
        "REDIS_PASSWORD"
        "QDRANT_API_KEY"
    )
    
    echo -e "${BLUE}Checking docker compose config output:${NC}"
    
    for var in "${SENSITIVE_VARS[@]}"; do
        echo -n "  $var: "
        
        # Get the value from docker compose config
        value=$(docker compose config --no-path-resolution 2>/dev/null | grep "^      $var:" | head -1 | cut -d: -f2- | xargs || echo "NOT_FOUND")
        
        if [ "$value" = "NOT_FOUND" ]; then
            echo -e "${YELLOW}NOT FOUND${NC}"
        elif [ "$value" = "" ]; then
            echo -e "${GREEN}MASKED (empty)${NC}"
        elif [[ "$value" == \$* ]]; then
            echo -e "${GREEN}MASKED (\$VAR)${NC}"
        elif [[ "$value" == *"your-"* ]] || [[ "$value" == *"generate-"* ]] || [[ "$value" == *"placeholder"* ]]; then
            echo -e "${YELLOW}PLACEHOLDER${NC}"
        else
            echo -e "${RED}EXPOSED: $value${NC}"
        fi
    done
}

# Function to test with production environment
test_production_masking() {
    echo -e "\n${YELLOW}🏭 Testing production environment masking...${NC}"
    
    if [ ! -f ".env.production" ]; then
        echo -e "${RED}❌ .env.production not found${NC}"
        return 1
    fi
    
    # Backup current .env.local
    if [ -f ".env.local" ]; then
        cp .env.local .env.local.backup.test
    fi
    
    # Switch to production environment temporarily
    cp .env.production .env.local
    
    echo -e "${BLUE}Testing with production environment:${NC}"
    
    # List of sensitive variables to check
    SENSITIVE_VARS=(
        "POSTGRES_PASSWORD"
        "TOGETHER_API_KEY"
        "DEEPSEEK_API_KEY"
        "GOOGLE_CLIENT_SECRET"
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
        "GRAFANA_PASSWORD"
    )
    
    for var in "${SENSITIVE_VARS[@]}"; do
        echo -n "  $var: "
        
        # Get the value from docker compose config
        value=$(docker compose config --no-path-resolution 2>/dev/null | grep "^      $var:" | head -1 | cut -d: -f2- | xargs || echo "NOT_FOUND")
        
        if [ "$value" = "NOT_FOUND" ]; then
            echo -e "${YELLOW}NOT FOUND${NC}"
        elif [ "$value" = "" ]; then
            echo -e "${GREEN}MASKED (empty)${NC}"
        elif [[ "$value" == \$* ]]; then
            echo -e "${GREEN}MASKED (\$VAR)${NC}"
        elif [[ "$value" == *"GENERATE"* ]] || [[ "$value" == *"generate-"* ]]; then
            echo -e "${RED}PLACEHOLDER: $value${NC}"
        else
            echo -e "${RED}EXPOSED: $value${NC}"
        fi
    done
    
    # Restore original .env.local
    if [ -f ".env.local.backup.test" ]; then
        mv .env.local.backup.test .env.local
    fi
}

# Function to test container environment
test_container_environment() {
    echo -e "\n${YELLOW}🐳 Testing container environment isolation...${NC}"
    
    # Get list of services
    services=$(docker compose config --services 2>/dev/null || echo "")
    
    if [ -z "$services" ]; then
        echo -e "${YELLOW}⚠️  Could not get services list${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Checking if containers would have access to sensitive variables:${NC}"
    
    for service in $services; do
        echo -n "  $service: "
        
        # Check if service has env_file directive
        if docker compose config 2>/dev/null | grep -A 20 "^  $service:" | grep -q "env_file:"; then
            echo -e "${GREEN}✅ Has env_file${NC}"
        else
            echo -e "${YELLOW}⚠️  No env_file${NC}"
        fi
    done
}

# Function to suggest improvements
suggest_improvements() {
    echo -e "\n${BLUE}💡 Suggestions for better secrets management:${NC}"
    echo ""
    echo "1. Use Docker secrets for production:"
    echo "   docker compose --file docker-compose.yaml --file docker-compose.prod.yaml up"
    echo ""
    echo "2. Consider using a secrets management system:"
    echo "   - HashiCorp Vault"
    echo "   - AWS Secrets Manager"
    echo "   - Azure Key Vault"
    echo ""
    echo "3. Use environment-specific compose files:"
    echo "   docker-compose.staging.yaml"
    echo "   docker-compose.production.yaml"
    echo ""
    echo "4. Implement runtime secret injection:"
    echo "   - Kubernetes secrets"
    echo "   - Docker swarm secrets"
    echo "   - External secret providers"
}

# Function to create production compose file
create_production_compose() {
    echo -e "\n${YELLOW}📝 Creating production compose file with secrets...${NC}"
    
    if [ -f "docker-compose.production.yaml" ]; then
        echo -e "${YELLOW}⚠️  docker-compose.production.yaml already exists${NC}"
        return 0
    fi
    
    cat > docker-compose.production.yaml << 'EOF'
# =============================================================================
# ONYX Production Docker Compose Override
# =============================================================================
# This file extends docker-compose.yaml for production deployment
# Use Docker secrets for sensitive data in production
# =============================================================================

services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

  redis:
    secrets:
      - redis_password
    command: redis-server --appendonly yes --requirepass-file /run/secrets/redis_password

  grafana:
    secrets:
      - grafana_password
    environment:
      GF_SECURITY_ADMIN_PASSWORD_FILE: /run/secrets/grafana_password

  onyx-core:
    secrets:
      - encryption_key
      - session_secret
      - google_client_id
      - google_client_secret
    environment:
      ENCRYPTION_KEY_FILE: /run/secrets/encryption_key
      SESSION_SECRET_FILE: /run/secrets/session_secret
      GOOGLE_CLIENT_ID_FILE: /run/secrets/google_client_id
      GOOGLE_CLIENT_SECRET_FILE: /run/secrets/google_client_secret

  litellm-proxy:
    secrets:
      - together_api_key
      - deepseek_api_key
    environment:
      TOGETHER_API_KEY_FILE: /run/secrets/together_api_key
      DEEPSEEK_API_KEY_FILE: /run/secrets/deepseek_api_key

secrets:
  postgres_password:
    external: true
  redis_password:
    external: true
  grafana_password:
    external: true
  encryption_key:
    external: true
  session_secret:
    external: true
  google_client_id:
    external: true
  google_client_secret:
    external: true
  together_api_key:
    external: true
  deepseek_api_key:
    external: true
EOF

    echo -e "${GREEN}✅ Created docker-compose.production.yaml${NC}"
    echo -e "${YELLOW}💡 Use with: docker compose -f docker-compose.yaml -f docker-compose.production.yaml up${NC}"
}

# Main execution
main() {
    echo "Starting secrets masking tests..."
    
    test_current_masking
    test_production_masking
    test_container_environment
    suggest_improvements
    
    read -p $'\nCreate production compose file with Docker secrets? (y/N): ' -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_production_compose
    fi
    
    echo -e "\n${GREEN}🎉 Secrets masking test complete!${NC}"
}

# Run main function
main "$@"