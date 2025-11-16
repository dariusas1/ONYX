# noVNC Security Configuration
# Security settings for VNC service

# Authentication Settings
VNC_SESSION_TIMEOUT=3600      # Session timeout in seconds (1 hour)
VNC_MAX_SESSIONS=10           # Maximum concurrent VNC sessions
VNC_AUTH_REQUIRED=true       # Require authentication
VNC_SESSION_ENCRYPTION=true  # Enable session encryption

# Access Control Settings
VNC_ALLOWED_IPS=""           # Comma-separated list of allowed IPs (empty = allow all)
VNC_BLOCKED_IPS="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"  # Blocked private ranges (uncomment to block)
VNC_RATE_LIMIT_REQUESTS=5    # Rate limit requests per second
VNC_RATE_LIMIT_BURST=10      # Rate limit burst size

# Connection Limits
VNC_MAX_CONNECTIONS_PER_IP=3 # Maximum connections per IP address
VNC_IDLE_TIMEOUT=1800        # Idle connection timeout in seconds (30 minutes)
VNC_CONNECTION_TIMEOUT=30    # Initial connection timeout in seconds

# Resource Protection
VNC_MEMORY_LIMIT=2147483648  # Memory limit in bytes (2GB)
VNC_CPU_LIMIT=2             # CPU limit in cores
VNC_MAX_BANDWIDTH_KBPS=10000 # Maximum bandwidth in KB/s

# Security Headers
VNC_SECURITY_HEADERS=true    # Enable security headers
VNC_CORS_ORIGIN="*"          # CORS allowed origin (customize for production)
VNC_FRAME_OPTIONS="DENY"     # X-Frame-Options header

# Session Management
VNC_SESSION_PERSISTENCE=true # Enable session persistence
VNC_SESSION_CLEANUP_ON_EXIT=false # Clean up session data on exit
VNC_SESSION_BACKUP_INTERVAL=300    # Session backup interval in seconds

# Monitoring and Logging
VNC_ACCESS_LOG=true          # Enable access logging
VNC_ERROR_LOG=true           # Enable error logging
VNC_SECURITY_LOG=true        # Enable security event logging
VNC_METRICS_ENABLED=true     # Enable Prometheus metrics

# SSL/TLS Configuration (handled by Nginx reverse proxy)
VNC_SSL_ONLY=true           # Enforce SSL/TLS connections
VNC_SSL_VERIFY_PEER=false   # Verify peer SSL certificates

# WebSocket Security
VNC_WEBSOCKET_ORIGIN_CHECK=true   # Check WebSocket Origin header
VNC_WEBSOCKET_RATE_LIMIT=10       # WebSocket rate limit per second
VNC_WEBSOCKET_MAX_FRAME_SIZE=1048576  # Max WebSocket frame size (1MB)

# Advanced Security
VNC_FAIL2BAN_ENABLED=false    # Enable fail2ban integration
VNC_FAIL2BAN_THRESHOLD=5     # Failed attempts before ban
VNC_FAIL2BAN_TIME=3600       # Ban duration in seconds

# Development/Debug Settings (set to false in production)
VNC_DEBUG_MODE=false         # Enable debug logging
VNC_ALLOW_INSECURE=false     # Allow insecure connections
VNC_SKIP_AUTH_FOR_LOCALHOST=false # Skip authentication for localhost

# Health Check Security
VNC_HEALTH_CHECK_TOKEN=""    # Optional token for health check access
VNC_HEALTH_CHECK_IP_WHITELIST="127.0.0.1,::1"  # IPs allowed to access health checks

# Environment-specific overrides
# Set VNC_ENV=production for production hardening
if [[ "${VNC_ENV}" == "production" ]]; then
    VNC_DEBUG_MODE=false
    VNC_ALLOW_INSECURE=false
    VNC_SKIP_AUTH_FOR_LOCALHOST=false
    VNC_SECURITY_HEADERS=true
    VNC_RATE_LIMIT_REQUESTS=3
    VNC_RATE_LIMIT_BURST=5
fi