#!/bin/bash

# noVNC Service Configuration Test Script
# Validates Docker Compose configuration and service setup

set -e

echo "🔍 noVNC Service Configuration Test"
echo "=================================="

# Test 1: Validate Docker Compose configuration
echo "📋 Test 1: Validating Docker Compose configuration..."
if docker-compose config >/dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    docker-compose config
    exit 1
fi

# Test 2: Check required directories exist
echo -e "\n📁 Test 2: Checking required directories..."
required_dirs=("novnc" "logs/novnc")
for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ Directory exists: $dir"
    else
        echo "❌ Missing directory: $dir"
        exit 1
    fi
done

# Test 3: Check required files exist
echo -e "\n📄 Test 3: Checking required files..."
required_files=(
    "novnc/startup.sh"
    "docker-compose.yaml"
    ".env.example"
    "prometheus/prometheus.yml"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ File exists: $file"
    else
        echo "❌ Missing file: $file"
        exit 1
    fi
done

# Test 4: Validate startup script syntax
echo -e "\n🔧 Test 4: Validating startup script syntax..."
if bash -n novnc/startup.sh; then
    echo "✅ Startup script syntax is valid"
else
    echo "❌ Startup script has syntax errors"
    exit 1
fi

# Test 5: Check startup script permissions
echo -e "\n🔐 Test 5: Checking file permissions..."
if [[ -x "novnc/startup.sh" ]]; then
    echo "✅ Startup script is executable"
else
    echo "❌ Startup script is not executable"
    exit 1
fi

# Test 6: Extract noVNC service configuration from docker-compose.yaml
echo -e "\n⚙️  Test 6: Analyzing noVNC service configuration..."
if command -v yq >/dev/null 2>&1; then
    # Use yq if available for proper YAML parsing
    novnc_image=$(yq eval '.services.novnc.image' docker-compose.yaml)
    novnc_ports=$(yq eval '.services.novnc.ports' docker-compose.yaml)
    novnc_network=$(yq eval '.services.novnc.networks' docker-compose.yaml)
else
    # Fallback to grep/yaml parsing
    novnc_image=$(grep -A 1 "novnc:" docker-compose.yaml | grep "image:" | awk '{print $2}')
fi

if [[ -n "$novnc_image" ]]; then
    echo "✅ noVNC image configured: $novnc_image"
else
    echo "❌ noVNC image not found in configuration"
    exit 1
fi

# Test 7: Check environment variables in .env.example
echo -e "\n🌍 Test 7: Checking environment variables..."
env_vars=("VNC_PASSWORD" "VNC_RESOLUTION" "VNC_REFRESH_RATE" "VNC_COMPRESS_LEVEL" "VNC_QUALITY")
for var in "${env_vars[@]}"; do
    if grep -q "^$var=" .env.example; then
        echo "✅ Environment variable defined: $var"
    else
        echo "❌ Missing environment variable: $var"
        exit 1
    fi
done

# Test 8: Check Prometheus configuration
echo -e "\n📊 Test 8: Checking Prometheus configuration..."
if grep -q "novnc:" prometheus/prometheus.yml; then
    echo "✅ noVNC service configured in Prometheus"
else
    echo "❌ noVNC service not configured in Prometheus"
    exit 1
fi

# Test 9: Validate port configurations
echo -e "\n🔌 Test 9: Validating port configurations..."
expected_ports=("6080" "5900" "9091")
for port in "${expected_ports[@]}"; do
    if grep -q "\"$port:" docker-compose.yaml; then
        echo "✅ Port $port is configured"
    else
        echo "❌ Port $port is not configured"
        exit 1
    fi
done

# Test 10: Check network integration
echo -e "\n🌐 Test 10: Checking network integration..."
if grep -q "manus-network" docker-compose.yaml; then
    echo "✅ Service integrated with manus-network"
else
    echo "❌ Service not integrated with manus-network"
    exit 1
fi

echo -e "\n🎉 All configuration tests passed!"
echo "=================================="
echo "✅ noVNC service is ready for deployment"
echo -e "\n📋 Next Steps:"
echo "1. Set VNC_PASSWORD in your .env.local file"
echo "2. Run: docker-compose up -d novnc"
echo "3. Access noVNC at: http://localhost:6080"
echo "4. Check metrics at: http://localhost:9091/metrics"
echo "5. Monitor service in Grafana dashboard"
echo -e "\n🔒 Security Reminder:"
echo "Set a strong VNC_PASSWORD before running in production!"
echo "=================================="