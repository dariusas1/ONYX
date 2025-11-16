#!/bin/bash

# noVNC Service Startup Script
# Sets up encrypted VNC password and starts the service

set -e

echo "Starting noVNC service setup..."

# Function to validate password strength
validate_password_strength() {
    local password="$1"
    local min_length=12

    # Check minimum length
    if [[ ${#password} -lt $min_length ]]; then
        echo "ERROR: VNC password must be at least $min_length characters long"
        return 1
    fi

    # Check for complexity (at least one uppercase, lowercase, digit, and special character)
    if [[ ! "$password" =~ [A-Z] ]]; then
        echo "ERROR: VNC password must contain at least one uppercase letter"
        return 1
    fi

    if [[ ! "$password" =~ [a-z] ]]; then
        echo "ERROR: VNC password must contain at least one lowercase letter"
        return 1
    fi

    if [[ ! "$password" =~ [0-9] ]]; then
        echo "ERROR: VNC password must contain at least one digit"
        return 1
    fi

    if [[ ! "$password" =~ [^a-zA-Z0-9] ]]; then
        echo "ERROR: VNC password must contain at least one special character"
        return 1
    fi

    # Check for common weak passwords
    local weak_patterns=("password" "123456" "qwerty" "admin" "welcome" "onyx")
    for pattern in "${weak_patterns[@]}"; do
        if [[ "${password,,}" == *"$pattern"* ]]; then
            echo "ERROR: VNC password contains common weak pattern '$pattern'"
            return 1
        fi
    done

    return 0
}

# Function to generate encrypted VNC password with security requirements
generate_vnc_password() {
    # CRITICAL SECURITY: Require VNC_PASSWORD to be set
    if [[ "${VNC_PASSWORD_REQUIRED}" == "true" && -z "${VNC_PASSWORD}" ]]; then
        echo "ERROR: VNC_PASSWORD environment variable is required but not set"
        echo "ERROR: For security reasons, VNC_PASSWORD must be explicitly provided"
        echo "ERROR: Set a strong password (12+ chars with uppercase, lowercase, digits, special chars)"
        exit 1
    fi

    if [[ -n "${VNC_PASSWORD}" ]]; then
        echo "Validating VNC password strength..."

        # Validate password strength
        if ! validate_password_strength "${VNC_PASSWORD}"; then
            echo "ERROR: VNC password validation failed"
            echo "ERROR: Please set a stronger VNC_PASSWORD meeting all security requirements"
            exit 1
        fi

        echo "Setting VNC password..."
        # Create password file using x11vnc format
        mkdir -p "$(dirname "$VNC_PASSWORD_FILE")"
        echo "${VNC_PASSWORD}" | x11vnc -storepasswd - "${VNC_PASSWORD_FILE}"
        chmod 600 "${VNC_PASSWORD_FILE}"
        echo "VNC password configured successfully"
    else
        echo "WARNING: No VNC_PASSWORD set - this is not recommended for production"
    fi
}

# Function to create startup scripts
create_startup_scripts() {
    cat > /home/novncuser/start-vnc.sh << 'EOF'
#!/bin/bash
# Start VNC server with optimized settings

export DISPLAY=:${DISPLAY_NUM:-1}

# Set screen resolution and color depth
echo "Starting VNC server with resolution ${VNC_RESOLUTION:-1920x1080}..."

# Start Xvfb with performance optimizations
Xvfb :${DISPLAY_NUM:-1} \
    -screen 0 ${VNC_RESOLUTION:-1920x1080}x${DISPLAY_DEPTH:-24} \
    -dpi 96 \
    -nolisten tcp \
    -nolisten unix &

# Wait for X server to start
sleep 2

# Start window manager
if command -v openbox >/dev/null 2>&1; then
    openbox &
elif command -v fluxbox >/dev/null 2>&1; then
    fluxbox &
elif command -v xfce4-session >/dev/null 2>&1; then
    xfce4-session &
fi

# Start VNC server with performance settings
if [[ -f "${VNC_PASSWORD_FILE}" ]]; then
    echo "Starting VNC server with password protection"
    x11vnc \
        -display :${DISPLAY_NUM:-1} \
        -rfbport ${VNC_PORT:-5900} \
        -rfbauth "${VNC_PASSWORD_FILE}" \
        -forever \
        -shared \
        -repeat \
        -threads \
        -nocursorshape \
        -cursorarrow \
        -nodragging \
        -nowf \
        -nowcr \
        -nosel \
        -noclipboards \
        -compresslevel ${VNC_COMPRESS_LEVEL:-6} \
        -quality ${VNC_QUALITY:-8} \
        -pixfmt ${VNC_PIXFORMAT:-rgb888} &
else
    echo "Starting VNC server without password"
    x11vnc \
        -display :${DISPLAY_NUM:-1} \
        -rfbport ${VNC_PORT:-5900} \
        -forever \
        -shared \
        -repeat \
        -threads \
        -nocursorshape \
        -cursorarrow \
        -nodragging \
        -nowf \
        -nowcr \
        -nosel \
        -noclipboards \
        -compresslevel ${VNC_COMPRESS_LEVEL:-6} \
        -quality ${VNC_QUALITY:-8} \
        -pixfmt ${VNC_PIXFORMAT:-rgb888} &
fi

echo "VNC server started on port ${VNC_PORT:-5900}"
EOF

    chmod +x /home/novncuser/start-vnc.sh
}

# Function to create health check endpoint
create_health_check() {
    cat > /home/novncuser/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for noVNC service

# Check VNC server process
if ! pgrep -x "x11vnc" > /dev/null; then
    echo "ERROR: VNC server not running"
    exit 1
fi

# Check WebSocket proxy process
if ! pgrep -f "websockify" > /dev/null; then
    echo "ERROR: WebSocket proxy not running"
    exit 1
fi

# Check X server process
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "ERROR: X server not running"
    exit 1
fi

# Test WebSocket connectivity
curl -f --connect-timeout 3 --max-time 5 \
    http://localhost:${NO_VNC_PORT:-6080}/health > /dev/null 2>&1 || {
    echo "ERROR: Health check endpoint not responding"
    exit 1
}

echo "OK: All services healthy"
exit 0
EOF

    chmod +x /home/novncuser/health-check.sh
}

# Function to create metrics endpoint
create_metrics_endpoint() {
    cat > /home/novncuser/metrics-endpoint.py << 'EOF'
#!/usr/bin/env python3
"""
Prometheus metrics endpoint for noVNC service
"""
import http.server
import socketserver
import psutil
import subprocess
import json
import os
import time
from urllib.parse import urlparse, parse_qs

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_health_response()
        elif self.path == '/metrics':
            self.send_metrics_response()
        else:
            self.send_response(404)
            self.end_headers()

    def send_health_response(self):
        """Health check endpoint"""
        try:
            # Check critical processes
            vnc_running = self.check_process('x11vnc')
            x_running = self.check_process('Xvfb')

            if vnc_running and x_running:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(503)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Service Unavailable')
        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def send_metrics_response(self):
        """Prometheus metrics endpoint"""
        try:
            metrics = self.collect_metrics()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(metrics.encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def check_process(self, process_name):
        """Check if process is running"""
        try:
            result = subprocess.run(['pgrep', '-x', process_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def collect_metrics(self):
        """Collect system and service metrics"""
        metrics = []

        # Process metrics
        vnc_cpu = 0
        vnc_memory = 0
        x_cpu = 0
        x_memory = 0

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['name'] == 'x11vnc':
                    vnc_cpu = proc.info['cpu_percent']
                    vnc_memory = proc.info['memory_percent']
                elif proc.info['name'] == 'Xvfb':
                    x_cpu = proc.info['cpu_percent']
                    x_memory = proc.info['memory_percent']
            except:
                continue

        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        # Create Prometheus metrics
        metrics.append(f'# HELP novnc_vnc_cpu_usage VNC server CPU usage percentage')
        metrics.append(f'# TYPE novnc_vnc_cpu_usage gauge')
        metrics.append(f'novnc_vnc_cpu_usage {vnc_cpu}')

        metrics.append(f'# HELP novnc_vnc_memory_usage VNC server memory usage percentage')
        metrics.append(f'# TYPE novnc_vnc_memory_usage gauge')
        metrics.append(f'novnc_vnc_memory_usage {vnc_memory}')

        metrics.append(f'# HELP novnc_xserver_cpu_usage X server CPU usage percentage')
        metrics.append(f'# TYPE novnc_xserver_cpu_usage gauge')
        metrics.append(f'novnc_xserver_cpu_usage {x_cpu}')

        metrics.append(f'# HELP novnc_xserver_memory_usage X server memory usage percentage')
        metrics.append(f'# TYPE novnc_xserver_memory_usage gauge')
        metrics.append(f'novnc_xserver_memory_usage {x_memory}')

        metrics.append(f'# HELP novnc_system_cpu_usage System CPU usage percentage')
        metrics.append(f'# TYPE novnc_system_cpu_usage gauge')
        metrics.append(f'novnc_system_cpu_usage {cpu_percent}')

        metrics.append(f'# HELP novnc_system_memory_usage System memory usage percentage')
        metrics.append(f'# TYPE novnc_system_memory_usage gauge')
        metrics.append(f'novnc_system_memory_usage {memory.percent}')

        metrics.append(f'# HELP novnc_service_up Service status')
        metrics.append(f'# TYPE novnc_service_up gauge')
        metrics.append(f'novnc_service_up 1')

        return '\n'.join(metrics)

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

if __name__ == '__main__':
    import sys

    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--health-check':
            # Run health check and exit
            handler = MetricsHandler
            try:
                handler.check_process = staticmethod(lambda name: subprocess.run(['pgrep', '-x', name], capture_output=True).returncode == 0)

                vnc_running = handler.check_process('x11vnc')
                x_running = handler.check_process('Xvfb')

                if vnc_running and x_running:
                    print("OK")
                    sys.exit(0)
                else:
                    print("Service Unavailable")
                    sys.exit(1)
            except Exception as e:
                print(f"Health check failed: {e}")
                sys.exit(1)

    port = int(os.environ.get('METRICS_PORT', 9091))

    with socketserver.TCPServer(('', port), MetricsHandler) as httpd:
        print(f"Metrics server listening on port {port}")
        httpd.serve_forever()
EOF

    chmod +x /home/novncuser/metrics-endpoint.py
}

# Function to create main service script
create_main_service() {
    cat > /home/novncuser/start-service.sh << 'EOF'
#!/bin/bash
# Main service startup script

set -e

echo "Starting noVNC service..."

# Set environment variables
export DISPLAY_NUM=${DISPLAY_NUM:-1}
export DISPLAY=:${DISPLAY_NUM}
export HOME=/home/novncuser

# Create necessary directories
mkdir -p ~/.vnc ~/.config

# Start X server and VNC
/home/novncuser/start-vnc.sh &
VNC_PID=$!

# Start metrics endpoint
/home/novncuser/metrics-endpoint.py &
METRICS_PID=$!

# Wait for services to start
sleep 3

# Start noVNC web server
cd /usr/share/novnc
python3 -m websockify --web=/usr/share/novnc \
    --target=localhost:${VNC_PORT:-5900} \
    :${NO_VNC_PORT:-6080} &
WEBSOCKET_PID=$!

# Function to log detailed error information
log_error() {
    local error_code="$1"
    local error_message="$2"
    local component="$3"

    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $error_message" | tee -a /var/log/onyx/novnc-errors.log
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR_CODE: $error_code" | tee -a /var/log/onyx/novnc-errors.log
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] COMPONENT: $component" | tee -a /var/log/onyx/novnc-errors.log

    # Send to metrics endpoint if available
    if [[ -n "$METRICS_PORT" ]]; then
        echo "vnc_errors_total{component=\"$component\",code=\"$error_code\"} 1" | curl -X POST http://localhost:$METRICS_PORT/metrics -d @- 2>/dev/null || true
    fi
}

# Function to cleanup on exit with enhanced logging
cleanup() {
    local exit_code=$1

    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: Starting graceful shutdown of noVNC services..."

    # Log which processes are being terminated
    if [[ -n "$VNC_PID" ]] && kill -0 $VNC_PID 2>/dev/null; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: Terminating VNC server (PID: $VNC_PID)"
        kill -TERM $VNC_PID 2>/dev/null || log_error "VNC_SHUTDOWN_FAIL" "Failed to terminate VNC server" "vnc-server"
        sleep 3
        kill -KILL $VNC_PID 2>/dev/null || true
    fi

    if [[ -n "$WEBSOCKET_PID" ]] && kill -0 $WEBSOCKET_PID 2>/dev/null; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: Terminating WebSocket server (PID: $WEBSOCKET_PID)"
        kill -TERM $WEBSOCKET_PID 2>/dev/null || log_error "WEBSOCKET_SHUTDOWN_FAIL" "Failed to terminate WebSocket server" "websocket-server"
        sleep 2
        kill -KILL $WEBSOCKET_PID 2>/dev/null || true
    fi

    if [[ -n "$METRICS_PID" ]] && kill -0 $METRICS_PID 2>/dev/null; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: Terminating metrics endpoint (PID: $METRICS_PID)"
        kill -TERM $METRICS_PID 2>/dev/null || log_error "METRICS_SHUTDOWN_FAIL" "Failed to terminate metrics endpoint" "metrics-endpoint"
        sleep 1
        kill -KILL $METRICS_PID 2>/dev/null || true
    fi

    # Cleanup session data if requested
    if [[ "${CLEANUP_SESSION_ON_SHUTDOWN}" == "true" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: Cleaning up session data"
        rm -rf /tmp/vnc-session/* 2>/dev/null || true
    fi

    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: noVNC services shutdown complete"
    exit ${exit_code:-0}
}

# Function to handle service health monitoring
monitor_service_health() {
    while true; do
        # Check VNC server health
        if [[ -n "$VNC_PID" ]]; then
            if ! kill -0 $VNC_PID 2>/dev/null; then
                log_error "VNC_PROCESS_DIED" "VNC server process died unexpectedly" "vnc-server"
                cleanup 1
            fi
        fi

        # Check WebSocket server health
        if [[ -n "$WEBSOCKET_PID" ]]; then
            if ! kill -0 $WEBSOCKET_PID 2>/dev/null; then
                log_error "WEBSOCKET_PROCESS_DIED" "WebSocket server process died unexpectedly" "websocket-server"
                cleanup 1
            fi
        fi

        # Check memory usage
        local memory_usage=$(ps -o rss= -p $VNC_PID 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
        if [[ $memory_usage -gt $((1024 * 1024 * 2)) ]]; then  # 2GB limit
            log_error "HIGH_MEMORY_USAGE" "VNC server memory usage too high: ${memory_usage}KB" "vnc-server"
        fi

        sleep 30
    done
}

# Set up enhanced signal handlers
trap 'cleanup 0' SIGTERM
trap 'cleanup 130' SIGINT
trap 'log_error "UNKNOWN_SIGNAL" "Received unexpected signal" "system"; cleanup 1' SIGUSR1 SIGUSR2

# Start health monitoring in background
monitor_service_health &
MONITOR_PID=$!

echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: noVNC services started successfully"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: VNC PID: $VNC_PID, WebSocket PID: $WEBSOCKET_PID, Metrics PID: $METRICS_PID, Monitor PID: $MONITOR_PID"

# Wait for services with error handling
wait $VNC_PID
vnc_exit_code=$?

echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: VNC server exited with code: $vnc_exit_code"

# Kill remaining processes
cleanup $vnc_exit_code

echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: noVNC service stopped"
EOF

    chmod +x /home/novncuser/start-service.sh
}

# Main execution
echo "Initializing noVNC configuration..."

# Generate VNC password if provided
generate_vnc_password

# Create startup scripts
create_startup_scripts
create_health_check
create_metrics_endpoint
create_main_service

echo "noVNC setup complete. Starting service..."

# Execute main service
exec /home/novncuser/start-service.sh