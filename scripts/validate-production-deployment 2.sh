#!/bin/bash

# =============================================================================
# ONYX Production Deployment Validation Script
# =============================================================================
# This script validates that production deployment is secure and ready
# It prevents deployment if secrets are exposed or configuration is unsafe
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️ ONYX Production Deployment Validation${NC}"
echo "============================================"

# Track validation failures
validation_failure=false

# Function to fail validation
fail_validation() {
    echo -e "${RED}❌ VALIDATION FAILED: $1${NC}"
    validation_failure=true
}

# Function to pass validation
pass_validation() {
    echo -e "${GREEN}✅ VALIDATION PASSED: $1${NC}"
}

# Function to check for dangerous patterns in configuration
check_dangerous_patterns() {
    echo -e "\n${YELLOW}🔍 Checking for dangerous configuration patterns...${NC}"

    # Check if .env.local is being used (contains dev secrets)
    if grep -q "dev-" .env.local 2>/dev/null; then
        fail_validation ".env.local contains development secrets - should not be used in production"
    fi

    # Check if docker-compose.yaml has env_file pointing to .env.local
    if grep -q "env_file.*\.env\.local" docker-compose.yaml 2>/dev/null; then
        fail_validation "docker-compose.yaml references .env.local - not safe for production"
    fi

    # Check if production env file contains ${VAR} substitution for secrets
    if [ -f ".env.production" ]; then
        if grep -E '\$\{.*PASSWORD.*\}|\$\{.*SECRET.*\}|\$\{.*KEY.*\}' .env.production 2>/dev/null; then
            fail_validation ".env.production contains dangerous \${VAR} substitution for secrets"
        fi
    fi
}

# Function to validate Docker secrets configuration
validate_docker_secrets() {
    echo -e "\n${YELLOW}🔐 Validating Docker secrets configuration...${NC}"

    if [ ! -f "docker-compose.secrets.yaml" ]; then
        fail_validation "docker-compose.secrets.yaml not found - required for production"
        return
    fi

    # Check if secrets file properly defines external secrets
    if ! grep -q "external: true" docker-compose.secrets.yaml 2>/dev/null; then
        fail_validation "docker-compose.secrets.yaml missing 'external: true' for secrets"
    fi

    # Test production configuration exposure
    echo -e "\n${YELLOW}🧪 Testing production configuration for secret exposure...${NC}"

    # Try to generate production config and check for exposure
    if docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml config --no-path-resolution 2>/dev/null | grep -E "(password|secret|key)" | grep -v "FILE:" | grep -v "_FILE:" > /tmp/production_config_check.txt; then
        if [ -s /tmp/production_config_check.txt ]; then
            echo -e "${RED}❌ PRODUCTION CONFIG EXPOSES SECRETS:${NC}"
            cat /tmp/production_config_check.txt
            fail_validation "Production configuration exposes secrets in docker compose config"
        else
            pass_validation "Production configuration does not expose secrets"
        fi
    else
        pass_validation "Production configuration validation passed"
    fi
}

# Function to check environment isolation
check_environment_isolation() {
    echo -e "\n${YELLOW}🌍 Checking environment isolation...${NC}"

    # Check current environment
    current_env="${NODE_ENV:-development}"
    if [ "$current_env" != "production" ]; then
        fail_validation "NODE_ENV is not set to 'production' (current: $current_env)"
    fi
}

# Function to validate deployment prerequisites
validate_prerequisites() {
    echo -e "\n${YELLOW}📋 Checking deployment prerequisites...${NC}"

    # Check required files
    required_files=("docker-compose.yaml" "docker-compose.secrets.yaml")

    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            pass_validation "Required file exists: $file"
        else
            fail_validation "Required file missing: $file"
        fi
    done

    # Check Docker availability
    if command -v docker >/dev/null 2>&1; then
        pass_validation "Docker is available"
    else
        fail_validation "Docker is not available"
    fi

    # Check Docker Compose availability
    if command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1; then
        pass_validation "Docker Compose is available"
    else
        fail_validation "Docker Compose is not available"
    fi
}

# Main validation function
main() {
    echo "Starting production deployment validation..."

    # Run all validation checks
    validate_prerequisites
    check_dangerous_patterns
    validate_docker_secrets
    check_environment_isolation

    # Final validation result
    echo -e "\n${BLUE}📊 VALIDATION SUMMARY${NC}"
    echo "======================="

    if [ "$validation_failure" = true ]; then
        echo -e "\n${RED}🚨 PRODUCTION DEPLOYMENT BLOCKED${NC}"
        echo -e "${RED}❌ CRITICAL ISSUES FOUND - Deployment not safe${NC}"
        echo ""
        echo -e "${RED}🛡️  FIX ALL VALIDATION FAILURES BEFORE DEPLOYING${NC}"
        echo -e "${RED}❌ DO NOT DEPLOY TO PRODUCTION${NC}"
        exit 1
    else
        echo -e "\n${GREEN}✅ PRODUCTION DEPLOYMENT VALIDATED${NC}"
        echo -e "${GREEN}🛡️  Configuration is secure and ready for deployment${NC}"
        echo ""
        echo -e "${GREEN}🚀 Ready to deploy with:${NC}"
        echo -e "${GREEN}docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml up -d${NC}"
        exit 0
    fi
}

# Run main function
main "$@"