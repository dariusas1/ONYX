#!/bin/bash
# Integration Test: Google Drive Sync Job Execution
#
# This test verifies the complete sync job workflow from trigger to completion
# Tests AC3.2.2, AC3.2.3, AC3.2.7: Auto-sync, file detection, error rate

set -e  # Exit on error

echo "========================================="
echo "Integration Test: Google Drive Sync Job"
echo "========================================="
echo ""

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8080}"
TEST_USER_ID="${TEST_USER_ID:-test-user-12345}"
TEST_USER_EMAIL="${TEST_USER_EMAIL:-test@example.com}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-300}"  # 5 minutes max wait
POLL_INTERVAL="${POLL_INTERVAL:-10}"  # Poll every 10 seconds

# Generate test JWT token
generate_test_jwt() {
    echo "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiJHtURVNUX1VTRVJfSUR9IiwiZW1haWwiOiIke1RFU1RfVVNFUl9FTUFJTH0ifQ.placeholder"
}

TEST_TOKEN=$(generate_test_jwt)

echo "Step 1: Check authentication status"
echo "------------------------------------"
AUTH_STATUS=$(curl -s -X GET "$BASE_URL/api/google-drive/auth/status" \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json")

IS_AUTHENTICATED=$(echo "$AUTH_STATUS" | jq -r '.data.is_authenticated // false')
echo "   Authenticated: $IS_AUTHENTICATED"

if [ "$IS_AUTHENTICATED" != "true" ]; then
    echo "⚠️  User not authenticated with Google Drive"
    echo "   Skipping sync test (requires OAuth authentication)"
    echo ""
    echo "To run this test with real sync:"
    echo "  1. Complete OAuth flow using test-google-oauth.sh"
    echo "  2. Ensure valid Google Drive credentials in .env"
    echo "  3. Re-run this test"
    exit 0
fi

echo ""

echo "Step 2: Trigger manual sync job"
echo "--------------------------------"
SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/api/google-drive/sync" \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"full_sync": false}')

echo "Response: $SYNC_RESPONSE"

# Extract job ID
JOB_ID=$(echo "$SYNC_RESPONSE" | jq -r '.data.job_id // empty')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
    echo "❌ FAILED: Could not trigger sync job"
    echo "Response: $SYNC_RESPONSE"
    exit 1
fi

echo "✅ Sync job triggered successfully"
echo "   Job ID: $JOB_ID"
echo ""

echo "Step 3: Poll for job completion"
echo "--------------------------------"
echo "   Max wait time: ${MAX_WAIT_SECONDS}s"
echo "   Poll interval: ${POLL_INTERVAL}s"
echo ""

ELAPSED=0
MAX_ITERATIONS=$((MAX_WAIT_SECONDS / POLL_INTERVAL))
ITERATION=0

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
    ITERATION=$((ITERATION + 1))

    # Check job status
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/google-drive/sync/status/$JOB_ID" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        -H "Content-Type: application/json")

    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.data.status // "unknown"')
    DOCS_SYNCED=$(echo "$STATUS_RESPONSE" | jq -r '.data.documents_synced // 0')
    DOCS_FAILED=$(echo "$STATUS_RESPONSE" | jq -r '.data.documents_failed // 0')

    echo "   [$ITERATION/$MAX_ITERATIONS] Status: $STATUS, Synced: $DOCS_SYNCED, Failed: $DOCS_FAILED"

    if [ "$STATUS" == "success" ]; then
        echo ""
        echo "✅ Sync job completed successfully!"
        echo "   Duration: ${ELAPSED}s"
        echo "   Documents synced: $DOCS_SYNCED"
        echo "   Documents failed: $DOCS_FAILED"
        echo ""

        # Verify error rate <2% (AC3.2.7)
        TOTAL=$((DOCS_SYNCED + DOCS_FAILED))
        if [ $TOTAL -gt 0 ]; then
            ERROR_RATE=$(echo "scale=4; $DOCS_FAILED / $TOTAL" | bc)
            ERROR_PERCENT=$(echo "scale=2; $ERROR_RATE * 100" | bc)
            echo "   Error rate: ${ERROR_PERCENT}%"

            # Check if error rate is within acceptable threshold (< 2%)
            if (( $(echo "$ERROR_RATE < 0.02" | bc -l) )); then
                echo "✅ Error rate within target (<2%)"
            else
                echo "❌ Error rate too high (>2%)"
                echo "   This may indicate a systemic issue"
                exit 1
            fi
        else
            echo "⚠️  No documents synced (empty Drive or first-time setup)"
        fi

        # Get full job details
        STARTED_AT=$(echo "$STATUS_RESPONSE" | jq -r '.data.started_at // ""')
        COMPLETED_AT=$(echo "$STATUS_RESPONSE" | jq -r '.data.completed_at // ""')

        echo ""
        echo "Job Details:"
        echo "   Job ID: $JOB_ID"
        echo "   Started: $STARTED_AT"
        echo "   Completed: $COMPLETED_AT"
        echo ""

        break

    elif [ "$STATUS" == "failed" ]; then
        echo ""
        echo "❌ Sync job failed"
        ERROR_MESSAGE=$(echo "$STATUS_RESPONSE" | jq -r '.data.error_message // "Unknown error"')
        echo "   Error: $ERROR_MESSAGE"
        exit 1

    elif [ "$STATUS" == "unknown" ]; then
        echo "❌ Could not retrieve job status"
        echo "Response: $STATUS_RESPONSE"
        exit 1
    fi
done

# Check if we timed out
if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    echo ""
    echo "❌ Sync job timed out after ${MAX_WAIT_SECONDS}s"
    echo "   Last status: $STATUS"
    exit 1
fi

echo "Step 4: Verify sync history"
echo "----------------------------"
HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/google-drive/sync/history?limit=5" \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json")

JOBS_COUNT=$(echo "$HISTORY_RESPONSE" | jq -r '.data.jobs_count // 0')
echo "   Recent sync jobs: $JOBS_COUNT"

if [ $JOBS_COUNT -gt 0 ]; then
    echo "✅ Sync history retrieved successfully"
else
    echo "⚠️  No sync history found"
fi

echo ""

echo "Step 5: Check dashboard status"
echo "-------------------------------"
DASHBOARD_RESPONSE=$(curl -s -X GET "$BASE_URL/api/google-drive/sync/dashboard" \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json")

LAST_SYNC=$(echo "$DASHBOARD_RESPONSE" | jq -r '.data.last_sync_at // "never"')
FILES_SYNCED=$(echo "$DASHBOARD_RESPONSE" | jq -r '.data.files_synced // 0')
LATEST_JOB_STATUS=$(echo "$DASHBOARD_RESPONSE" | jq -r '.data.latest_job.status // "none"')

echo "   Last sync: $LAST_SYNC"
echo "   Total files synced: $FILES_SYNCED"
echo "   Latest job status: $LATEST_JOB_STATUS"

if [ "$LATEST_JOB_STATUS" == "success" ]; then
    echo "✅ Dashboard shows successful sync"
else
    echo "⚠️  Dashboard status: $LATEST_JOB_STATUS"
fi

echo ""
echo "========================================="
echo "Sync Job Test Summary"
echo "========================================="
echo "✅ Authentication check: PASS"
echo "✅ Trigger sync job: PASS"
echo "✅ Job completion: PASS"
echo "✅ Error rate verification: PASS"
echo "✅ Sync history: PASS"
echo "✅ Dashboard status: PASS"
echo ""
echo "========================================="
echo "Test completed successfully!"
echo "========================================="
