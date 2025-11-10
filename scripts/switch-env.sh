#!/bin/bash

# =============================================================================
# ONYX Environment Switching Script
# =============================================================================
# This script helps switch between different environment configurations
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
    echo -e "${BLUE}ONYX Environment Switcher${NC}"
    echo "=========================="
    echo ""
    echo "Usage: $0 [environment]"
    echo ""
    echo "Available environments:"
    echo "  development  - Local development environment"
    echo "  staging      - Staging environment for testing"
    echo "  production   - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 development   # Switch to development"
    echo "  $0 staging       # Switch to staging"
    echo "  $0 production    # Switch to production"
    echo ""
    echo "Current environment files:"
    for env_file in .env.*; do
        if [ -f "$env_file" ] && [ "$env_file" != ".env.example" ]; then
            echo "  - $env_file"
        fi
    done
}

# Function to validate environment
validate_environment() {
    local env=$1
    local env_file=".env.$env"
    
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ Environment file '$env_file' not found${NC}"
        echo -e "${YELLOW}💡 Available environments:${NC}"
        for file in .env.*; do
            if [ -f "$file" ] && [ "$file" != ".env.example" ]; then
                basename "$file" .env
            fi
        done
        exit 1
    fi
}

# Function to switch environment
switch_environment() {
    local env=$1
    local env_file=".env.$env"
    local target_file=".env.local"
    
    echo -e "${YELLOW}🔄 Switching to '$env' environment...${NC}"
    
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
    echo "  NODE_ENV: $(grep NODE_ENV "$target_file" | cut -d= -f2)"
    echo "  LOG_LEVEL: $(grep LOG_LEVEL "$target_file" | cut -d= -f2)"
    
    # Show warnings for production
    if [ "$env" = "production" ]; then
        echo -e "\n${RED}⚠️  PRODUCTION WARNINGS:${NC}"
        echo "  - Ensure all placeholder values are replaced with actual secure values"
        echo "  - Verify all passwords are strong and unique"
        echo "  - Check that SSL certificates are properly configured"
        echo "  - Ensure monitoring and logging are properly set up"
        echo "  - Test all services before going live"
    fi
}

# Function to show current environment
show_current() {
    if [ -f ".env.local" ]; then
        echo -e "${BLUE}📋 Current Environment:${NC}"
        echo "  NODE_ENV: $(grep NODE_ENV .env.local 2>/dev/null | cut -d= -f2 || echo 'not set')"
        echo "  LOG_LEVEL: $(grep LOG_LEVEL .env.local 2>/dev/null | cut -d= -f2 || echo 'not set')"
        echo "  COMPOSE_PROJECT_NAME: $(grep COMPOSE_PROJECT_NAME .env.local 2>/dev/null | cut -d= -f2 || echo 'not set')"
    else
        echo -e "${YELLOW}⚠️  No .env.local file found${NC}"
        echo -e "${YELLOW}💡 Run '$0 development' to set up initial environment${NC}"
    fi
}

# Function to validate environment configuration
validate_config() {
    local env=$1
    local env_file=".env.$env"
    
    echo -e "\n${YELLOW}🔍 Validating environment configuration...${NC}"
    
    # Check for required variables
    local required_vars=(
        "NODE_ENV"
        "POSTGRES_PASSWORD"
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
        "GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
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
            "GENERATE_"
            "change-me"
            "CHANGE_ME"
        )
        
        local found_placeholders=()
        
        for pattern in "${placeholder_patterns[@]}"; do
            if grep -i "$pattern" "$env_file" >/dev/null 2>&1; then
                found_placeholders+=("$pattern")
            fi
        done
        
        if [ ${#found_placeholders[@]} -gt 0 ]; then
            echo -e "${RED}❌ Production environment contains placeholder values:${NC}"
            for pattern in "${found_placeholders[@]}"; do
                echo -e "  ${RED}- $pattern${NC}"
            done
            echo -e "${RED}⚠️  Replace all placeholders with actual secure values before production deployment${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}✅ Environment configuration is valid${NC}"
    return 0
}

# Function to test environment
test_environment() {
    local env=$1
    
    echo -e "\n${YELLOW}🧪 Testing environment configuration...${NC}"
    
    # Test docker compose config
    echo -n "Testing docker compose config... "
    if docker compose config --no-path-resolution >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo -e "${RED}⚠️  Docker compose configuration has errors${NC}"
        return 1
    fi
    
    # Test environment variable loading
    echo -n "Testing environment variable loading... "
    if docker compose config --no-path-resolution | grep -q "NODE_ENV.*$env"; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING${NC}"
        echo -e "${YELLOW}💡 Environment variables may not be loading correctly${NC}"
    fi
    
    echo -e "${GREEN}✅ Environment test completed${NC}"
}

# Main execution
main() {
    case "$1" in
        -h|--help|help)
            show_usage
            exit 0
            ;;
        --current|current)
            show_current
            exit 0
            ;;
        --validate|validate)
            if [ -z "$2" ]; then
                echo -e "${RED}❌ Please specify an environment to validate${NC}"
                exit 1
            fi
            validate_environment "$2"
            validate_config "$2"
            exit 0
            ;;
        --test|test)
            if [ -z "$2" ]; then
                echo -e "${RED}❌ Please specify an environment to test${NC}"
                exit 1
            fi
            validate_environment "$2"
            test_environment "$2"
            exit 0
            ;;
        "")
            show_usage
            exit 1
            ;;
        *)
            validate_environment "$ENVIRONMENT"
            validate_config "$ENVIRONMENT"
            switch_environment "$ENVIRONMENT"
            test_environment "$ENVIRONMENT"
            
            echo -e "\n${GREEN}🎉 Environment switch complete!${NC}"
            echo -e "\n${BLUE}Next steps:${NC}"
            echo "1. Review the configuration in .env.local"
            echo "2. Update any placeholder values with actual values"
            echo "3. Run 'docker compose up' to start services"
            echo "4. Run './scripts/validate-secrets.sh' to check for security issues"
            ;;
    esac
}

# Run main function
main "$@"