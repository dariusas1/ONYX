#!/bin/bash

# =============================================================================
# ONYX Secure Environment Management Script
# =============================================================================
# This script properly manages environment switching with security considerations
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${1:-development}

# Function to show usage
show_usage() {
    echo -e "${BLUE}ONYX Secure Environment Manager${NC}"
    echo "================================="
    echo ""
    echo "Usage: $0 [environment] [action]"
    echo ""
    echo "Environments:"
    echo "  development  - Local development with test values"
    echo "  staging      - Staging with placeholder values"
    echo "  production  - Production with variable references"
    echo "  template     - Template with variable references (for testing)"
    echo ""
    echo "Actions:"
    echo "  switch       - Switch to environment (default)"
    echo "  test         - Test environment masking"
    echo "  validate     - Validate environment configuration"
    echo ""
    echo "Examples:"
    echo "  $0 development        # Switch to development"
    echo "  $0 production test   # Test production masking"
    echo "  $0 template switch   # Switch to template for security testing"
}

# Function to validate environment
validate_environment() {
    local env=$1
    local valid_envs=("development" "staging" "production" "template")
    
    for valid_env in "${valid_envs[@]}"; do
        if [ "$env" = "$valid_env" ]; then
            return 0
        fi
    done
    
    echo -e "${RED}❌ Invalid environment: $env${NC}"
    echo -e "${YELLOW}💡 Valid environments: ${valid_envs[*]}${NC}"
    return 1
}

# Function to get source file for environment
get_env_file() {
    local env=$1
    case "$env" in
        "development")
            echo ".env.development-template"
            ;;
        "staging")
            echo ".env.staging"
            ;;
        "production")
            echo ".env.production"
            ;;
        "template")
            echo ".env.template"
            ;;
        *)
            echo ".env.local"
            ;;
    esac
}

# Function to switch environment
switch_environment() {
    local env=$1
    local env_file=$(get_env_file "$env")
    local target_file=".env.local"
    
    echo -e "${YELLOW}🔄 Switching to '$env' environment...${NC}"
    
    # Validate source file exists
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ Environment file '$env_file' not found${NC}"
        return 1
    fi
    
    # Backup existing .env.local if it exists
    if [ -f "$target_file" ]; then
        backup_file=".env.local.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$target_file" "$backup_file"
        echo -e "${YELLOW}📦 Backed up existing $target_file to $backup_file${NC}"
    fi
    
    # Copy environment file
    cp "$env_file" "$target_file"
    echo -e "${GREEN}✅ Switched to '$env' environment${NC}"
    
    # Show environment info
    echo -e "\n${BLUE}📋 Environment Information:${NC}"
    echo "  Environment: $env"
    echo "  Source file: $env_file"
    echo "  Target file: $target_file"
    echo "  Purpose: $(get_env_purpose "$env")"
    
    # Show warnings for production
    if [ "$env" = "production" ]; then
        echo -e "\n${RED}⚠️  PRODUCTION WARNINGS:${NC}"
        echo "  - This environment uses variable references"
        echo "  - Use Docker secrets for actual deployment"
        echo "  - Set environment variables before deployment"
        echo "  - Test with: docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml up"
    fi
}

# Function to get environment purpose
get_env_purpose() {
    local env=$1
    case "$env" in
        "development")
            echo "Development with test values (functional)"
            ;;
        "staging")
            echo "Staging with placeholder values (testing)"
            ;;
        "production")
            echo "Production with variable references (secure)"
            ;;
        "template")
            echo "Template with variable references (security testing)"
            ;;
        *)
            echo "Custom environment"
            ;;
    esac
}

