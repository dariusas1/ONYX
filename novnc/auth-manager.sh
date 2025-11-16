#!/bin/bash

# noVNC Authentication Manager
# Handles authentication, session management, and access control

set -e

# Load security configuration
source /home/novncuser/security-config.sh

# Session storage directory
SESSION_DIR="/tmp/vnc-sessions"
SESSION_TIMEOUT=${VNC_SESSION_TIMEOUT:-3600}
MAX_SESSIONS=${VNC_MAX_SESSIONS:-10}

# Initialize session directory
init_session_storage() {
    mkdir -p "$SESSION_DIR"
    chmod 700 "$SESSION_DIR"
}

# Generate session ID
generate_session_id() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 16 2>/dev/null || date +%s%N | sha256sum | cut -d' ' -f1
    else
        date +%s%N | sha256sum | cut -d' ' -f1
    fi
}

# Create new session
create_session() {
    local client_ip="$1"
    local user_agent="$2"

    # Check session limit
    local current_sessions=$(find "$SESSION_DIR" -name "session_*.json" -mmin -$((SESSION_TIMEOUT/60)) 2>/dev/null | wc -l)
    if [[ $current_sessions -ge $MAX_SESSIONS ]]; then
        echo "ERROR: Maximum sessions ($MAX_SESSIONS) reached"
        return 1
    fi

    # Check IP-based session limit
    local ip_sessions=$(find "$SESSION_DIR" -name "session_*.json" -mmin -$((SESSION_TIMEOUT/60)) -exec grep -l "\"client_ip\":\"$client_ip\"" {} \; 2>/dev/null | wc -l)
    if [[ $ip_sessions -ge ${VNC_MAX_CONNECTIONS_PER_IP:-3} ]]; then
        echo "ERROR: Maximum sessions per IP reached for $client_ip"
        return 1
    fi

    local session_id=$(generate_session_id)
    local session_file="$SESSION_DIR/session_${session_id}.json"
    local created_at=$(date +%s)
    local expires_at=$((created_at + SESSION_TIMEOUT))

    # Create session data
    cat > "$session_file" << EOF
{
    "session_id": "$session_id",
    "client_ip": "$client_ip",
    "user_agent": "$user_agent",
    "created_at": $created_at,
    "expires_at": $expires_at,
    "last_activity": $created_at,
    "authenticated": true,
    "access_count": 0
}
EOF

    chmod 600 "$session_file"
    echo "$session_id"
}

# Validate session
validate_session() {
    local session_id="$1"
    local client_ip="$2"

    if [[ -z "$session_id" ]]; then
        return 1
    fi

    local session_file="$SESSION_DIR/session_${session_id}.json"

    if [[ ! -f "$session_file" ]]; then
        return 1
    fi

    # Check session expiration
    local current_time=$(date +%s)
    local expires_at=$(grep '"expires_at"' "$session_file" | cut -d':' -f2 | tr -d ' ,')

    if [[ $current_time -gt $expires_at ]]; then
        rm -f "$session_file"
        return 1
    fi

    # Validate client IP (optional security measure)
    local stored_ip=$(grep '"client_ip"' "$session_file" | cut -d'"' -f4)
    if [[ "$client_ip" != "$stored_ip" && "${VNC_SESSION_IP_BINDING:-true}" == "true" ]]; then
        return 1
    fi

    # Update last activity
    update_session_activity "$session_id"

    return 0
}

# Update session activity
update_session_activity() {
    local session_id="$1"
    local session_file="$SESSION_DIR/session_${session_id}.json"

    if [[ -f "$session_file" ]]; then
        local new_expires=$(($(date +%s) + SESSION_TIMEOUT))
        sed -i "s/\"last_activity\":[^,]*/\"last_activity\":$(date +%s)/" "$session_file"
        sed -i "s/\"expires_at\":[^,]*/\"expires_at\":$new_expires/" "$session_file"
        local access_count=$(grep '"access_count"' "$session_file" | cut -d':' -f2 | tr -d ' ,')
        sed -i "s/\"access_count\":[^,]*/\"access_count\":$((access_count + 1))/" "$session_file"
    fi
}

# Destroy session
destroy_session() {
    local session_id="$1"
    local session_file="$SESSION_DIR/session_${session_id}.json"

    if [[ -f "$session_file" ]]; then
        rm -f "$session_file"
        return 0
    fi

    return 1
}

# Cleanup expired sessions
cleanup_expired_sessions() {
    find "$SESSION_DIR" -name "session_*.json" -mmin +$((SESSION_TIMEOUT/60)) -delete 2>/dev/null || true
}

# Get session info
get_session_info() {
    local session_id="$1"
    local session_file="$SESSION_DIR/session_${session_id}.json"

    if [[ -f "$session_file" ]]; then
        cat "$session_file"
        return 0
    fi

    return 1
}

