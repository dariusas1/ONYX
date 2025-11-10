# ONYX - Strategic Intelligence System

**Project:** Manus Internal - M3rcury's Strategic Intelligence System  
**Status:** Foundation & Infrastructure Setup (Epic 1)  
**Version:** 1.0.0  

## Quick Start

### Prerequisites
- Docker Desktop or Docker Engine
- Node.js 18+ (for local development)
- Python 3.10+ (for local development)

### Setup Commands

```bash
# Clone repository
git clone <repository-url>
cd onyx

# Create environment file
cp .env.example .env.local
# Edit .env.local with your credentials

# Start all services
docker compose up -d

# Verify services are running
docker compose ps

# View logs
docker compose logs -f
```

### Service URLs

- **Frontend (Suna):** http://localhost:3000
- **API Documentation:** http://localhost:8080/docs
- **Grafana Dashboard:** http://localhost:3001
- **Prometheus Metrics:** http://localhost:9090

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **suna** | 3000 | Next.js frontend with Suna UI components |
| **onyx-core** | 8080 | Python RAG service |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Cache and job queue |
| **qdrant** | 6333 | Vector database for semantic search |
| **nginx** | 80/443 | Reverse proxy and load balancer |
| **litellm-proxy** | 4000 | LLM routing and fallback |
| **ollama** | 11434 | Local fallback LLM |
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3001 | Monitoring dashboards |

## Health Checks

All services implement health check endpoints:

- Frontend: `GET /api/health`
- Onyx Core: `GET /health`
- Database: PostgreSQL native health check
- Redis: `redis-cli ping`
- Qdrant: `GET /health`

## Development

### Frontend Development
```bash
cd suna
npm install
npm run dev
```

### Backend Development
```bash
cd onyx-core
pip install -r requirements.txt
python main.py
```

### Testing
```bash
# Frontend tests
cd suna && npm test

# Backend tests
cd onyx-core && pytest
```

## Architecture

This is a **multi-service, self-hosted strategic AI platform** combining:

- **Real-time chat** with streaming responses
- **Company-wide RAG** (Retrieval-Augmented Generation)
- **Persistent memory** and user context
- **Autonomous agent execution** with approval gates
- **Google Workspace integration**
- **Web automation** capabilities

## Technology Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Suna UI
- **Backend:** FastAPI (Python), PostgreSQL, Redis, Qdrant
- **LLM:** DeepSeek (via Together AI) + Ollama fallback
- **Infrastructure:** Docker Compose, Nginx, Prometheus, Grafana

## Security

- Google OAuth2 for authentication
- Encrypted credential storage
- Rate limiting and approval gates
- Structured audit logging
- Self-hosted data (no vendor lock-in)

## Monitoring

- Prometheus metrics collection
- Grafana dashboards
- Structured JSON logging
- Health check endpoints
- Error tracking with Sentry (optional)

## Contributing

1. Follow the established directory structure
2. Use conventional commit messages
3. Add tests for new functionality
4. Update documentation
5. Ensure all health checks pass

## Support

For technical questions or issues:
- Check the [Architecture Document](docs/architecture.md)
- Review [Development Guide](docs/DEVELOPMENT.md)
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

---

**Status:** ✅ Foundation setup complete - Ready for development