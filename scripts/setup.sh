#!/bin/bash

# =============================================================================
# ONYX Development Environment Setup Script
# =============================================================================
# This script automates the setup of the ONYX development environment
# Target setup time: < 30 minutes
# Supported platforms: macOS, Linux, Windows (WSL2)
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.local"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
LOG_FILE="$PROJECT_ROOT/setup.log"

# Minimum version requirements
MIN_DOCKER_VERSION="24.0.0"
MIN_NODE_VERSION="18.0.0"
MIN_PYTHON_VERSION="3.10.0"

# =============================================================================
# Utility Functions
# =============================================================================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

header() {
    echo -e "\n${BLUE}=== $1 ===${NC}" | tee -a "$LOG_FILE"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

version_compare() {
    local version1=$1
    local version2=$2
    local operator=$3
    
    if [[ "$operator" == ">=" ]]; then
        printf '%s\n%s\n' "$version2" "$version1" | sort -V -C
    elif [[ "$operator" == ">" ]]; then
        [[ "$version1" != "$version2" ]] && printf '%s\n%s\n' "$version2" "$version1" | sort -V -C
    fi
}

check_port() {
    local port=$1
    local service_name=$2
    
    if command_exists lsof; then
        if lsof -i ":$port" >/dev/null 2>&1; then
            warning "Port $port is already in use (required for $service_name)"
            local pid=$(lsof -ti ":$port")
            echo "   Process using port: $(ps -p "$pid" -o comm= 2>/dev/null || echo 'Unknown')"
            echo "   To free the port: kill -9 $pid"
            return 1
        fi
    elif command_exists netstat; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            warning "Port $port is already in use (required for $service_name)"
            return 1
        fi
    fi
    return 0
}

prompt_user() {
    local prompt=$1
    local default=${2:-}
    local response
    
    while true; do
        if [[ -n "$default" ]]; then
            read -p "$prompt [$default]: " response
            response=${response:-$default}
        else
            read -p "$prompt: " response
        fi
        
        if [[ -n "$response" ]]; then
            echo "$response"
            break
        else
            echo "Please provide a value."
        fi
    done
}

prompt_yes_no() {
    local prompt=$1
    local default=${2:-n}
    local response
    
    while true; do
        read -p "$prompt [y/N]: " response
        response=${response:-$default}
        
        case $response in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]|"") return 1 ;;
            *) echo "Please enter y or n." ;;
        esac
    done
}

# =============================================================================
# System Detection
# =============================================================================

detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

detect_architecture() {
    local arch=$(uname -m)
    case $arch in
        x86_64) echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        *) echo "$arch" ;;
    esac
}

# =============================================================================
# Prerequisite Checks
# =============================================================================

check_docker() {
    header "Checking Docker Installation"
    
    if ! command_exists docker; then
        error "Docker is not installed or not in PATH"
        echo "Please install Docker Desktop from https://docker.com/products/docker-desktop"
        return 1
    fi
    
    local docker_version=$(docker --version | sed 's/.*version //;s/,.*//g')
    log "Found Docker version: $docker_version"
    
    if ! version_compare "$docker_version" "$MIN_DOCKER_VERSION" ">="; then
        error "Docker version $docker_version is too old. Minimum required: $MIN_DOCKER_VERSION"
        return 1
    fi
    
    success "Docker version check passed"
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        echo "Please start Docker Desktop or Docker service"
        return 1
    fi
    
    success "Docker daemon is running"
    
    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose is not available"
        return 1
    fi
    
    local compose_version=$(docker compose version --short)
    success "Docker Compose version: $compose_version"
    
    return 0
}

check_node() {
    header "Checking Node.js Installation"
    
    if ! command_exists node; then
        error "Node.js is not installed or not in PATH"
        echo "Please install Node.js 18+ from https://nodejs.org/"
        return 1
    fi
    
    local node_version=$(node --version | sed 's/v//')
    log "Found Node.js version: $node_version"
    
    if ! version_compare "$node_version" "$MIN_NODE_VERSION" ">="; then
        error "Node.js version $node_version is too old. Minimum required: $MIN_NODE_VERSION"
        echo "Please upgrade Node.js from https://nodejs.org/"
        return 1
    fi
    
    success "Node.js version check passed"
    
    # Check npm
    if ! command_exists npm; then
        error "npm is not installed"
        return 1
    fi
    
    local npm_version=$(npm --version)
    success "npm version: $npm_version"
    
    return 0
}

check_python() {
    header "Checking Python Installation"
    
    local python_cmd=""
    
    # Try different Python commands
    for cmd in python3 python3.11 python3.10 python; do
        if command_exists $cmd; then
            local version=$($cmd --version 2>&1 | sed 's/Python //')
            if version_compare "$version" "$MIN_PYTHON_VERSION" ">="; then
                python_cmd=$cmd
                break
            fi
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        error "Python 3.10+ is not installed"
        echo "Please install Python 3.10+ from https://python.org/"
        return 1
    fi
    
    local python_version=$($python_cmd --version | sed 's/Python //')
    log "Found Python version: $python_version (command: $python_cmd)"
    success "Python version check passed"
    
    # Check pip
    if ! command_exists pip && ! $python_cmd -m pip --version >/dev/null 2>&1; then
        error "pip is not installed"
        return 1
    fi
    
    local pip_version=$(pip --version 2>/dev/null | head -n1 || $python_cmd -m pip --version | head -n1)
    success "pip: $pip_version"
    
    return 0
}

