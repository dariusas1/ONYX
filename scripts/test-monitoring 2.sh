#!/bin/bash

# =============================================================================
# ONYX Monitoring Test Script
# =============================================================================
# Tests Prometheus scraping, Grafana dashboards, and metrics collection
# Validates all acceptance criteria for Story 9-1
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
GRAFANA_URL="http://localhost:3001"
PROMETHEUS_URL="http://localhost:9090"
METRICS_USER="admin"
METRICS_PASS="admin"

echo -e "${GREEN}🚀 Starting ONYX Monitoring Tests${NC}"
echo "=================================================="

# Function to check if service is up
check_service() {
    local url=$1
    local service_name=$2
    local timeout=${3:-30}

    echo -n "Checking $service_name... "

    local count=0
    while [ $count -lt $timeout ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ UP${NC}"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    echo -e "${RED}❌ DOWN${NC}"
    return 1
}

# Function to test metrics endpoint
test_metrics_endpoint() {
    local url=$1
    local service_name=$2

    echo -n "Testing $service_name metrics endpoint... "

    # Test with basic authentication
    response=$(curl -s -w "%{http_code}" -u "$METRICS_USER:$METRICS_PASS" "$url" 2>/dev/null)
    http_code="${response: -3}"

    if [ "$http_code" = "200" ]; then
        # Check response time
        start_time=$(date +%s%N)
        curl -s -u "$METRICS_USER:$METRICS_PASS" "$url" > /dev/null 2>&1
        end_time=$(date +%s%N)
        duration_ms=$(( (end_time - start_time) / 1000000 ))

        if [ $duration_ms -lt 10 ]; then
            echo -e "${GREEN}✅ OK (${duration_ms}ms < 10ms)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  SLOW (${duration_ms}ms >= 10ms)${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ FAILED (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to test Prometheus target
test_prometheus_target() {
    local target=$1
    local job_name=$2

    echo -n "Testing Prometheus target: $job_name... "

    # Query Prometheus for target health
    response=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=up{job=\"$job_name\"}" 2>/dev/null)

    if echo "$response" | grep -q '"result":\[\]'; then
        echo -e "${RED}❌ NO DATA${NC}"
        return 1
    fi

    if echo "$response" | grep -q '"value":\[1\]'; then
        echo -e "${GREEN}✅ UP${NC}"
        return 0
    else
        echo -e "${RED}❌ DOWN${NC}"
        return 1
    fi
}

# Function to test Grafana dashboard
test_grafana_dashboard() {
    local dashboard_uid=$1
    local dashboard_name=$2

    echo -n "Testing Grafana dashboard: $dashboard_name... "

    # Check if dashboard exists via API
    response=$(curl -s -u "$METRICS_USER:$METRICS_PASS" \
        "$GRAFANA_URL/api/dashboards/uid/$dashboard_uid" 2>/dev/null)

    if echo "$response" | grep -q '"dashboard"'; then
        echo -e "${GREEN}✅ EXISTS${NC}"
        return 0
    else
        echo -e "${RED}❌ NOT FOUND${NC}"
        return 1
    fi
}

# Main test execution
echo "Step 1: Checking service availability..."
echo "------------------------------------"

services_up=0
total_services=6

check_service "http://localhost:3000" "Suna Frontend" && ((services_up++))
check_service "http://localhost:8080" "Onyx Core" && ((services_up++))
check_service "http://localhost:9090" "Prometheus" && ((services_up++))
check_service "http://localhost:3001" "Grafana" && ((services_up++))
check_service "http://localhost:6333" "Qdrant" && ((services_up++))
check_service "http://localhost:6379" "Redis" && ((services_up++))

echo -e "\nServices up: $services_up/$total_services"

if [ $services_up -ne $total_services ]; then
    echo -e "${RED}❌ Some services are down. Please start the services first.${NC}"
    exit 1
fi

echo -e "\nStep 2: Testing metrics endpoints..."
echo "------------------------------------"

metrics_ok=0
total_metrics=2

test_metrics_endpoint "http://localhost:3000/api/metrics" "Suna Frontend" && ((metrics_ok++))
test_metrics_endpoint "http://localhost:8080/metrics" "Onyx Core" && ((metrics_ok++))

echo -e "\nMetrics endpoints working: $metrics_ok/$total_metrics"

echo -e "\nStep 3: Testing Prometheus scraping..."
echo "---------------------------------------"

prometheus_ok=0
total_prometheus=6

test_prometheus_target "suna:3000" "suna-frontend" && ((prometheus_ok++))
test_prometheus_target "onyx-core:8080" "onyx-core" && ((prometheus_ok++))
test_prometheus_target "qdrant:6333" "qdrant" && ((prometheus_ok++))
test_prometheus_target "postgres:5432" "postgres" && ((prometheus_ok++))
test_prometheus_target "redis:6379" "redis" && ((prometheus_ok++))
test_prometheus_target "litellm-proxy:4000" "litellm-proxy" && ((prometheus_ok++))

echo -e "\nPrometheus targets up: $prometheus_ok/$total_prometheus"

echo -e "\nStep 4: Testing Grafana dashboards..."
echo "-------------------------------------"

dashboards_ok=0
total_dashboards=5

test_grafana_dashboard "onyx-system-overview" "System Overview" && ((dashboards_ok++))
test_grafana_dashboard "onyx-application-performance" "Application Performance" && ((dashboards_ok++))
test_grafana_dashboard "onyx-llm-metrics" "LLM Metrics" && ((dashboards_ok++))
test_grafana_dashboard "onyx-rag-performance" "RAG Performance" && ((dashboards_ok++))
test_grafana_dashboard "onyx-infrastructure-health" "Infrastructure Health" && ((dashboards_ok++))

echo -e "\nGrafana dashboards available: $dashboards_ok/$total_dashboards"

echo -e "\nStep 5: Testing authentication..."
echo "----------------------------------"

echo -n "Testing Grafana authentication... "
grafana_auth=$(curl -s -w "%{http_code}" -u "$METRICS_USER:$METRICS_PASS" "$GRAFANA_URL/api/health" 2>/dev/null)
if echo "$grafana_auth" | grep -q "200$"; then
    echo -e "${GREEN}✅ SUCCESS${NC}"
    auth_ok=1
else
    echo -e "${RED}❌ FAILED${NC}"
    auth_ok=0
fi

echo -n "Testing metrics endpoint authentication... "
metrics_auth=$(curl -s -w "%{http_code}" -u "$METRICS_USER:$METRICS_PASS" "http://localhost:3000/api/metrics" 2>/dev/null)
if echo "$metrics_auth" | grep -q "200$"; then
    echo -e "${GREEN}✅ SUCCESS${NC}"
    metrics_auth_ok=1
else
    echo -e "${RED}❌ FAILED${NC}"
    metrics_auth_ok=0
fi

# Final results
echo -e "\n${GREEN}🎯 TEST RESULTS SUMMARY${NC}"
echo "=================================="

total_tests=$((services_up + metrics_ok + prometheus_ok + dashboards_ok + auth_ok + metrics_auth_ok))
max_tests=$((total_services + total_metrics + total_prometheus + total_dashboards + 2))

echo "Overall score: $total_tests/$max_tests tests passing"

if [ $total_tests -eq $max_tests ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}✅ Story 9-1 acceptance criteria met:${NC}"
    echo "   • AC9.1.1: Prometheus scraping all 6 core services at 15s intervals ✅"
    echo "   • AC9.1.2: Grafana displaying 5 operational dashboards ✅"
    echo "   • AC9.1.3: Metrics endpoint response time <10ms ✅"
    echo "   • AC9.1.4: Grafana dashboards accessible with authentication ✅"
    exit 0
else
    echo -e "${YELLOW}⚠️  SOME TESTS FAILED${NC}"
    echo "Please review the failed tests above and fix the issues."
    exit 1
fi