# ONYX Development Environment Setup Guide

**Target Setup Time:** < 30 minutes  
**Supported Platforms:** macOS, Linux, Windows (with WSL2)  
**Last Updated:** 2025-11-12

---

## System Requirements

### Minimum System Specifications
- **RAM:** 8GB (16GB recommended for full LLM services)
- **Storage:** 20GB free disk space for Docker volumes
- **Network:** Stable internet connection for initial downloads

### Required Software

#### Docker (Required)
- **macOS:** Docker Desktop 4.25+ (Apple Silicon or Intel)
- **Linux:** Docker Engine 24.0+ + Docker Compose v2.0+
- **Windows:** Docker Desktop 4.25+ with WSL2 backend

#### Node.js (Required for Frontend Development)
- **Version:** 18.0.0 or higher
- **Package Manager:** npm 8.0.0+ or yarn 1.22.0+
- **Installation:** [Node.js Official Downloads](https://nodejs.org/)

#### Python (Required for Backend Development)
- **Version:** 3.10.0 or higher (3.11+ recommended)
- **Package Manager:** pip 23.0+
- **Installation:** [Python Official Downloads](https://python.org/)

#### Git (Required)
- **Version:** 2.30.0 or higher
- **Configuration:** User email and name configured

#### Optional Tools
- **PostgreSQL Client:** For manual database queries (psql, DBeaver, or pgAdmin)
- **Redis CLI:** For cache inspection (`redis-tools` package)
- **Docker Desktop:** Includes helpful GUI for container management

---

## Platform-Specific Setup

### macOS Setup

#### 1. Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Required Tools
```bash
# Install Docker Desktop
brew install --cask docker

# Install Node.js
brew install node@18

# Install Python 3.11
brew install python@3.11

# Install Git (if not installed)
brew install git
```

#### 3. Configure Git
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### 4. Start Docker Desktop
- Open Docker Desktop from Applications
- Wait for Docker daemon to start (status in menu bar)
- Ensure Docker version is 24.0+

### Linux Setup (Ubuntu/Debian)

#### 1. Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Install Docker
```bash
# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 3. Install Node.js 18
```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Install Node.js
sudo apt install -y nodejs
```

#### 4. Install Python 3.11
```bash
# Install Python and development tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set default python3 to python3.11
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

#### 5. Install Git
```bash
sudo apt install -y git
```

### Windows Setup (WSL2)

#### 1. Enable WSL2
```powershell
# Run as Administrator
wsl --install
```

#### 2. Install Ubuntu from Microsoft Store
- Open Microsoft Store
- Search "Ubuntu 22.04 LTS"
- Install and launch Ubuntu

#### 3. Setup Ubuntu (follow Linux instructions above)
```bash
# Update and install tools in Ubuntu
sudo apt update && sudo apt upgrade -y
# Then follow Linux setup instructions
```

#### 4. Install Docker Desktop for Windows
- Download from [Docker Website](https://docker.com/products/docker-desktop)
- Enable WSL2 integration in Docker Desktop settings
- Restart Docker Desktop

---

## Project Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd onyx
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env.local

# Edit environment file
nano .env.local  # or use your preferred editor
```

#### Required Environment Variables
```bash
# Google OAuth2 (required for authentication)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LLM API Keys (at least one required)
TOGETHER_API_KEY=your-together-ai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# Database Security
POSTGRES_PASSWORD=generate-secure-password-here
ENCRYPTION_KEY=generate-32-byte-hex-string

# Development Settings
NODE_ENV=development
```

### 3. Automated Setup (Recommended)
```bash
# Run the automated setup script
./scripts/setup.sh
```

### 4. Manual Setup (Alternative)
```bash
# Install frontend dependencies
cd suna
npm install
cd ..

# Install backend dependencies
cd onyx-core
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

---

## Starting Services

### Quick Start
```bash
# Start all services in background
docker compose up -d

# Start services with logs visible
docker compose up

# Start specific services
docker compose up -d postgres redis qdrant
```

### Service Startup Order
Critical services start in this order automatically:
1. **Database Services:** postgres, redis, qdrant
2. **LLM Services:** ollama, litellm-proxy
3. **Application Services:** onyx-core, suna
4. **Infrastructure:** nginx, prometheus, grafana

### Verify Services
```bash
# Check all services are running
docker compose ps

# Check service logs
docker compose logs -f [service-name]

# Check service health
curl http://localhost:3000/api/health  # Frontend
curl http://localhost:8080/health       # Backend
```

---

## Port Configuration

### Default Service Ports
| Service | Port | Purpose |
|---------|------|---------|
| **suna** (Frontend) | 3000 | Next.js application |
| **onyx-core** (Backend) | 8080 | FastAPI service |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Cache and job queue |
| **qdrant** | 6333 | Vector database HTTP |
| **qdrant** | 6334 | Vector database gRPC |
| **nginx** | 80/443 | Reverse proxy |
| **litellm-proxy** | 4000 | LLM routing service |
| **ollama** | 11434 | Local LLM service |
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3001 | Monitoring dashboard |

### Resolving Port Conflicts
If ports are already in use:

#### Option 1: Stop Conflicting Services
```bash
# Find process using port
sudo lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

#### Option 2: Change ONYX Ports
Edit `.env.local` to override default ports:
```bash
# Example: Change frontend port
FRONTEND_PORT=3001

# Example: Change backend port
BACKEND_PORT=8081
```

#### Option 3: Use Docker Compose Override
Create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  suna:
    ports:
      - "3001:3000"  # Map host 3001 to container 3000
```

---

## Development Workflow

### Frontend Development
```bash
cd suna

# Start development server (hot reload)
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Lint code
npm run lint

# Type checking
npm run type-check
```

### Backend Development
```bash
cd onyx-core

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start development server
python main.py

# Run tests
pytest

# Run tests with coverage
pytest --cov=.

# Lint code
flake8 .

# Type checking
mypy .

# Format code
black .
isort .
```

### Database Operations
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U manus -d manus

# View database logs
docker compose logs postgres

# Reset database (destructive)
docker compose down -v
docker compose up -d postgres
```

### Cache Operations
```bash
# Connect to Redis
docker compose exec redis redis-cli

# Clear all cache
docker compose exec redis redis-cli FLUSHALL

# Monitor Redis
docker compose exec redis redis-cli MONITOR
```

---

## Testing

### Run All Tests
```bash
# Frontend tests
cd suna && npm test

# Backend tests
cd onyx-core && pytest

# Integration tests
pytest tests/
```

### Test Coverage
```bash
# Frontend coverage
cd suna && npm run test:coverage

# Backend coverage
cd onyx-core && pytest --cov=.
```

### Environment Validation
```bash
# Validate environment configuration
./scripts/validate-secrets.sh

# Test secrets masking
./scripts/test-secrets-masking.sh

# Validate runtime secrets
./scripts/validate-runtime-secrets.sh
```

---

## Troubleshooting

### Common Issues

#### Docker Issues
**Problem:** Docker daemon not running
```bash
# macOS/Linux
sudo systemctl start docker  # Linux
# Open Docker Desktop on macOS

# Check Docker status
docker --version
docker compose version
```

**Problem:** Permission denied
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker  # or logout/login
```

#### Port Conflicts
**Problem:** Port already in use
```bash
# Find and kill process using port
sudo lsof -i :3000
kill -9 <PID>

# Or change ONYX port in .env.local
```

#### Node.js Issues
**Problem:** Node version too old
```bash
# Check current version
node --version

# Install correct version using nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

#### Python Issues
**Problem:** Python version mismatch
```bash
# Check Python version
python3 --version

# Create virtual environment with correct Python
python3.11 -m venv venv
source venv/bin/activate
```

#### Environment Issues
**Problem:** Missing environment variables
```bash
# Validate environment file
./scripts/validate-secrets.sh

# Check required variables
grep -E "^(GOOGLE_|TOGETHER_|DEEPSEEK_|POSTGRES_|ENCRYPTION_)" .env.local
```

#### Service Startup Issues
**Problem:** Services fail to start
```bash
# Check service logs
docker compose logs [service-name]

# Check service status
docker compose ps

# Restart specific service
docker compose restart [service-name]

# Rebuild and restart
docker compose up -d --build [service-name]
```

#### Database Issues
**Problem:** Database connection failed
```bash
# Check PostgreSQL is running
docker compose exec postgres pg_isready

# Test connection from backend
docker compose exec onyx-core python -c "from app.database import engine; print(engine.url)"

# Reset database
docker compose down -v
docker compose up -d postgres
```

### Getting Help

1. **Check Logs:** Always check service logs first
2. **Validate Environment:** Run `./scripts/validate-secrets.sh`
3. **Check Documentation:** Review [Architecture](docs/architecture.md) and [API docs](http://localhost:8080/docs)
4. **Community:** Check issues and discussions in the repository

---

## Verification Checklist

After completing setup, verify each item:

### Prerequisites ✅
- [ ] Docker Desktop/Docker Engine installed and running
- [ ] Node.js 18+ installed
- [ ] Python 3.10+ installed
- [ ] Git configured with user details

### Environment Setup ✅
- [ ] Repository cloned successfully
- [ ] `.env.local` created from template
- [ ] Required environment variables configured
- [ ] Setup script runs without errors

### Service Startup ✅
- [ ] `docker compose up -d` starts all services
- [ ] All services show "healthy" status in `docker compose ps`
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend health check passes at http://localhost:8080/health

### Health Checks ✅
- [ ] Frontend: `curl http://localhost:3000/api/health` returns 200
- [ ] Backend: `curl http://localhost:8080/health` returns 200
- [ ] Database: PostgreSQL accepting connections
- [ ] Cache: Redis responding to ping
- [ ] Vector DB: Qdrant accessible at http://localhost:6333

### Development Tools ✅
- [ ] Frontend development server starts with `npm run dev`
- [ ] Backend development server starts with `python main.py`
- [ ] Tests run successfully for both frontend and backend
- [ ] Linting and formatting tools work

---

## Next Steps

Once setup is complete:

1. **Explore the UI:** Open http://localhost:3000
2. **Check API Docs:** Visit http://localhost:8080/docs
3. **Review Architecture:** Read [docs/architecture.md](architecture.md)
4. **Run Tests:** Execute the full test suite
5. **Start Development:** Begin working on features

---

## Performance Tips

### Docker Optimization
- Allocate sufficient RAM to Docker Desktop (8GB+ recommended)
- Use SSD storage for better Docker performance
- Enable Docker Desktop's "Use virtualization framework" on Apple Silicon

### Development Performance
- Use `npm run dev` for frontend hot reload
- Run backend services directly outside Docker for faster iteration
- Use `docker compose up -d` for background services

### Resource Monitoring
```bash
# Monitor Docker resource usage
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

---

**Setup Complete!** 🎉

You now have a fully functional ONYX development environment. The entire setup should take less than 30 minutes on a modern machine with a good internet connection.

For additional help, refer to:
- [Architecture Documentation](docs/architecture.md)
- [API Documentation](http://localhost:8080/docs)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Project Issues and Discussions