check_git() {
    header "Checking Git Installation"
    
    if ! command_exists git; then
        error "Git is not installed"
        return 1
    fi
    
    local git_version=$(git --version | sed 's/git version //')
    success "Git version: $git_version"
    
    # Check if git is configured
    if ! git config --global user.name >/dev/null 2>&1; then
        warning "Git user.name is not configured"
        echo "   Run: git config --global user.name 'Your Name'"
    fi
    
    if ! git config --global user.email >/dev/null 2>&1; then
        warning "Git user.email is not configured"
        echo "   Run: git config --global user.email 'your.email@example.com'"
    fi
    
    return 0
}

check_ports() {
    header "Checking Port Availability"
    
    local ports_conflicts=0
    
    # Define critical ports and their services
    local ports=(
        "3000:Frontend (Suna)"
        "8080:Backend (Onyx Core)"
        "5432:PostgreSQL Database"
        "6379:Redis Cache"
        "6333:Qdrant Vector Database"
        "80:Nginx Reverse Proxy"
        "4000:LiteLLM Proxy"
        "11434:Ollama LLM Service"
        "9090:Prometheus Metrics"
        "3001:Grafana Dashboard"
    )
    
    for port_info in "${ports[@]}"; do
        IFS=':' read -r port service_name <<< "$port_info"
        if ! check_port "$port" "$service_name"; then
            ((ports_conflicts++))
        fi
    done
    
    if [[ $ports_conflicts -gt 0 ]]; then
        warning "Found $ports_conflicts port conflicts"
        echo "   You can either:"
        echo "   1. Stop the conflicting services"
        echo "   2. Change ONYX ports in .env.local"
        echo "   3. Continue and resolve conflicts later"
        
        if ! prompt_yes_no "Continue despite port conflicts?"; then
            return 1
        fi
    else
        success "All required ports are available"
    fi
    
    return 0
}

# =============================================================================
# Environment Setup
# =============================================================================

setup_environment() {
    header "Setting Up Environment"
    
    if [[ -f "$ENV_FILE" ]]; then
        log "Environment file already exists: $ENV_FILE"
        if prompt_yes_no "Overwrite existing environment file?"; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            log "Environment file reset from template"
        fi
    else
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        success "Environment file created from template"
    fi
    
    # Check for required environment variables
    local missing_vars=()
    local configured_vars=()
    
    # Read environment file and check for placeholder values
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Extract variable name and value
        if [[ $line =~ ^([A-Z_]+)=(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            
            # Check for placeholder values
            if [[ $var_value =~ (your-|generate-|optional-|placeholder) ]]; then
                case $var_name in
                    GOOGLE_CLIENT_ID|GOOGLE_CLIENT_SECRET)
                        missing_vars+=("$var_name (Google OAuth2)")
                        ;;
                    TOGETHER_API_KEY|DEEPSEEK_API_KEY)
                        missing_vars+=("$var_name (LLM API)")
                        ;;
                    POSTGRES_PASSWORD|ENCRYPTION_KEY)
                        missing_vars+=("$var_name (Security)")
                        ;;
                esac
            else
                configured_vars+=("$var_name")
            fi
        fi
    done < "$ENV_FILE"
    
    # Report configuration status
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        warning "Environment file needs configuration:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        
        echo
        echo "Please edit $ENV_FILE and configure the required variables"
        echo "Refer to DEVELOPMENT.md for detailed instructions"
        
        if ! prompt_yes_no "Continue with incomplete environment?"; then
            return 1
        fi
    else
        success "Environment file is properly configured"
    fi
    
    return 0
}

# =============================================================================
# Dependency Installation
# =============================================================================

install_dependencies() {
    header "Installing Dependencies"
    
    # Frontend dependencies
    log "Installing frontend dependencies..."
    if [[ -d "$PROJECT_ROOT/suna" ]]; then
        cd "$PROJECT_ROOT/suna"
        if npm install; then
            success "Frontend dependencies installed"
        else
            error "Failed to install frontend dependencies"
            return 1
        fi
        cd "$PROJECT_ROOT"
    else
        warning "Frontend directory not found: $PROJECT_ROOT/suna"
    fi
    
    # Backend dependencies
    log "Installing backend dependencies..."
    if [[ -d "$PROJECT_ROOT/onyx-core" ]]; then
        cd "$PROJECT_ROOT/onyx-core"
        
        # Create virtual environment if it doesn't exist
        if [[ ! -d "venv" ]]; then
            log "Creating Python virtual environment..."
            if python3 -m venv venv; then
                success "Virtual environment created"
            else
                error "Failed to create virtual environment"
                return 1
            fi
        fi
        
        # Activate virtual environment and install dependencies
        log "Activating virtual environment and installing dependencies..."
        if source venv/bin/activate && pip install -r requirements.txt; then
            success "Backend dependencies installed"
        else
            error "Failed to install backend dependencies"
            return 1
        fi
        cd "$PROJECT_ROOT"
    else
        warning "Backend directory not found: $PROJECT_ROOT/onyx-core"
    fi
    
    return 0
}

