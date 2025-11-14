#!/bin/bash

# =============================================================================
# ONYX Log Viewing Script
# =============================================================================
# Script for viewing and searching aggregated logs from all services
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"

# Service list
SERVICES=("suna" "onyx-core" "nginx")
DEFAULT_SERVICE="all"
DEFAULT_LINES=50
DEFAULT_FOLLOW=false

# Help function
show_help() {
    cat << EOF
${CYAN}ONYX Log Viewing Script${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS] [SERVICE]

${YELLOW}SERVICES:${NC}
    all         - View logs from all services (default)
    suna        - View Suna (Next.js) logs
    onyx-core   - View Onyx Core (Python) logs
    nginx       - View Nginx logs

${YELLOW}OPTIONS:${NC}
    -f, --follow        Follow log output (like tail -f)
    -n, --lines NUM     Show last NUM lines (default: 50)
    -l, --level LEVEL   Filter by log level (debug, info, warn, error)
    -s, --service SERVICE Filter by service name
    -r, --request-id ID Filter by request ID
    -t, --timestamp     Show human-readable timestamps
    -j, --json          Show raw JSON output (default: formatted)
    -h, --help          Show this help message

${YELLOW}EXAMPLES:${NC}
    # View last 100 lines from all services
    $0 -n 100

    # Follow logs from onyx-core service
    $0 -f onyx-core

    # View error logs from nginx
    $0 -l error nginx

    # Filter by request ID
    $0 -r req_1234567890_abcdef123

    # View logs with human-readable timestamps
    $0 -t

${YELLOW}DOCKER COMPOSE ALTERNATIVES:${NC}
    # View all service logs with Docker Compose
    docker-compose logs -f

    # View specific service logs
    docker-compose logs -f suna
    docker-compose logs -f onyx-core
    docker-compose logs -f nginx

EOF
}

# Parse command line arguments
parse_args() {
    FOLLOW=false
    LINES=$DEFAULT_LINES
    LOG_LEVEL=""
    SERVICE_FILTER=""
    REQUEST_ID=""
    TIMESTAMP=false
    JSON_OUTPUT=false
    SERVICE=$DEFAULT_SERVICE

    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--follow)
                FOLLOW=true
                shift
                ;;
            -n|--lines)
                LINES="$2"
                shift 2
                ;;
            -l|--level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            -s|--service)
                SERVICE_FILTER="$2"
                shift 2
                ;;
            -r|--request-id)
                REQUEST_ID="$2"
                shift 2
                ;;
            -t|--timestamp)
                TIMESTAMP=true
                shift
                ;;
            -j|--json)
                JSON_OUTPUT=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo -e "${RED}Error: Unknown option $1${NC}" >&2
                show_help
                exit 1
                ;;
            *)
                if [[ " ${SERVICES[@]} all " =~ " $1 " ]]; then
                    SERVICE="$1"
                else
                    echo -e "${RED}Error: Unknown service '$1'${NC}" >&2
                    echo -e "${RED}Valid services: all, ${SERVICES[*]}${NC}" >&2
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# Check if required tools are available
check_dependencies() {
    local missing_tools=()

    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi

    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required tools: ${missing_tools[*]}${NC}" >&2
        echo -e "${YELLOW}Install with: brew install ${missing_tools[*]}${NC}" >&2
        exit 1
    fi
}

