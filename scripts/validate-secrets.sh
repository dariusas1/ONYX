#!/bin/bash

# =============================================================================
# ONYX Secrets Validation Script
# =============================================================================
# This script checks for potential secrets in git history and current files
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 ONYX Secrets Validation${NC}"
echo "=================================="

# Function to check for secrets in git history
check_git_history() {
    echo -e "\n${YELLOW}📚 Checking git history for secrets...${NC}"
    
    # Patterns that might indicate secrets
    PATTERNS=(
        "password"
        "secret"
        "api_key"
        "apikey"
        "api-key"
        "token"
        "private_key"
        "privatekey"
        "auth"
        "credential"
        "client_secret"
        "client-secret"
    )
    
    FOUND_SECRETS=false
    
    for pattern in "${PATTERNS[@]}"; do
        echo -n "Checking pattern '$pattern'... "
        if git log -S "$pattern" --oneline --all 2>/dev/null | grep -q .; then
            echo -e "${RED}FOUND${NC}"
            echo -e "${RED}⚠️  Potential secrets found with pattern: $pattern${NC}"
            git log -S "$pattern" --oneline --all 2>/dev/null | head -5
            FOUND_SECRETS=true
        else
            echo -e "${GREEN}CLEAR${NC}"
        fi
    done
    
    if [ "$FOUND_SECRETS" = false ]; then
        echo -e "${GREEN}✅ No obvious secrets found in git history${NC}"
    fi
}

# Function to check current files for secrets
check_current_files() {
    echo -e "\n${YELLOW}📁 Checking current files for secrets...${NC}"
    
    # Files to check (excluding .env files which should contain secrets)
    FILES_TO_CHECK=(
        "docker-compose.yaml"
        "docker-compose.yml"
        "nginx/nginx.conf"
        "scripts/*"
        "*.md"
        "*.yaml"
        "*.yml"
        "*.json"
    )
    
    FOUND_SECRETS=false
    
    for file_pattern in "${FILES_TO_CHECK[@]}"; do
        if ls $file_pattern 1> /dev/null 2>&1; then
            for file in $file_pattern; do
                if [ -f "$file" ]; then
                    echo -n "Checking $file... "
                    
                    # Check for common secret patterns
                    if grep -i -E "(password|secret|key|token|auth).*=.*[^a-z]{8,}" "$file" >/dev/null 2>&1; then
                        echo -e "${RED}POTENTIAL SECRETS${NC}"
                        echo -e "${RED}⚠️  Check $file for hardcoded secrets${NC}"
                        grep -n -i -E "(password|secret|key|token|auth).*=.*[^a-z]{8,}" "$file" | head -3
                        FOUND_SECRETS=true
                    else
                        echo -e "${GREEN}CLEAR${NC}"
                    fi
                fi
            done
        fi
    done
    
    if [ "$FOUND_SECRETS" = false ]; then
        echo -e "${GREEN}✅ No hardcoded secrets found in current files${NC}"
    fi
}

# Function to check .env files are properly ignored
check_env_files_ignored() {
    echo -e "\n${YELLOW}🚫 Checking .env files are properly ignored...${NC}"
    
    if [ -f ".gitignore" ]; then
        ENV_PATTERNS=(".env" ".env.*" "*.env")
        
        for pattern in "${ENV_PATTERNS[@]}"; do
            if grep -q "^$pattern$" .gitignore; then
                echo -e "✅ Pattern '$pattern' found in .gitignore"
            else
                echo -e "${YELLOW}⚠️  Pattern '$pattern' not found in .gitignore${NC}"
            fi
        done
    else
        echo -e "${RED}❌ .gitignore file not found${NC}"
    fi
}

# Function to check Docker images for secrets
check_docker_images() {
    echo -e "\n${YELLOW}🐳 Checking Docker images for secrets...${NC}"
    
    # Get list of services from docker-compose
    if command -v docker-compose >/dev/null 2>&1; then
        SERVICES=$(docker-compose config --services 2>/dev/null || echo "")
        
        if [ -n "$SERVICES" ]; then
            for service in $SERVICES; do
                echo -n "Checking image for service '$service'... "
                
                # Get the image name
                IMAGE=$(docker-compose config 2>/dev/null | grep -A 10 "$service:" | grep "image:" | cut -d: -f2- | xargs)
                
                if [ -n "$IMAGE" ] && docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$IMAGE"; then
                    # Check image history for potential secrets
                    if docker history "$IMAGE" --format "{{.CreatedBy}}" 2>/dev/null | grep -i -E "(password|secret|key|token)" >/dev/null 2>&1; then
                        echo -e "${YELLOW}REVIEW NEEDED${NC}"
                        echo -e "${YELLOW}⚠️  Review image $IMAGE for potential secrets${NC}"
                    else
                        echo -e "${GREEN}CLEAR${NC}"
                    fi
                else
                    echo -e "${YELLOW}IMAGE NOT FOUND${NC}"
                fi
            done
        else
            echo -e "${YELLOW}⚠️  Could not get services from docker-compose${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  docker-compose not available${NC}"
    fi
}

# Function to validate environment variable masking
check_env_masking() {
    echo -e "\n${YELLOW}🎭 Checking environment variable masking...${NC}"
    
    if [ -f ".env.local" ]; then
        echo -n "Testing docker compose config masking... "
        
        # Check if docker compose config shows actual values or variables
        if docker compose config 2>/dev/null | grep -E "(POSTGRES_PASSWORD|TOGETHER_API_KEY|GRAFANA_PASSWORD)" | grep -v "^\$" >/dev/null 2>&1; then
            echo -e "${YELLOW}VALUES VISIBLE${NC}"
            echo -e "${YELLOW}⚠️  Environment variables are visible in docker compose config${NC}"
            echo -e "${YELLOW}💡 This is normal for development. Consider using Docker secrets in production.${NC}"
        else
            echo -e "${GREEN}MASKED${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  .env.local not found${NC}"
    fi
}

# Main execution
main() {
    echo "Starting secrets validation..."
    
    check_git_history
    check_current_files
    check_env_files_ignored
    check_docker_images
    check_env_masking
    
    echo -e "\n${GREEN}🎉 Secrets validation complete!${NC}"
    echo -e "\n${YELLOW}💡 Recommendations:${NC}"
    echo "1. Use environment-specific .env files (.env.development, .env.staging, .env.production)"
    echo "2. Never commit actual values to version control"
    echo "3. Use Docker secrets for production deployments"
    echo "4. Rotate secrets regularly"
    echo "5. Use strong, unique passwords for each environment"
}

# Run main function
main "$@"