# =============================================================================
# Docker Services Setup
# =============================================================================

setup_docker_services() {
    header "Setting Up Docker Services"
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    log "Pulling Docker images..."
    if docker compose pull; then
        success "Docker images pulled successfully"
    else
        warning "Some Docker images failed to pull (this may be normal for local images)"
    fi
    
    # Build custom images
    log "Building custom Docker images..."
    if docker compose build; then
        success "Docker images built successfully"
    else
        error "Failed to build Docker images"
        return 1
    fi
    
    # Start services
    log "Starting Docker services..."
    if docker compose up -d; then
        success "Docker services started"
    else
        error "Failed to start Docker services"
        return 1
    fi
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Check service status
    log "Checking service status..."
    if docker compose ps; then
        success "Services status checked"
    else
        warning "Some services may not be running properly"
    fi
    
    return 0
}

# =============================================================================
# Health Checks
# =============================================================================

run_health_checks() {
    header "Running Health Checks"
    
    local failed_checks=0
    
    # Wait a bit more for services to fully start
    log "Waiting for services to fully initialize..."
    sleep 20
    
    # Frontend health check
    log "Checking frontend health..."
    if curl -s http://localhost:3000/api/health >/dev/null 2>&1; then
        success "Frontend health check passed"
    else
        error "Frontend health check failed"
        ((failed_checks++))
    fi
    
    # Backend health check
    log "Checking backend health..."
    if curl -s http://localhost:8080/health >/dev/null 2>&1; then
        success "Backend health check passed"
    else
        error "Backend health check failed"
        ((failed_checks++))
    fi
    
    # Database connectivity
    log "Checking database connectivity..."
    if docker compose exec -T postgres pg_isready >/dev/null 2>&1; then
        success "Database connectivity check passed"
    else
        error "Database connectivity check failed"
        ((failed_checks++))
    fi
    
    # Redis connectivity
    log "Checking Redis connectivity..."
    if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        success "Redis connectivity check passed"
    else
        error "Redis connectivity check failed"
        ((failed_checks++))
    fi
    
    # Qdrant connectivity
    log "Checking Qdrant connectivity..."
    if curl -s http://localhost:6333/health >/dev/null 2>&1; then
        success "Qdrant connectivity check passed"
    else
        error "Qdrant connectivity check failed"
        ((failed_checks++))
    fi
    
    if [[ $failed_checks -gt 0 ]]; then
        warning "$failed_checks health checks failed"
        echo "   Check the service logs for more information:"
        echo "   docker compose logs [service-name]"
        return 1
    else
        success "All health checks passed"
    fi
    
    return 0
}

# =============================================================================
# Final Verification
# =============================================================================

final_verification() {
    header "Final Verification"
    
    echo
    echo "🎉 ONYX Development Environment Setup Complete!"
    echo
    echo "Service URLs:"
    echo "  • Frontend (Suna):     http://localhost:3000"
    echo "  • Backend API:         http://localhost:8080"
    echo "  • API Documentation:   http://localhost:8080/docs"
    echo "  • Grafana Dashboard:   http://localhost:3001"
    echo "  • Prometheus Metrics:  http://localhost:9090"
    echo
    echo "Development Commands:"
    echo "  • Frontend dev:        cd suna && npm run dev"
    echo "  • Backend dev:         cd onyx-core && source venv/bin/activate && python main.py"
    echo "  • Run tests:           npm test && pytest"
    echo "  • View logs:           docker compose logs -f"
    echo "  • Stop services:       docker compose down"
    echo
    echo "Next Steps:"
    echo "  1. Open http://localhost:3000 in your browser"
    echo "  2. Review the DEVELOPMENT.md for detailed instructions"
    echo "  3. Check the API documentation at http://localhost:8080/docs"
    echo "  4. Start developing!"
    echo
    echo "Setup log saved to: $LOG_FILE"
    
    return 0
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log "Starting ONYX development environment setup"
    log "Platform: $(detect_platform) $(detect_architecture)"
    log "Project root: $PROJECT_ROOT"
    
    # Create log file
    touch "$LOG_FILE"
    
    # Run setup steps
    local steps=(
        "check_docker"
        "check_node" 
        "check_python"
        "check_git"
        "check_ports"
        "setup_environment"
        "install_dependencies"
        "setup_docker_services"
        "run_health_checks"
        "final_verification"
    )
    
    for step in "${steps[@]}"; do
        if ! $step; then
            error "Setup failed at step: $step"
            echo
            echo "Check the log file for details: $LOG_FILE"
            echo "Refer to DEVELOPMENT.md for troubleshooting instructions"
            exit 1
        fi
    done
    
    success "Setup completed successfully!"
}

# Handle script interruption
trap 'error "Setup interrupted by user"; exit 130' INT

# Run main function
main "$@"