# Get log files for a service
get_log_files() {
    local service="$1"
    local log_files=()

    case "$service" in
        "suna")
            log_files=("$LOGS_DIR/suna"/*.log)
            ;;
        "onyx-core")
            log_files=("$LOGS_DIR/onyx-core"/*.log)
            ;;
        "nginx")
            log_files=("$LOGS_DIR/nginx"/*.log)
            ;;
        "all")
            for svc in "${SERVICES[@]}"; do
                log_files+=($(get_log_files "$svc"))
            done
            ;;
    esac

    # Filter existing files
    for file in "${log_files[@]}"; do
        if [[ -f "$file" ]]; then
            echo "$file"
        fi
    done
}

# Format JSON log entry
format_log_entry() {
    local entry="$1"

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "$entry"
        return
    fi

    # Parse JSON and format
    local timestamp=$(echo "$entry" | jq -r '.timestamp // empty')
    local level=$(echo "$entry" | jq -r '.level // empty')
    local service=$(echo "$entry" | jq -r '.service // empty')
    local action=$(echo "$entry" | jq -r '.action // empty')
    local message=$(echo "$entry" | jq -r '.message // empty')
    local request_id=$(echo "$entry" | jq -r '.request_id // empty')
    local error=$(echo "$entry" | jq -r '.error // empty')
    local duration=$(echo "$entry" | jq -r '.duration_ms // empty')

    # Apply color coding for log levels
    local level_color=""
    case "$level" in
        "error") level_color="$RED" ;;
        "warn")  level_color="$YELLOW" ;;
        "info")  level_color="$GREEN" ;;
        "debug") level_color="$BLUE" ;;
    esac

    # Format timestamp
    local formatted_timestamp=""
    if [[ "$TIMESTAMP" == "true" && -n "$timestamp" ]]; then
        formatted_timestamp=$(date -d "$timestamp" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$timestamp")
    fi

    # Build output
    local output=""

    # Timestamp
    if [[ -n "$formatted_timestamp" ]]; then
        output+="${CYAN}[$formatted_timestamp]${NC} "
    fi

    # Level and Service
    output+="${level_color}${level^^}${NC} ${PURPLE}$service${NC}"

    # Request ID
    if [[ -n "$request_id" ]]; then
        output+=" ${BLUE}[$request_id]${NC}"
    fi

    # Action/Message
    if [[ -n "$action" ]]; then
        output+=": $action"
    elif [[ -n "$message" ]]; then
        output+=": $message"
    fi

    # Duration
    if [[ -n "$duration" ]]; then
        output+=" ${YELLOW}(${duration}ms)${NC}"
    fi

    # Error
    if [[ -n "$error" && "$error" != "null" ]]; then
        output+="\n${RED}Error: $error${NC}"
    fi

    echo "$output"
}

# Filter log entries
filter_logs() {
    local log_files=("$@")

    for log_file in "${log_files[@]}"; do
        if [[ ! -f "$log_file" ]]; then
            continue
        fi

        # Read and filter log entries
        while IFS= read -r line; do
            # Skip empty lines
            [[ -z "$line" ]] && continue

            # Apply filters
            if [[ -n "$LOG_LEVEL" ]]; then
                local entry_level=$(echo "$line" | jq -r '.level // empty' 2>/dev/null || echo "")
                [[ "$entry_level" != "$LOG_LEVEL" ]] && continue
            fi

            if [[ -n "$SERVICE_FILTER" ]]; then
                local entry_service=$(echo "$line" | jq -r '.service // empty' 2>/dev/null || echo "")
                [[ "$entry_service" != "$SERVICE_FILTER" ]] && continue
            fi

            if [[ -n "$REQUEST_ID" ]]; then
                local entry_request_id=$(echo "$line" | jq -r '.request_id // empty' 2>/dev/null || echo "")
                [[ "$entry_request_id" != "$REQUEST_ID" ]] && continue
            fi

            format_log_entry "$line"
        done < <(tail -n "$LINES" "$log_file" | tac)
    done
}

# Follow logs in real-time
follow_logs() {
    local log_files=("$@")

    echo -e "${CYAN}Following logs... (Press Ctrl+C to stop)${NC}"
    echo

    # Use tail -f to follow all log files
    tail -f "${log_files[@]}" | while read -r line; do
        [[ -z "$line" ]] && continue

        # Apply filters and format
        if should_show_line "$line"; then
            format_log_entry "$line"
        fi
    done
}

# Check if line should be shown
should_show_line() {
    local line="$1"

    # Apply level filter
    if [[ -n "$LOG_LEVEL" ]]; then
        local entry_level=$(echo "$line" | jq -r '.level // empty' 2>/dev/null || echo "")
        [[ "$entry_level" != "$LOG_LEVEL" ]] && return 1
    fi

    # Apply service filter
    if [[ -n "$SERVICE_FILTER" ]]; then
        local entry_service=$(echo "$line" | jq -r '.service // empty' 2>/dev/null || echo "")
        [[ "$entry_service" != "$SERVICE_FILTER" ]] && return 1
    fi

    # Apply request ID filter
    if [[ -n "$REQUEST_ID" ]]; then
        local entry_request_id=$(echo "$line" | jq -r '.request_id // empty' 2>/dev/null || echo "")
        [[ "$entry_request_id" != "$REQUEST_ID" ]] && return 1
    fi

    return 0
}

# Docker Compose logs fallback
show_docker_logs() {
    echo -e "${YELLOW}Falling back to Docker Compose logs...${NC}"

    local docker_args=()

    if [[ "$FOLLOW" == "true" ]]; then
        docker_args+=("-f")
    fi

    if [[ "$SERVICE" != "all" ]]; then
        docker_args+=("$SERVICE")
    fi

    docker-compose logs "${docker_args[@]}"
}

# Main function
main() {
    parse_args "$@"
    check_dependencies

    # Create logs directory if it doesn't exist
    mkdir -p "$LOGS_DIR"

    echo -e "${CYAN}ONYX Log Viewer${NC}"
    echo -e "${CYAN}=================${NC}"
    echo -e "Service: $SERVICE"
    echo -e "Lines: $LINES"
    echo -e "Follow: $FOLLOW"
    [[ -n "$LOG_LEVEL" ]] && echo -e "Level: $LOG_LEVEL"
    [[ -n "$REQUEST_ID" ]] && echo -e "Request ID: $REQUEST_ID"
    echo

    # Get log files
    local log_files
    readarray -t log_files < <(get_log_files "$SERVICE")

    # Check if we have any log files
    if [ ${#log_files[@]} -eq 0 ]; then
        echo -e "${YELLOW}No log files found. Using Docker Compose logs...${NC}"
        show_docker_logs
        return
    fi

    echo -e "${GREEN}Found ${#log_files[@]} log file(s)${NC}"
    echo

    # Show logs
    if [[ "$FOLLOW" == "true" ]]; then
        follow_logs "${log_files[@]}"
    else
        filter_logs "${log_files[@]}"
    fi
}

# Run main function with all arguments
main "$@"