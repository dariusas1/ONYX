# ONYX Backlog

## Action Items & Follow-ups

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|--------|--------|-------|
| 2025-11-10 | 1.1 | 1 | Tech Debt | Low | TBD | Open | Implement actual database connectivity checks in health endpoints [onyx-core/health.py:32-34] |
| 2025-11-10 | 1.1 | 1 | Tech Debt | Low | TBD | Open | Add missing REDIS_PASSWORD default or remove reference [docker-compose.yaml:104] |
| 2025-11-10 | 1.1 | 1 | Security | Low | TBD | Open | Configure non-root users for production containers [docker-compose.yaml:6,44] |
| 2025-11-10 | 1.2 | 1 | Bug | High | TBD | Open | Generate self-signed SSL certificates for localhost [nginx/ssl/] |
| 2025-11-10 | 1.2 | 1 | Enhancement | Med | TBD | Open | Add explicit location block for /chat/ routing to Suna backend [nginx/nginx.conf:188] |
| 2025-11-10 | 1.2 | 1 | Enhancement | Med | TBD | Open | Create SSL certificate generation script for development setup [scripts/generate-ssl.sh] |
| 2025-11-10 | 1.3 | 1 | Bug | Med | TBD | Open | Fix secrets masking in docker compose config output (AC #5) [docker-compose.yaml:11-222] |
| 2025-11-10 | 1.3 | 1 | Security | Med | TBD | Open | Replace placeholder values in production environment with proper variable references (AC #4, #5) [.env.production:19-20] |
| 2025-11-10 | 1.3 | 1 | Tech Debt | Low | TBD | Open | Remove ${VAR} references in docker-compose.yaml environment sections, rely solely on env_file (Task #2) [docker-compose.yaml:16-24] |
| 2025-11-10 | 1.3 | 1 | Enhancement | Low | TBD | Open | Add production Docker secrets configuration example (Task #3) [scripts/test-secrets-masking.sh:164-241] |

## Notes

- Story 1.2 has HIGH severity SSL certificate issue that must be resolved before HTTPS functionality
- Foundation infrastructure is production-ready except for missing SSL certificates
- Consider addressing CORS origin restriction ("*") before production deployment
- Story 1.2 items include both critical fixes and enhancements for maintainability