# Log security events
log_security_event() {
    local event_type="$1"
    local client_ip="$2"
    local details="$3"

    if [[ "${VNC_SECURITY_LOG:-true}" == "true" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] SECURITY_EVENT: $event_type | IP: $client_ip | $details" >> /var/log/onyx/novnc-security.log
    fi

    # Send to metrics if enabled
    if [[ "${VNC_METRICS_ENABLED:-true}" == "true" ]]; then
        echo "vnc_security_events_total{type=\"$event_type\"} 1" | curl -X POST http://localhost:${METRICS_PORT:-9091}/metrics -d @- 2>/dev/null || true
    fi
}

# Check IP access control
check_ip_access() {
    local client_ip="$1"

    # Check blocked IPs first
    if [[ -n "${VNC_BLOCKED_IPS}" ]]; then
        IFS=',' read -ra BLOCKED_RANGES <<< "$VNC_BLOCKED_IPS"
        for range in "${BLOCKED_RANGES[@]}"; do
            if [[ "$range" == *"/"* ]]; then
                # CIDR range check
                if ipcalc -c "$client_ip/$range" >/dev/null 2>&1; then
                    log_security_event "IP_BLOCKED" "$client_ip" "Blocked by CIDR range: $range"
                    return 1
                fi
            else
                # Exact IP match
                if [[ "$client_ip" == "$range" ]]; then
                    log_security_event "IP_BLOCKED" "$client_ip" "Blocked by exact match"
                    return 1
                fi
            fi
        done
    fi

    # Check allowed IPs (if specified)
    if [[ -n "${VNC_ALLOWED_IPS}" ]]; then
        IFS=',' read -ra ALLOWED_RANGES <<< "$VNC_ALLOWED_IPS"
        for range in "${ALLOWED_RANGES[@]}"; do
            if [[ "$range" == *"/"* ]]; then
                # CIDR range check
                if ipcalc -c "$client_ip/$range" >/dev/null 2>&1; then
                    return 0
                fi
            else
                # Exact IP match
                if [[ "$client_ip" == "$range" ]]; then
                    return 0
                fi
            fi
        done

        log_security_event "IP_NOT_ALLOWED" "$client_ip" "Not in allowed IP list"
        return 1
    fi

    return 0
}

# Rate limiting check
check_rate_limit() {
    local client_ip="$1"
    local rate_limit_file="/tmp/vnc-rate-limit-$(echo "$client_ip" | tr '.' '_')"
    local current_time=$(date +%s)
    local window_size=60  # 1-minute window
    local max_requests=${VNC_RATE_LIMIT_REQUESTS:-5}

    if [[ -f "$rate_limit_file" ]]; then
        # Clean old entries
        awk -v current="$current_time" -v window="$window_size" '$1 >= current - window' "$rate_limit_file" > "${rate_limit_file}.tmp"
        mv "${rate_limit_file}.tmp" "$rate_limit_file"

        # Count requests in window
        local request_count=$(wc -l < "$rate_limit_file")
        if [[ $request_count -ge $max_requests ]]; then
            log_security_event "RATE_LIMIT_EXCEEDED" "$client_ip" "Requests: $request_count, Limit: $max_requests"
            return 1
        fi
    else
        touch "$rate_limit_file"
    fi

    # Add current request
    echo "$current_time" >> "$rate_limit_file"
    return 0
}

# Main authentication function
authenticate_vnc_connection() {
    local client_ip="$1"
    local user_agent="$2"
    local session_id="$3"

    # Check IP access control
    if ! check_ip_access "$client_ip"; then
        echo "ERROR: IP access denied"
        return 1
    fi

    # Check rate limiting
    if ! check_rate_limit "$client_ip"; then
        echo "ERROR: Rate limit exceeded"
        return 1
    fi

    # Validate existing session or create new one
    if [[ -n "$session_id" ]]; then
        if validate_session "$session_id" "$client_ip"; then
            log_security_event "SESSION_VALIDATED" "$client_ip" "Session: $session_id"
            echo "Session validated: $session_id"
            return 0
        else
            log_security_event "SESSION_INVALID" "$client_ip" "Invalid session: $session_id"
            echo "ERROR: Invalid session"
            return 1
        fi
    else
        # Create new session
        if new_session_id=$(create_session "$client_ip" "$user_agent"); then
            log_security_event "SESSION_CREATED" "$client_ip" "New session: $new_session_id"
            echo "Session created: $new_session_id"
            return 0
        else
            echo "ERROR: Failed to create session"
            return 1
        fi
    fi
}

# Initialize
init_session_storage
cleanup_expired_sessions

# Export functions for use in other scripts
export -f create_session validate_session destroy_session update_session_activity
export -f get_session_info cleanup_expired_sessions log_security_event
export -f check_ip_access check_rate_limit authenticate_vnc_connection

echo "Authentication manager initialized"
echo "Session timeout: ${SESSION_TIMEOUT}s"
echo "Max sessions: ${MAX_SESSIONS}"
echo "Rate limit: ${VNC_RATE_LIMIT_REQUESTS} req/s"