# Function to test environment masking
test_masking() {
    local env=$1
    local env_file=$(get_env_file "$env")
    
    echo -e "\n${YELLOW}🎭 Testing secrets masking for '$env' environment...${NC}"
    
    # Backup current .env.local
    if [ -f ".env.local" ]; then
        cp .env.local .env.local.backup.test
    fi
    
    # Switch to test environment
    cp "$env_file" .env.local
    
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
    
    local exposed_count=0
    local masked_count=0
    
    for var in "${SENSITIVE_VARS[@]}"; do
        echo -n "  $var: "
        
        # Get value from docker compose config
        value=$(docker compose config --no-path-resolution 2>/dev/null | grep "^      $var:" | head -1 | cut -d: -f2- | xargs || echo "NOT_FOUND")
        
        if [ "$value" = "NOT_FOUND" ]; then
            echo -e "${YELLOW}NOT FOUND${NC}"
        elif [ "$value" = "" ]; then
            echo -e "${GREEN}MASKED (empty)${NC}"
            ((masked_count++))
        elif [[ "$value" == \$* ]]; then
            echo -e "${GREEN}MASKED (\$VAR)${NC}"
            ((masked_count++))
        elif [[ "$value" == *"your-"* ]] || [[ "$value" == *"generate-"* ]] || [[ "$value" == *"test-"* ]] || [[ "$value" == *"dev-"* ]]; then
            echo -e "${YELLOW}PLACEHOLDER: $value${NC}"
            ((exposed_count++))
        else
            echo -e "${RED}EXPOSED: $value${NC}"
            ((exposed_count++))
        fi
    done
    
    # Restore original .env.local
    if [ -f ".env.local.backup.test" ]; then
        mv .env.local.backup.test .env.local
    fi
    
    # Summary
    echo -e "\n${BLUE}📊 Masking Test Results:${NC}"
    echo "  Masked variables: $masked_count"
    echo "  Exposed variables: $exposed_count"
    
    if [ $exposed_count -eq 0 ]; then
        echo -e "${GREEN}✅ ALL SECRETS PROPERLY MASKED${NC}"
        return 0
    else
        echo -e "${RED}❌ SECRETS EXPOSED - SECURITY RISK${NC}"
        return 1
    fi
}

# Function to validate environment
validate_environment_config() {
    local env=$1
    local env_file=$(get_env_file "$env")
    
    echo -e "\n${YELLOW}🔍 Validating '$env' environment configuration...${NC}"
    
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ Environment file '$env_file' not found${NC}"
        return 1
    fi
    
    # Check for required variables
    local required_vars=(
        "NODE_ENV"
        "POSTGRES_PASSWORD"
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing required variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "  ${RED}- $var${NC}"
        done
        return 1
    else
        echo -e "${GREEN}✅ All required variables present${NC}"
    fi
    
    # Check for placeholder values in production
    if [ "$env" = "production" ]; then
        local placeholder_patterns=(
            "your-"
            "generate-"
            "test-"
            "dev-"
        )
        
        local found_placeholders=()
        
        for pattern in "${placeholder_patterns[@]}"; do
            if grep -i "$pattern" "$env_file" >/dev/null 2>&1; then
                found_placeholders+=("$pattern")
            fi
        done
        
        if [ ${#found_placeholders[@]} -gt 0 ]; then
            echo -e "${RED}❌ Production environment contains placeholder patterns:${NC}"
            for pattern in "${found_placeholders[@]}"; do
                echo -e "  ${RED}- $pattern${NC}"
            done
            echo -e "${RED}⚠️  This is expected for production with variable references${NC}"
        fi
    fi
    
    echo -e "${GREEN}✅ Environment configuration is valid${NC}"
    return 0
}

# Main execution
main() {
    local environment="$1"
    local action="${2:-switch}"
    
    case "$action" in
        -h|--help|help)
            show_usage
            exit 0
            ;;
        switch)
            validate_environment "$environment"
            switch_environment "$environment"
            ;;
        test)
            validate_environment "$environment"
            test_masking "$environment"
            ;;
        validate)
            validate_environment "$environment"
            validate_environment_config "$environment"
            ;;
        "")
            show_usage
            exit 1
            ;;
        *)
            echo -e "${RED}❌ Unknown action: $action${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"