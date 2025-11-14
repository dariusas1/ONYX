#!/bin/bash
################################################################################
# Qdrant Integration Test Suite
#
# Tests Docker Compose deployment, health checks, collection creation,
# and basic CRUD operations for the Qdrant vector database.
#
# Usage:
#   bash tests/integration/test_qdrant_setup.sh
#
# Prerequisites:
#   - Docker Compose running
#   - jq installed (for JSON parsing)
#   - curl installed
################################################################################

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_test_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_test_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it: sudo apt-get install jq"
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed. Please install it: sudo apt-get install curl"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed."
        exit 1
    fi

    log_info "All prerequisites met"
}

# Test: Start Qdrant service
test_start_qdrant() {
    log_info "Test: Starting Qdrant service..."

    docker compose up -d qdrant

    if [ $? -eq 0 ]; then
        log_test_pass "Qdrant service started successfully"
    else
        log_test_fail "Failed to start Qdrant service"
        return 1
    fi
}

# Test: Wait for Qdrant to be healthy
test_qdrant_health() {
    log_info "Test: Waiting for Qdrant health check..."

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        HEALTH_STATUS=$(curl -s http://localhost:6333/health | jq -r '.status' 2>/dev/null || echo "error")

        if [ "$HEALTH_STATUS" = "ok" ]; then
            log_test_pass "Qdrant health check passed (status: ok)"
            return 0
        fi

        ((RETRY_COUNT++))
        echo "Waiting for Qdrant... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    done

    log_test_fail "Qdrant health check failed after $MAX_RETRIES attempts"
    return 1
}

# Test: Verify Qdrant is accessible on port 6333
test_qdrant_accessibility() {
    log_info "Test: Verifying Qdrant REST API accessibility..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/health)

    if [ "$HTTP_CODE" = "200" ]; then
        log_test_pass "Qdrant REST API accessible on port 6333 (HTTP 200)"
    else
        log_test_fail "Qdrant REST API returned HTTP $HTTP_CODE (expected 200)"
        return 1
    fi
}

# Test: Docker healthcheck configuration
test_docker_healthcheck() {
    log_info "Test: Verifying Docker healthcheck configuration..."

    HEALTH=$(docker inspect manus-qdrant --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_found")

    if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "starting" ]; then
        log_test_pass "Docker healthcheck configured and running (status: $HEALTH)"
    else
        log_test_fail "Docker healthcheck not working properly (status: $HEALTH)"
        return 1
    fi
}

# Test: Volume mount for persistence
test_volume_mount() {
    log_info "Test: Verifying volume mount for persistence..."

    VOLUME=$(docker inspect manus-qdrant --format='{{range .Mounts}}{{if eq .Destination "/qdrant/storage"}}{{.Name}}{{end}}{{end}}' 2>/dev/null)

    if [ -n "$VOLUME" ]; then
        log_test_pass "Volume mounted at /qdrant/storage (volume: $VOLUME)"
    else
        log_test_fail "Volume not properly mounted at /qdrant/storage"
        return 1
    fi
}

# Test: Initialize collection
test_collection_initialization() {
    log_info "Test: Running collection initialization script..."

    if python3 scripts/init-qdrant.py; then
        log_test_pass "Collection initialization script completed successfully"
    else
        log_test_fail "Collection initialization script failed"
        return 1
    fi
}

# Test: Verify collection exists
test_collection_exists() {
    log_info "Test: Verifying 'documents' collection exists..."

    COLLECTIONS=$(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name' 2>/dev/null)

    if echo "$COLLECTIONS" | grep -q "documents"; then
        log_test_pass "Collection 'documents' exists"
    else
        log_test_fail "Collection 'documents' not found"
        log_error "Available collections: $COLLECTIONS"
        return 1
    fi
}

# Test: Verify collection configuration
test_collection_configuration() {
    log_info "Test: Verifying collection configuration..."

    COLLECTION_INFO=$(curl -s http://localhost:6333/collections/documents)

    VECTOR_SIZE=$(echo "$COLLECTION_INFO" | jq -r '.result.config.params.vectors.size')
    DISTANCE=$(echo "$COLLECTION_INFO" | jq -r '.result.config.params.vectors.distance')
    ON_DISK=$(echo "$COLLECTION_INFO" | jq -r '.result.config.params.vectors.on_disk')

    ERRORS=0

    if [ "$VECTOR_SIZE" = "1536" ]; then
        log_test_pass "Vector size is 1536 dimensions (OpenAI text-embedding-3-small)"
    else
        log_test_fail "Vector size is $VECTOR_SIZE (expected 1536)"
        ((ERRORS++))
    fi

    if [ "$DISTANCE" = "Cosine" ]; then
        log_test_pass "Distance metric is Cosine"
    else
        log_test_fail "Distance metric is $DISTANCE (expected Cosine)"
        ((ERRORS++))
    fi

    if [ "$ON_DISK" = "true" ]; then
        log_test_pass "On-disk storage is enabled"
    else
        log_warning "On-disk storage is $ON_DISK (expected true)"
    fi

    return $ERRORS
}

# Test: Collection is idempotent
test_collection_idempotent() {
    log_info "Test: Verifying collection creation is idempotent..."

    # Run initialization script again
    if python3 scripts/init-qdrant.py > /tmp/qdrant_init_output.log 2>&1; then
        if grep -q "already exists" /tmp/qdrant_init_output.log; then
            log_test_pass "Collection creation is idempotent (already exists check works)"
        else
            log_warning "Idempotency message not found, but script succeeded"
            log_test_pass "Collection creation script can be run multiple times"
        fi
    else
        log_test_fail "Running initialization script second time failed"
        return 1
    fi
}

# Test: Basic vector operations
test_vector_operations() {
    log_info "Test: Testing basic vector operations..."

    # Create a test point
    TEST_PAYLOAD=$(cat <<EOF
{
    "points": [
        {
            "id": "test-doc-1",
            "vector": $(python3 -c "import json; print(json.dumps([0.1] * 1536))"),
            "payload": {
                "text": "This is a test document",
                "title": "Test Document",
                "source": "integration_test",
                "doc_id": "test-doc-1"
            }
        }
    ]
}
EOF
)

    # Upsert the test point
    UPSERT_RESPONSE=$(curl -s -X PUT http://localhost:6333/collections/documents/points \
        -H "Content-Type: application/json" \
        -d "$TEST_PAYLOAD")

    UPSERT_STATUS=$(echo "$UPSERT_RESPONSE" | jq -r '.status')

    if [ "$UPSERT_STATUS" = "ok" ]; then
        log_test_pass "Vector upsert successful"
    else
        log_test_fail "Vector upsert failed: $UPSERT_RESPONSE"
        return 1
    fi

    # Search for the test point
    SEARCH_PAYLOAD=$(cat <<EOF
{
    "vector": $(python3 -c "import json; print(json.dumps([0.1] * 1536))"),
    "limit": 5
}
EOF
)

    SEARCH_RESPONSE=$(curl -s -X POST http://localhost:6333/collections/documents/points/search \
        -H "Content-Type: application/json" \
        -d "$SEARCH_PAYLOAD")

    SEARCH_RESULTS=$(echo "$SEARCH_RESPONSE" | jq -r '.result | length')

    if [ "$SEARCH_RESULTS" -gt 0 ]; then
        log_test_pass "Vector search successful (found $SEARCH_RESULTS results)"
    else
        log_test_fail "Vector search returned no results"
        return 1
    fi
}

# Test: Data persistence
test_data_persistence() {
    log_info "Test: Testing data persistence across container restarts..."

    # Get current document count
    COUNT_BEFORE=$(curl -s http://localhost:6333/collections/documents | jq -r '.result.points_count')

    if [ -z "$COUNT_BEFORE" ] || [ "$COUNT_BEFORE" = "null" ]; then
        COUNT_BEFORE=0
    fi

    log_info "Document count before restart: $COUNT_BEFORE"

    # Restart Qdrant container
    log_info "Restarting Qdrant container..."
    docker compose restart qdrant

    # Wait for Qdrant to be healthy again
    sleep 10

    MAX_RETRIES=20
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        HEALTH_STATUS=$(curl -s http://localhost:6333/health | jq -r '.status' 2>/dev/null || echo "error")

        if [ "$HEALTH_STATUS" = "ok" ]; then
            break
        fi

        ((RETRY_COUNT++))
        sleep 2
    done

    # Get document count after restart
    COUNT_AFTER=$(curl -s http://localhost:6333/collections/documents | jq -r '.result.points_count')

    if [ -z "$COUNT_AFTER" ] || [ "$COUNT_AFTER" = "null" ]; then
        COUNT_AFTER=0
    fi

    log_info "Document count after restart: $COUNT_AFTER"

    if [ "$COUNT_BEFORE" = "$COUNT_AFTER" ]; then
        log_test_pass "Data persisted across container restart (count: $COUNT_AFTER)"
    else
        log_test_fail "Data loss detected (before: $COUNT_BEFORE, after: $COUNT_AFTER)"
        return 1
    fi
}

# Test: API endpoints
test_api_endpoints() {
    log_info "Test: Verifying all API endpoints..."

    ERRORS=0

    # GET /collections
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/collections)
    if [ "$HTTP_CODE" = "200" ]; then
        log_test_pass "GET /collections returns HTTP 200"
    else
        log_test_fail "GET /collections returned HTTP $HTTP_CODE"
        ((ERRORS++))
    fi

    # GET /collections/documents
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/collections/documents)
    if [ "$HTTP_CODE" = "200" ]; then
        log_test_pass "GET /collections/documents returns HTTP 200"
    else
        log_test_fail "GET /collections/documents returned HTTP $HTTP_CODE"
        ((ERRORS++))
    fi

    return $ERRORS
}

# Main test execution
main() {
    echo "================================================================================"
    echo "Qdrant Integration Test Suite"
    echo "================================================================================"
    echo ""

    check_prerequisites

    # Run tests
    test_start_qdrant || true
    sleep 5
    test_qdrant_health || exit 1
    test_qdrant_accessibility || true
    test_docker_healthcheck || true
    test_volume_mount || true
    test_collection_initialization || true
    test_collection_exists || exit 1
    test_collection_configuration || true
    test_collection_idempotent || true
    test_vector_operations || true
    test_data_persistence || true
    test_api_endpoints || true

    # Summary
    echo ""
    echo "================================================================================"
    echo "Test Summary"
    echo "================================================================================"
    echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed. Please review the output above.${NC}"
        exit 1
    fi
}

# Run main function
main
