#!/bin/bash

# noVNC Service Startup Script
# Sets up encrypted VNC password and starts the service

set -e

echo "Starting noVNC service setup..."

# Function to generate encrypted VNC password
generate_vnc_password() {
    if [[ -n "${VNC_PASSWORD}" ]]; then
        echo "Setting VNC password..."
        # Create password file using x11vnc format
        mkdir -p "$(dirname "$VNC_PASSWORD_FILE")"
        echo "${VNC_PASSWORD}" | x11vnc -storepasswd - "${VNC_PASSWORD_FILE}"
        chmod 600 "${VNC_PASSWORD_FILE}"
        echo "VNC password configured successfully"
    else
        echo "WARNING: No VNC_PASSWORD set, using no password"
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

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $VNC_PID $WEBSOCKET_PID $METRICS_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for services
wait

echo "noVNC service stopped"
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