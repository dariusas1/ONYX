#!/bin/bash

# =============================================================================
# ONYX Runtime Secret Validation Script
# =============================================================================
# This script validates that no placeholder values are present before deployment
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 ONYX Runtime Secret Validation${NC}"
echo "=================================="

# Exit code
EXIT_CODE=0

# Function to check if a value is a placeholder
is_placeholder() {
    local value="$1"
    local var_name="$2"
    
    # Check for common placeholder patterns (exclude test values)
    if [[ "$value" == *"your-"* ]] || \
       [[ "$value" == *"generate-"* ]] || \
       [[ "$value" == *"GENERATE"* ]] || \
       [[ "$value" == *"placeholder"* ]] || \
       [[ "$value" == *"example"* ]] || \
       [[ "$value" == *"change-me"* ]] || \
       [[ "$value" == *"xxx"* ]] || \
       [[ "$value" == *"dev-"*"-placeholder" ]]; then
        return 0  # Is placeholder
    fi
    
    # Check for empty values that shouldn't be empty
    if [[ -z "$value" ]] && ( [[ "$var_name" == *"_KEY"* ]] || [[ "$var_name" == *"_SECRET"* ]] || [[ "$var_name" == *"_PASSWORD"* ]] ); then
        return 0  # Is placeholder (empty sensitive value)
    fi
    
    return 1  # Not placeholder
}

# Function to validate environment file
validate_env_file() {
    local env_file="$1"
    local file_type="$2"
    
    echo -e "\n${YELLOW}📋 Validating $file_type environment file: $env_file${NC}"
    
    if [[ ! -f "$env_file" ]]; then
        echo -e "${RED}❌ Environment file not found: $env_file${NC}"
        return 1
    fi
    
    # List of critical variables that must not be placeholders
    local critical_vars=(
        "GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
        "TOGETHER_API_KEY"
        "DEEPSEEK_API_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "QDRANT_API_KEY"
        "ENCRYPTION_KEY"
        "SESSION_SECRET"
        "GRAFANA_PASSWORD"
    )
    
    local placeholders_found=0
    
    for var in "${critical_vars[@]}"; do
        # Get value from environment file
        local value=$(grep "^$var=" "$env_file" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")
        
        if is_placeholder "$value" "$var"; then
            echo -e "${RED}  ❌ $var: PLACEHOLDER DETECTED${NC}"
            echo -e "     Value: $value"
            placeholders_found=$((placeholders_found + 1))
        elif [[ -z "$value" ]]; then
            echo -e "${YELLOW}  ⚠️  $var: EMPTY${NC}"
        else
            echo -e "${GREEN}  ✅ $var: VALID${NC}"
        fi
    done
    
    if [[ $placeholders_found -gt 0 ]]; then
        echo -e "${RED}  ❌ Found $placeholders_found placeholder(s) in $env_file${NC}"
        EXIT_CODE=1
    else
        echo -e "${GREEN}  ✅ No placeholders found in $env_file${NC}"
    fi
}

# Function to validate docker compose config
validate_docker_compose() {
    echo -e "\n${YELLOW}🐳 Validating Docker Compose configuration...${NC}"
    
    # Determine which environment file to use
    local env_file_to_check="${ENV_FILE:-.env.local}"
    
    # Check if environment file exists
    if [[ ! -f "$env_file_to_check" ]]; then
        echo -e "${RED}❌ Environment file not found: $env_file_to_check. Cannot validate Docker Compose config.${NC}"
        EXIT_CODE=1
        return 1
    fi
    
    # Get docker compose config and check for exposed secrets (respect ENV_FILE)
    local config_output
    if [[ -n "$ENV_FILE" ]]; then
        config_output=$(docker compose --env-file "$ENV_FILE" config --no-path-resolution 2>/dev/null || echo "")
    else
        config_output=$(docker compose config --no-path-resolution 2>/dev/null || echo "")
    fi
    
    if [[ -z "$config_output" ]]; then
        echo -e "${RED}❌ Failed to generate Docker Compose config${NC}"
        EXIT_CODE=1
        return 1
    fi
    
    local exposed_secrets=0
    
    # Check for sensitive variables in config output
    local sensitive_vars=(
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
    
    for var in "${sensitive_vars[@]}"; do
        local value=$(echo "$config_output" | grep "^      $var:" | head -1 | cut -d: -f2- | xargs || echo "NOT_FOUND")
        
        if [[ "$value" == "NOT_FOUND" ]]; then
            echo -e "${GREEN}  ✅ $var: NOT EXPOSED${NC}"
        elif [[ -z "$value" ]]; then
            echo -e "${GREEN}  ✅ $var: MASKED (empty)${NC}"
        elif [[ "$value" == \$* ]]; then
            echo -e "${GREEN}  ✅ $var: MASKED (\$VAR)${NC}"
        elif is_placeholder "$value" "$var"; then
            echo -e "${YELLOW}  ⚠️  $var: PLACEHOLDER VISIBLE${NC}"
            echo -e "     Value: $value"
            exposed_secrets=$((exposed_secrets + 1))
        else
            echo -e "${RED}  ❌ $var: EXPOSED: $value${NC}"
            exposed_secrets=$((exposed_secrets + 1))
        fi
    done
    
    if [[ $exposed_secrets -gt 0 ]]; then
        echo -e "${RED}  ❌ Found $exposed_secrets exposed secret(s) in Docker Compose config${NC}"
        EXIT_CODE=1
    else
        echo -e "${GREEN}  ✅ No exposed secrets in Docker Compose config${NC}"
    fi
}

# Function to validate encryption key format
validate_encryption_key() {
    echo -e "\n${YELLOW}🔑 Validating encryption key format...${NC}"
    
    if [[ -f ".env.local" ]]; then
        local encryption_key=$(grep "^ENCRYPTION_KEY=" .env.local 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")
        
        if [[ -z "$encryption_key" ]]; then
            echo -e "${YELLOW}  ⚠️  ENCRYPTION_KEY not found or empty${NC}"
        elif [[ ${#encryption_key} -eq 64 ]] && [[ "$encryption_key" =~ ^[a-fA-F0-9]{64}$ ]]; then
            echo -e "${GREEN}  ✅ ENCRYPTION_KEY: Valid 32-byte hex string${NC}"
        elif is_placeholder "$encryption_key" "ENCRYPTION_KEY"; then
            echo -e "${RED}  ❌ ENCRYPTION_KEY: PLACEHOLDER DETECTED${NC}"
            EXIT_CODE=1
        else
            echo -e "${YELLOW}  ⚠️  ENCRYPTION_KEY: Invalid format (expected 32-byte hex string)${NC}"
            echo -e "     Length: ${#encryption_key}, Expected: 64"
            EXIT_CODE=1
        fi
    fi
}

# Main validation logic
main() {
    echo -e "${BLUE}Starting runtime secret validation...${NC}"
    
    # Determine which environment file to validate
    local env_file_to_validate="${ENV_FILE:-.env.local}"
    
    # Validate environment file
    if [[ -f "$env_file_to_validate" ]]; then
        validate_env_file "$env_file_to_validate" "current"
    else
        echo -e "${RED}❌ Environment file not found: $env_file_to_validate${NC}"
        EXIT_CODE=1
    fi
    
    # Only validate additional files if we're using the default .env.local
    if [[ -z "$ENV_FILE" ]]; then
        # Also validate production if it exists and we're not already validating it
        if [[ "$env_file_to_validate" != ".env.production" ]] && [[ -f ".env.production" ]]; then
            validate_env_file ".env.production" "production"
        fi
        
        # Validate Docker Compose configuration
        validate_docker_compose
    fi
    
    # Validate encryption key format
    validate_encryption_key
    
    # Final result
    echo -e "\n${BLUE}📊 Validation Summary${NC}"
    echo "====================="
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        echo -e "${GREEN}✅ All validations passed! Ready for deployment.${NC}"
    else
        echo -e "${RED}❌ Validation failed! Please fix placeholder values before deployment.${NC}"
        echo -e "\n${YELLOW}Next steps:${NC}"
        echo "1. Replace all placeholder values with actual secure values"
        echo "2. Generate strong passwords and API keys"
        echo "3. Run this validation script again"
        echo "4. Ensure Docker Compose config masks sensitive values"
    fi
    
    return $EXIT_CODE
}

# Run main function
main "$@"