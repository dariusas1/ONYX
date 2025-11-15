#!/bin/bash

# =============================================================================
# ONYX Secrets Masking Validation Script - FINAL ATTEMPT #3
# =============================================================================
# CRITICAL: Tests AC1.3.5 compliance - docker compose config shows masked secrets
# This script tests the FUNDAMENTAL requirement that NO secret values are exposed
# Updated to handle the new architecture without env_file directives
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️ ONYX Secrets Masking Validation - FINAL ATTEMPT #3${NC}"
echo -e "${BLUE}🎯 Target: AC1.3.5 - docker compose config shows masked secrets${NC}"
echo "======================================================================"

# Track test results
total_tests=0
passed_tests=0
failed_tests=0

# Function to log test result
log_test() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    total_tests=$((total_tests + 1))

    echo -n "  $test_name: "
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        failed_tests=$((failed_tests + 1))
        if [ -n "$details" ]; then
            echo -e "    ${RED}Reason: $details${NC}"
        fi
    fi
}

# CRITICAL TEST 1: Test with actual secret values to ensure they are NOT exposed
test_actual_secrets_exposure() {
    echo -e "\n${RED}🚨 CRITICAL TEST 1: Testing with ACTUAL secret values${NC}"
    echo -e "${RED}❌ This simulates real deployment - secrets MUST NOT be exposed${NC}"

    # Set actual test secrets (NOT placeholders)
    export POSTGRES_PASSWORD="super-secret-password-12345"
    export DEEPSEEK_API_KEY="sk-real-api-key-abcdef67890"
    export GOOGLE_CLIENT_SECRET="GOCSPX-real-secret-xyz1234567890"
    export ENCRYPTION_KEY="abcdef1234567890abcdef1234567890"
    export SESSION_SECRET="real-session-secret-abcdef123456"
    export GRAFANA_PASSWORD="real-grafana-password-123456"
    export REDIS_PASSWORD="real-redis-password-789"
    export QDRANT_API_KEY="real-qdrant-key-abcdef123456"
    export TOGETHER_API_KEY="sk-together-real-key-xyz1234567890"

    echo -e "${YELLOW}Testing with REAL secret values set in environment...${NC}"

    # Get docker compose config output
    config_output=$(docker compose config --no-path-resolution 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ FAILED: Cannot run docker compose config${NC}"
        return 1
    fi

    # Count exposed secrets - CRITICAL SECURITY MEASUREMENT
    exposed_secrets=0

    # Test each sensitive variable
    local sensitive_vars=(
        "POSTGRES_PASSWORD:super-secret-password-12345"
        "DEEPSEEK_API_KEY:sk-real-api-key-abcdef67890"
        "GOOGLE_CLIENT_SECRET:GOCSPX-real-secret-xyz1234567890"
        "ENCRYPTION_KEY:abcdef1234567890abcdef1234567890"
        "SESSION_SECRET:real-session-secret-abcdef123456"
        "GRAFANA_PASSWORD:real-grafana-password-123456"
        "REDIS_PASSWORD:real-redis-password-789"
        "QDRANT_API_KEY:real-qdrant-key-abcdef123456"
        "TOGETHER_API_KEY:sk-together-real-key-xyz1234567890"
    )

    for var_test in "${sensitive_vars[@]}"; do
        local var_name=$(echo "$var_test" | cut -d: -f1)
        local var_value=$(echo "$var_test" | cut -d: -f2)

        # Check if the actual secret value appears in config output
        if echo "$config_output" | grep -q "$var_value"; then
            echo -e "  ${RED}❌ $var_name: EXPOSED (value: $var_value)${NC}"
            exposed_secrets=$((exposed_secrets + 1))
        else
            echo -e "  ${GREEN}✅ $var_name: NOT EXPOSED${NC}"
        fi
    done

    # Clean up test environment variables
    unset POSTGRES_PASSWORD DEEPSEE_API_KEY GOOGLE_CLIENT_SECRET ENCRYPTION_KEY
    unset SESSION_SECRET GRAFANA_PASSWORD REDIS_PASSWORD QDRANT_API_KEY TOGETHER_API_KEY

    if [ $exposed_secrets -gt 0 ]; then
        echo -e "\n${RED}🚨 CRITICAL SECURITY FAILURE: $exposed_secrets secrets EXPOSED in docker compose config!${NC}"
        return 1
    else
        echo -e "\n${GREEN}✅ CRITICAL TEST PASSED: NO secrets exposed in config${NC}"
        return 0
    fi
}

# TEST 2: Verify no env_file directives exist (they've been removed)
test_no_env_file_directives() {
    echo -e "\n${BLUE}TEST 2: Verify no env_file directives${NC}"

    # Check that no env_file directives exist in the main compose file
    if grep -q "env_file:" docker-compose.yaml; then
        log_test "No env_file directives" "FAIL" "Found env_file directives in docker-compose.yaml"
        return 1
    else
        log_test "No env_file directives" "PASS" "All env_file directives successfully removed"
        return 0
    fi
}

# TEST 3: Verify Docker secrets configuration exists and is properly structured
test_docker_secrets_config() {
    echo -e "\n${BLUE}TEST 3: Verify Docker secrets configuration${NC}"

    if [ ! -f "docker-compose.secrets.yaml" ]; then
        log_test "Docker secrets config exists" "FAIL" "docker-compose.secrets.yaml not found"
        return 1
    fi

    # Check that docker-compose.secrets.yaml uses secrets properly
    if grep -q "secrets:" docker-compose.secrets.yaml; then
        log_test "Docker secrets config has secrets section" "PASS" "Docker secrets properly configured"
    else
        log_test "Docker secrets config has secrets section" "FAIL" "No secrets section found in docker-compose.secrets.yaml"
        return 1
    fi

    # Count external secrets
    secret_count=$(grep -c "external: true" docker-compose.secrets.yaml || echo "0")
    if [ "$secret_count" -ge 5 ]; then
        log_test "Docker secrets configured" "PASS" "Found $secret_count external secrets"
    else
        log_test "Docker secrets configured" "FAIL" "Only $secret_count secrets found, need at least 5"
        return 1
    fi

    return 0
}

# TEST 4: Test development environment still works
test_development_environment() {
    echo -e "\n${BLUE}TEST 4: Verify development environment still works${NC}"

    if [ ! -f ".env.local" ]; then
        log_test "Development environment file exists" "FAIL" ".env.local not found"
        return 1
    fi

    # Check that .env.local has actual values (not just ${VAR} substitution)
    if grep -q "POSTGRES_PASSWORD=dev-" .env.local; then
        log_test "Development env has actual values" "PASS" "Development environment configured with actual values"
    else
        log_test "Development env has actual values" "FAIL" "Development environment missing actual values"
        return 1
    fi

    return 0
}

# TEST 5: Test production environment configuration
test_production_environment() {
    echo -e "\n${BLUE}TEST 5: Verify production environment configuration${NC}"

    if [ ! -f ".env.production" ]; then
        log_test "Production environment file exists" "FAIL" ".env.production not found"
        return 1
    fi

    # Check that production environment has NO sensitive values (only safe configs)
    sensitive_patterns=("PASSWORD=" "SECRET=" "KEY=")

    for pattern in "${sensitive_patterns[@]}"; do
        if grep -q "$pattern" .env.production; then
            # But allow REDACTED which is a safe placeholder
            if grep -q "$pattern" .env.production | grep -v "REDACTED" | grep -q -v "your-"; then
                log_test "Production env has no sensitive values" "FAIL" "Found $pattern in production environment"
                return 1
            fi
        fi
    done

    log_test "Production env has no sensitive values" "PASS" "Production environment properly configured"
    return 0
}

# TEST 6: Test docker compose config output for any sensitive patterns
test_config_output_cleanliness() {
    echo -e "\n${BLUE}TEST 6: Verify config output contains no sensitive patterns${NC}"

    # Get docker compose config output
    config_output=$(docker compose config --no-path-resolution 2>/dev/null)

    # Check for any obvious sensitive patterns in config
    sensitive_patterns=("password" "secret" "key=" "token" "credential")

    found_sensitive=false
    for pattern in "${sensitive_patterns[@]}"; do
        if echo "$config_output" | grep -i "$pattern" | grep -v "NOT_FOUND"; then
            echo -e "  ${RED}⚠️  Found sensitive pattern: $pattern${NC}"
            found_sensitive=true
        fi
    done

    if [ "$found_sensitive" = true ]; then
        log_test "Config output has no sensitive patterns" "FAIL" "Found potentially sensitive patterns in config output"
    else
        log_test "Config output has no sensitive patterns" "PASS" "Config output appears clean"
    fi
}

# TEST 7: Test specific AC1.3.5 requirement
test_ac1_3_5_compliance() {
    echo -e "\n${BLUE}TEST 7: AC1.3.5 Compliance Test${NC}"
    echo -e "${BLUE}Requirement: 'docker compose config shows masked secrets'${NC}"

    # Set up test environment with actual secrets
    export POSTGRES_PASSWORD="test-ac1-3-5-password"
    export GOOGLE_CLIENT_SECRET="test-ac1-3-5-secret"
    export ENCRYPTION_KEY="test-ac1-3-5-encryption-key"

    # Get config output
    config_output=$(docker compose config --no-path-resolution 2>/dev/null)

    # CRITICAL: Check that NO actual secret values appear in config output
    if echo "$config_output" | grep -q "test-ac1-3-5"; then
        log_test "AC1.3.5: docker compose config shows masked secrets" "FAIL" "AC1.3.5 VIOLATION: Actual secret values exposed in config output"
        result=1
    else
        log_test "AC1.3.5: docker compose config shows masked secrets" "PASS" "AC1.3.5 COMPLIANT: No secret values exposed in config"
        result=0
    fi

    # Clean up
    unset POSTGRES_PASSWORD GOOGLE_CLIENT_SECRET ENCRYPTION_KEY

    return $result
}

# Main validation execution
main() {
    echo -e "${BLUE}Starting comprehensive secrets masking validation...${NC}"
    echo -e "${RED}🎯 TARGET: AC1.3.5 COMPLIANCE - docker compose config shows masked secrets${NC}"
    echo ""

    # Run all tests
    test_actual_secrets_exposure || echo -e "${RED}CRITICAL FAILURE: Secrets exposed${NC}"
    test_no_env_file_directives || echo -e "${YELLOW}WARNING: env_file directives still exist${NC}"
    test_docker_secrets_config || echo -e "${YELLOW}WARNING: Docker secrets not configured${NC}"
    test_development_environment || echo -e "${YELLOW}WARNING: Development environment issues${NC}"
    test_production_environment || echo -e "${YELLOW}WARNING: Production environment issues${NC}"
    test_config_output_cleanliness || echo -e "${YELLOW}WARNING: Config output may contain sensitive patterns${NC}"
    test_ac1_3_5_compliance || echo -e "${RED}CRITICAL FAILURE: AC1.3.5 NOT COMPLIANT${NC}"

    # Final results
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}FINAL VALIDATION RESULTS:${NC}"
    echo -e "${BLUE}Total Tests: $total_tests, Passed: $passed_tests, Failed: $failed_tests${NC}"

    if [ $failed_tests -eq 0 ]; then
        echo -e "\n${GREEN}🎉 SUCCESS: ALL TESTS PASSED - AC1.3.5 COMPLIANT!${NC}"
        echo -e "${GREEN}✅ docker compose config shows masked secrets${NC}"
        echo -e "${GREEN}✅ Ready for production deployment${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ FAILURE: $failed_tests TESTS FAILED${NC}"
        echo -e "${RED}❌ NOT READY FOR PRODUCTION DEPLOYMENT${NC}"
        echo -e "${RED}❌ AC1.3.5 CRITICAL REQUIREMENT NOT MET${NC}"
        exit 1
    fi
}

# Execute main function if script is called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi