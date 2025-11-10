# Epic Technical Specification: Foundation & Infrastructure

Date: 2025-11-10
Author: darius
Epic ID: epic-1
Status: Draft

---

## Overview

Epic 1 establishes the foundational infrastructure for Manus Internal, enabling all subsequent development. This epic creates the Docker-based multi-service environment, deployment pipeline, and operational monitoring necessary for the strategic intelligence platform. The foundation supports Suna UI, Onyx Core RAG service, Qdrant vector database, Supabase PostgreSQL, and Redis cache - all orchestrated via Docker Compose on Hostinger KVM 4 VPS.

## Objectives and Scope

### In-Scope:
- Docker Compose orchestration for 6 core services (Suna, Onyx, Qdrant, Supabase, Redis, Nginx)
- Nginx reverse proxy configuration with SSL/TLS support
- Environment configuration and secrets management across dev/staging/prod
- CI/CD pipeline via GitHub Actions (lint → test → build → deploy)
- Local development environment setup with one-command startup
- Foundation monitoring and logging with structured JSON output

### Out-of-Scope:
- Production SSL certificates (Let's Encrypt - Epic 9)
- Advanced monitoring (Prometheus/Grafana - Epic 9)
- Backup automation (Epic 9)
- Performance optimization (baseline only)
- Multi-user scaling (single-user MVP)

## System Architecture Alignment

Epic 1 implements the foundational container orchestration layer defined in the architecture document. This epic establishes the Docker Compose environment that hosts all services, implements the Nginx reverse proxy routing pattern, and provides the base infrastructure patterns (environment management, health checks, logging) that all other epics depend upon. The foundation enables the multi-service architecture with proper service isolation, networking, and data persistence as specified in the technical architecture.

## Detailed Design

### Services and Modules

| Service | Purpose | Port | Responsibilities | Owner |
|---------|---------|------|----------------|-------|
| **suna** | Next.js frontend + API | 3000 | Chat UI, API routing, auth, streaming | Frontend |
| **onyx-core** | Python RAG service | 8080 | Vector search, document sync, connectors | Backend |
| **postgres** | Supabase PostgreSQL | 5432 | User data, conversations, memories, tasks | Data |
| **redis** | Cache + job queue | 6379 | Sessions, rate limiting, BullMQ jobs | Infrastructure |
| **qdrant** | Vector database | 6333 | Semantic search, document embeddings | Data |
| **nginx** | Reverse proxy | 80/443 | SSL termination, routing, static assets | DevOps |
| **litellm-proxy** | LLM routing | 4000 | DeepSeek + Ollama fallback, rate limiting | Backend |
| **ollama** | Fallback LLM | 11434 | Local inference when API unavailable | Backend |

### Service Dependencies:
```
nginx → suna (frontend)
nginx → onyx-core (API)
suna → postgres, redis, litellm-proxy
onyx-core → qdrant, postgres, redis
litellm-proxy → ollama (fallback)
```

### Data Models and Contracts

#### PostgreSQL Schema (Core Tables):
```sql
-- Users and authentication
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  google_id TEXT UNIQUE,
  display_name TEXT,
  encrypted_google_token BYTEA,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat sessions
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title TEXT DEFAULT 'Untitled',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Message history
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  role 'user' | 'assistant' NOT NULL,
  content TEXT NOT NULL,
  citations JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- User memories and learning
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  fact TEXT NOT NULL,
  source TEXT,
  embedding VECTOR(1536),
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Standing instructions
CREATE TABLE standing_instructions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  instruction TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Agent task tracking
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  conversation_id UUID REFERENCES conversations(id),
  description TEXT NOT NULL,
  status 'pending' | 'running' | 'success' | 'failed' NOT NULL DEFAULT 'pending',
  steps JSONB,
  result TEXT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

#### Docker Compose Service Contracts:
```yaml
# Environment variable contracts
services:
  suna:
    environment:
      - DATABASE_URL=postgresql://manus:${POSTGRES_PASSWORD}@postgres:5432/manus
      - REDIS_URL=redis://redis:6379
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
  
  onyx-core:
    environment:
      - QDRANT_URL=http://qdrant:6333
      - DATABASE_URL=postgresql://manus:${POSTGRES_PASSWORD}@postgres:5432/manus
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
```

### APIs and Interfaces

#### Nginx Reverse Proxy Routes:
```nginx
# Frontend routes
location / {
  proxy_pass http://suna:3000;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
}

# API routes  
location /api/ {
  proxy_pass http://suna:3000;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
}

# VNC workspace (future)
location /vnc/ {
  proxy_pass http://novnc:6080;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}
```

#### Health Check Endpoints:
```
GET /health  - Service health (JSON: {status: "ok", services: {...}})
GET /metrics - Prometheus metrics (if enabled)
```

#### Inter-Service Communication:
```
Suna → Onyx Core: POST http://onyx-core:8080/search
Suna → LiteLLM: POST http://litellm-proxy:4000/chat/completions
Onyx → Qdrant: POST http://qdrant:6333/collections/documents/search
All Services → Postgres: postgresql://user:pass@postgres:5432/manus
All Services → Redis: redis://redis:6379
```

#### Environment Variable Interface:
```bash
# Required for all services
POSTGRES_PASSWORD=xxxxxx
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxxx
NEXTAUTH_SECRET=xxxxxx
ENCRYPTION_KEY=xxxxxx (32-byte hex)

# Service-specific
TOGETHER_API_KEY=xxxxxx
QDRANT_API_KEY=xxxxxx (optional)
```

### Workflows and Sequencing

#### Service Startup Sequence:
1. **Infrastructure First**: postgres → redis → qdrant
2. **Backend Services**: onyx-core → litellm-proxy → ollama
3. **Frontend**: suna
4. **Proxy**: nginx (last, routes traffic)

#### Development Workflow:
```bash
# 1. Clone and setup
git clone manus-internal
cd manus-internal
cp .env.example .env.local

# 2. Start all services
docker compose up -d

# 3. Verify health
curl http://localhost/health
docker compose ps

# 4. View logs
docker compose logs -f suna
```

#### CI/CD Pipeline Sequence:
1. **Code Quality**: ESLint → Prettier → TypeScript check
2. **Testing**: Unit tests → Integration tests → Build verification
3. **Build**: Docker images → Tag with commit SHA
4. **Deploy**: Push to registry → Update production → Health check
5. **Notify**: Slack notification with deployment status

#### Configuration Loading:
1. Load `.env.local` (git-ignored, user-specific)
2. Merge with defaults from `.env.example`
3. Validate required variables present
4. Inject into Docker containers
5. Health check verifies all services accessible

## Non-Functional Requirements

### Performance

#### Service Startup Targets:
- Docker Compose up: <30 seconds to all services healthy
- Health check response: <100ms for /health endpoint
- Service restart: <10 seconds per container

#### Resource Utilization (KVM 4: 4 vCPU, 16GB RAM):
- **Suna (Next.js)**: <1GB RAM, <0.5 vCPU
- **Onyx Core**: <2GB RAM, <1 vCPU  
- **PostgreSQL**: <2GB RAM, <0.5 vCPU
- **Qdrant**: <1GB RAM, <0.5 vCPU
- **Redis**: <512MB RAM, <0.2 vCPU
- **Nginx**: <256MB RAM, <0.1 vCPU
- **Total Baseline**: <7GB RAM, <3 vCPU (leaves headroom)

#### Network Performance:
- Nginx proxy latency: <10ms
- Inter-service communication: <5ms (same Docker network)
- SSL handshake: <50ms (self-signed cert)

#### Development Experience:
- `docker compose up`: <30s to ready state
- Hot reload: <2s for frontend changes
- Log aggregation: <100ms to view logs across all services

### Security

#### Credential Management:
- All secrets in environment variables (never in code)
- `.env.local` git-ignored, `.env.example` provides template
- Database passwords auto-generated for production
- API keys encrypted at rest (AES-256) in Supabase
- No credentials in Docker images or logs

#### Network Security:
- All inter-service communication via Docker internal network
- Only Nginx exposed to external traffic (ports 80/443)
- Database ports not exposed externally
- SSL/TLS termination at Nginx layer

#### Container Security:
- Non-root user in all containers
- Minimal base images (alpine where possible)
- Security scanning in CI/CD pipeline
- Regular base image updates

#### Development Security:
- Local development uses self-signed certificates
- Google OAuth2 for authentication (no passwords)
- IP whitelist option for production access
- Audit logging for all sensitive operations

### Reliability/Availability

#### Service Health Monitoring:
- Health check endpoints on all services (`/health`)
- Docker health checks with 30-second intervals
- Automatic restart on container failure
- Dependency management (wait for postgres before starting app)

#### Data Persistence:
- PostgreSQL data volume: `/var/lib/postgresql/data`
- Qdrant vector storage: `/qdrant/storage`
- Redis persistence: RDB snapshots every 5 minutes
- Docker volumes mounted with proper permissions

#### Error Handling:
- Graceful degradation if non-critical services fail
- Circuit breaker pattern for external API calls
- Retry logic with exponential backoff
- Comprehensive error logging with context

#### Development Reliability:
- Consistent environment across dev/staging/prod
- Reproducible builds with Docker
- Version-controlled configuration
- Automated dependency updates

### Observability

#### Logging Strategy:
- Structured JSON logging across all services
- Standard log format: `{timestamp, level, service, action, details}`
- Centralized log viewing via `docker compose logs`
- Log levels: info, warn, error, debug
- No sensitive data in logs (credentials masked)

#### Health Monitoring:
- `/health` endpoint on all services returns JSON status
- Docker health checks with automatic restart
- Service dependency health verification
- Database connection health checks

#### Development Observability:
- Real-time log streaming during development
- Service status dashboard (basic)
- Request/response logging for API debugging
- Performance metrics collection (basic)

#### Foundation for Advanced Monitoring:
- Metrics endpoints ready for Prometheus (Epic 9)
- Error tracking integration points (Sentry - Epic 9)
- Audit trail foundation for security events

## Dependencies and Integrations

### External Dependencies:
| Service | Version | Purpose | Integration Point |
|---------|---------|---------|------------------|
| **Docker** | 24.0+ | Container orchestration | Runtime environment |
| **Docker Compose** | 2.20+ | Multi-service management | Development/deployment |
| **PostgreSQL** | 15+ | Primary database | Supabase-compatible |
| **Redis** | 7.0+ | Cache + job queue | Session storage |
| **Qdrant** | 1.7+ | Vector database | Semantic search |
| **Nginx** | Latest | Reverse proxy | SSL termination |
| **Node.js** | 18+ | Suna runtime | Frontend/backend |
| **Python** | 3.10+ | Onyx Core runtime | RAG processing |

### Internal Service Dependencies:
```
Epic 1 (Foundation) → All other epics (blocking dependency)
├── Docker Compose environment
├── Service networking and discovery  
├── Base configuration patterns
├── Health check standards
└── Logging and monitoring foundation
```

### Integration Points:
- **GitHub Actions**: CI/CD pipeline automation
- **Hostinger KVM 4**: Production deployment target
- **Google Cloud Platform**: OAuth2 authentication
- **Docker Hub**: Container registry (optional)

### Version Constraints:
- Docker images pinned to specific versions for reproducibility
- Node.js packages via package-lock.json
- Python requirements via requirements.txt
- Database migrations version-controlled

## Acceptance Criteria (Authoritative)

### Story 1.1: Project Setup & Repository Initialization
- AC1.1.1: `git clone` + `docker compose up` starts all services without manual configuration
- AC1.1.2: Health check endpoints return 200 for all services
- AC1.1.3: Logs aggregated and readable via `docker compose logs`
- AC1.1.4: Docker Compose includes all 6 core services with proper networking

### Story 1.2: Nginx Reverse Proxy Configuration  
- AC1.2.1: Requests to `http://localhost/api/*` proxy to Suna backend correctly
- AC1.2.2: Requests to `/chat/*` proxy to Suna (:3000) and respond correctly
- AC1.2.3: Requests to `/vnc/*` proxy to noVNC (:6080) [future]
- AC1.2.4: CORS headers configured for frontend ↔ backend communication
- AC1.2.5: SSL/TLS support with self-signed certificates for development

### Story 1.3: Environment Configuration & Secrets Management
- AC1.3.1: `.env.example` provides template with all required variables
- AC1.3.2: `.env.local` (git-ignored) loads environment variables into containers
- AC1.3.3: No secrets appear in Docker images or build logs
- AC1.3.4: Different `.env.*` files work for dev/staging/prod environments
- AC1.3.5: `docker compose config` shows masked secrets

### Story 1.4: CI/CD Pipeline (GitHub Actions)
- AC1.4.1: Workflow triggers on `push` to main/dev branches automatically
- AC1.4.2: Pipeline runs linter, tests, builds Docker images in sequence
- AC1.4.3: Images pushed to container registry with version tags
- AC1.4.4: Deployment script runs with optional manual approval for production
- AC1.4.5: Slack notification sent with build/deployment status

### Story 1.5: Local Development Environment Setup Guide
- AC1.5.1: `DEVELOPMENT.md` provides step-by-step instructions for setup
- AC1.5.2: `./scripts/setup.sh` automates prerequisite installation
- AC1.5.3: `docker compose up` starts all services on fresh machine
- AC1.5.4: Suna UI accessible at `http://localhost:3000` after setup
- AC1.5.5: All health checks pass and services ready for development

### Story 1.6: Monitoring & Logging Foundation
- AC1.6.1: All services log to stdout in structured JSON format
- AC1.6.2: `docker compose logs` shows aggregated service logs with timestamps
- AC1.6.3: Each service includes request/error logs with proper severity levels
- AC1.6.4: Health check endpoints (`/health`) return JSON status with service details
- AC1.6.5: Prometheus metrics endpoint available at `/metrics` (basic implementation)

## Traceability Mapping

| Acceptance Criteria | Spec Section | Component/Service | Test Strategy |
|-------------------|--------------|-------------------|---------------|
| AC1.1.1 | Services and Modules | Docker Compose, all services | Integration test: docker compose up |
| AC1.1.2 | APIs and Interfaces | Health endpoints | Unit test: GET /health returns 200 |
| AC1.1.3 | Observability | Logging strategy | Manual: docker compose logs verification |
| AC1.1.4 | Services and Modules | Service definitions | Code review: docker-compose.yaml |
| AC1.2.1 | APIs and Interfaces | Nginx routes | Integration: curl localhost/api/health |
| AC1.2.2 | APIs and Interfaces | Nginx routes | Integration: curl localhost/chat/ |
| AC1.2.3 | APIs and Interfaces | Nginx routes | Integration: curl localhost/vnc/ |
| AC1.2.4 | Security | Network security | Integration: CORS headers check |
| AC1.2.5 | Security | SSL/TLS | Integration: HTTPS certificate validation |
| AC1.3.1 | Security | Credential management | Manual: .env.example completeness |
| AC1.3.2 | Security | Environment variables | Integration: docker compose config |
| AC1.3.3 | Security | Credential management | Security scan: no secrets in images |
| AC1.3.4 | Security | Environment separation | Manual: multi-environment testing |
| AC1.3.5 | Security | Credential management | Integration: secret masking verification |
| AC1.4.1 | Dependencies | GitHub Actions | Integration: push to main triggers workflow |
| AC1.4.2 | Dependencies | CI/CD pipeline | Integration: workflow execution verification |
| AC1.4.3 | Dependencies | Container registry | Integration: image push verification |
| AC1.4.4 | Dependencies | Deployment pipeline | Integration: deployment script execution |
| AC1.4.5 | Observability | Notifications | Integration: Slack webhook test |
| AC1.5.1 | Dependencies | Documentation | Manual: setup guide completeness |
| AC1.5.2 | Dependencies | Setup automation | Integration: setup.sh execution |
| AC1.5.3 | Services and Modules | Service orchestration | Integration: fresh machine setup test |
| AC1.5.4 | APIs and Interfaces | Frontend access | Integration: UI accessibility test |
| AC1.5.5 | Reliability | Health monitoring | Integration: health check verification |
| AC1.6.1 | Observability | Logging strategy | Integration: log format verification |
| AC1.6.2 | Observability | Log aggregation | Manual: docker compose logs test |
| AC1.6.3 | Observability | Logging strategy | Integration: error log verification |
| AC1.6.4 | APIs and Interfaces | Health endpoints | Unit test: health endpoint response |
| AC1.6.5 | Observability | Metrics foundation | Integration: /metrics endpoint test |

## Risks, Assumptions, Open Questions

### Risks:
| Risk | Severity | Mitigation |
|------|----------|------------|
| Docker version incompatibility across team machines | Medium | Document version requirements, provide Docker Desktop install guide |
| Port conflicts on local development machines | Low | Document port mapping, provide conflict resolution steps |
| Environment variable misconfiguration | Medium | Validation scripts, comprehensive .env.example template |
| Container resource exhaustion on KVM 4 | Medium | Resource limits in Docker Compose, monitoring setup |
| SSL certificate management complexity | Low | Self-signed certs for dev, document Let's Encrypt for prod |

### Assumptions:
- Team has Docker Desktop or Docker Engine installed
- Hostinger KVM 4 VPS is available and properly configured
- Google OAuth2 credentials can be obtained for development
- All developers have access to required API keys (Together AI, etc.)
- Git-based workflow is acceptable to the team

### Open Questions:
- Should we use Docker Hub or GitHub Container Registry for images?
- Do we need separate staging environment or just dev/prod?
- Should we implement database migrations in this epic or defer?
- What's the preferred backup strategy for development data?
- Do we need automated dependency vulnerability scanning in CI/CD?

### Next Steps for Risk Mitigation:
1. Document Docker installation requirements for each OS
2. Create port conflict resolution guide
3. Implement environment variable validation script
4. Set up basic resource monitoring in Docker Compose
5. Create SSL certificate management documentation

## Test Strategy Summary

### Testing Levels:
1. **Unit Tests**: Individual service health checks, configuration validation
2. **Integration Tests**: Service communication, API routing, database connectivity
3. **End-to-End Tests**: Full Docker Compose startup, development workflow
4. **Manual Verification**: Setup guide completeness, documentation accuracy

### Test Environment:
- **Local**: Docker Compose on developer machines
- **CI**: GitHub Actions runners with Docker support
- **Validation**: Fresh machine setup test (quarterly)

### Key Test Scenarios:
```bash
# 1. Service Health
test_health_endpoints() {
  curl -f http://localhost/health || exit 1
  docker compose ps | grep "Up" || exit 1
}

# 2. Environment Configuration
test_environment_loading() {
  docker compose config | grep -v "password" || exit 1
  docker compose exec suna env | grep DATABASE_URL || exit 1
}

# 3. Development Workflow
test_development_setup() {
  ./scripts/setup.sh || exit 1
  docker compose up -d || exit 1
  curl -f http://localhost:3000 || exit 1
}

# 4. CI/CD Pipeline
test_cicd_pipeline() {
  # Triggered automatically on push
  # Verify: lint → test → build → deploy sequence
}
```

### Test Coverage Requirements:
- **Health Checks**: 100% of services
- **Configuration**: All environment variables validated
- **Documentation**: All setup steps verified
- **CI/CD**: All workflow stages tested

### Success Criteria:
- All 6 services start successfully within 30 seconds
- Health endpoints return 200 status
- Development environment setup works on fresh machine
- CI/CD pipeline executes without manual intervention
- No credentials exposed in logs or images

### Test Automation:
- GitHub Actions runs integration tests on each PR
- Automated health check monitoring in development
- Weekly dependency vulnerability scanning
- Monthly fresh-machine setup verification

## Post-Review Follow-ups

### Story 1.1 Review Action Items (2025-11-10)

**Low Severity Improvements:**
- Implement actual database connectivity checks in health endpoints (currently simulated)
- Add missing REDIS_PASSWORD environment variable handling in docker-compose.yaml
- Configure non-root users for production containers (security best practice)

**Production Readiness Notes:**
- Foundation infrastructure is production-ready with current implementation
- Action items are enhancements, not blockers for deployment
- Consider addressing before production deployment for enhanced security