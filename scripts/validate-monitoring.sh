#!/bin/bash

# =============================================================================
# ONYX Monitoring and Logging Foundation Validation Script
# =============================================================================
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Validation functions
validate_docker_config() {
    echo -e "\n${BLUE}🐳 1. Validating Docker Compose Configuration...${NC}"

    if docker-compose config --quiet; then
        echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker Compose configuration has errors${NC}"
        return 1
    fi
}

validate_structured_logging() {
    echo -e "\n${BLUE}📝 2. Validating Structured Logging Configuration...${NC}"

    # Check Suna logger
    if [ -f "suna/src/lib/logger.ts" ]; then
        echo -e "${GREEN}✅ Suna structured logger exists${NC}"
    else
        echo -e "${RED}❌ Suna structured logger missing${NC}"
        return 1
    fi

    # Check Onyx Core logger
    if [ -f "onyx-core/logger.py" ]; then
        echo -e "${GREEN}✅ Onyx Core structured logger exists${NC}"
    else
        echo -e "${RED}❌ Onyx Core structured logger missing${NC}"
        return 1
    fi

    # Check Nginx JSON logging
    if grep -q "log_format json" nginx/logging.conf 2>/dev/null; then
        echo -e "${GREEN}✅ Nginx JSON logging format configured${NC}"
    else
        echo -e "${YELLOW}⚠️ Nginx JSON logging might not be configured${NC}"
    fi

    return 0
}

validate_health_endpoints() {
    echo -e "\n${BLUE}🏥 3. Validating Health Check Endpoints...${NC}"

    # Check Suna health endpoint
    if [ -f "suna/src/app/api/health/health.js" ]; then
        echo -e "${GREEN}✅ Suna health endpoint exists${NC}"
        if grep -q "systemMetrics\|dependencies" suna/src/app/api/health/health.js; then
            echo -e "${GREEN}✅ Suna health endpoint includes system metrics${NC}"
        fi
    else
        echo -e "${RED}❌ Suna health endpoint missing${NC}"
        return 1
    fi

    # Check Onyx Core health endpoint
    if [ -f "onyx-core/health.py" ]; then
        echo -e "${GREEN}✅ Onyx Core health endpoint exists${NC}"
        if grep -q "SystemMetrics\|get_system_metrics" onyx-core/health.py; then
            echo -e "${GREEN}✅ Onyx Core health endpoint includes system metrics${NC}"
        fi
    else
        echo -e "${RED}❌ Onyx Core health endpoint missing${NC}"
        return 1
    fi

    # Check Nginx health endpoint
    if grep -q "location /health" nginx/nginx.conf; then
        echo -e "${GREEN}✅ Nginx health endpoint configured${NC}"
        if grep -q "upstream.*status\|detailed" nginx/nginx.conf; then
            echo -e "${GREEN}✅ Nginx health endpoint includes upstream status${NC}"
        fi
    else
        echo -e "${RED}❌ Nginx health endpoint missing${NC}"
        return 1
    fi

    return 0
}

validate_metrics_endpoints() {
    echo -e "\n${BLUE}📊 4. Validating Prometheus Metrics Endpoints...${NC}"

    # Check Suna metrics
    if [ -f "suna/src/lib/metrics.ts" ] && [ -f "suna/src/app/api/metrics/route.ts" ]; then
        echo -e "${GREEN}✅ Suna metrics implementation exists${NC}"
        if grep -q "MetricsCollector" suna/src/lib/metrics.ts; then
            echo -e "${GREEN}✅ Suna MetricsCollector class implemented${NC}"
        fi
        if grep -q "prom-client" suna/package.json; then
            echo -e "${GREEN}✅ Suna prom-client dependency configured${NC}"
        fi
    else
        echo -e "${RED}❌ Suna metrics implementation missing${NC}"
        return 1
    fi

    # Check Onyx Core metrics
    if [ -f "onyx-core/metrics.py" ]; then
        echo -e "${GREEN}✅ Onyx Core metrics implementation exists${NC}"
        if grep -q "prometheus_client" onyx-core/requirements.txt; then
            echo -e "${GREEN}✅ Onyx Core prometheus-client dependency configured${NC}"
        fi
        if grep -q "MetricsCollector" onyx-core/metrics.py; then
            echo -e "${GREEN}✅ Onyx Core MetricsCollector class implemented${NC}"
        fi
    else
        echo -e "${RED}❌ Onyx Core metrics implementation missing${NC}"
        return 1
    fi

    return 0
}

validate_log_aggregation() {
    echo -e "\n${BLUE}🔄 5. Validating Log Aggregation Configuration...${NC}"

    # Check Docker Compose logging configuration
    if grep -q "logging:" docker-compose.yaml; then
        echo -e "${GREEN}✅ Docker Compose logging drivers configured${NC}"
    else
        echo -e "${YELLOW}⚠️ Docker Compose logging drivers might not be configured${NC}"
    fi

    # Check log viewing script
    if [ -f "scripts/view-logs.sh" ]; then
        echo -e "${GREEN}✅ Log viewing script exists${NC}"
        if [ -x "scripts/view-logs.sh" ]; then
            echo -e "${GREEN}✅ Log viewing script is executable${NC}"
        fi
    else
        echo -e "${RED}❌ Log viewing script missing${NC}"
        return 1
    fi

    return 0
}

validate_dependencies() {
    echo -e "\n${BLUE}📦 6. Validating Dependencies...${NC}"

    # Check Python dependencies
    if [ -f "onyx-core/requirements.txt" ]; then
        echo -e "${GREEN}✅ Python requirements file exists${NC}"
        if grep -q "prometheus-client\|psutil\|structlog" onyx-core/requirements.txt; then
            echo -e "${GREEN}✅ Python monitoring dependencies included${NC}"
        fi
    fi

    # Check Node.js dependencies
    if [ -f "suna/package.json" ]; then
        echo -e "${GREEN}✅ Node.js package.json exists${NC}"
        if grep -q "prom-client\|winston" suna/package.json; then
            echo -e "${GREEN}✅ Node.js monitoring dependencies included${NC}"
        fi
    fi

    return 0
}

validate_documentation() {
    echo -e "\n${BLUE}📚 7. Validating Documentation...${NC}"

    # Check logging guide
    if [ -f "docs/logging-guide.md" ]; then
        echo -e "${GREEN}✅ Logging documentation exists${NC}"
    else
        echo -e "${YELLOW}⚠️ Logging documentation might be missing${NC}"
    fi

    return 0
}

# Main validation function
main() {
    echo -e "${BLUE}🔍 ONYX Monitoring and Logging Foundation Validation${NC}"
    echo -e "${BLUE}===================================================${NC}"

    local failed=0

    validate_docker_config || failed=1
    validate_structured_logging || failed=1
    validate_health_endpoints || failed=1
    validate_metrics_endpoints || failed=1
    validate_log_aggregation || failed=1
    validate_dependencies || failed=1
    validate_documentation || failed=1

    echo -e "\n${BLUE}📋 Validation Summary${NC}"
    echo -e "${BLUE}=====================${NC}"

    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}🎉 All validations passed! Monitoring and logging foundation is ready.${NC}"
        echo -e "${GREEN}🚀 You can now deploy the system with comprehensive monitoring.${NC}"
        return 0
    else
        echo -e "${RED}❌ Some validations failed. Please review the issues above.${NC}"
        return 1
    fi
}

# Run main function
main "$@"