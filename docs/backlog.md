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
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Fix secrets masking in docker compose config output - CRITICAL SECURITY FAILURE (AC #5) [docker-compose.yaml:11-242] |
| 2025-11-10 | 1.3 | 1 | Process | High | TBD | Open | Remove false completion claim for Task 3 - secrets masking NOT implemented [story tasks section] |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Remove all ${VAR} references with proper env_file-only approach [docker-compose.yaml:16,55,154] |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Implement actual secrets masking - current approach completely ineffective [scripts/test-secrets-masking.sh] |
| 2025-11-13 | 1.3 | 1 | Security | Critical | TBD | Open | Fix AC #5 - docker compose config exposes actual secret values when environment variables set [docker-compose.yaml:11-242] |
| 2025-11-13 | 1.3 | 1 | Security | Critical | TBD | Open | Fix test-secrets-masking.sh script - incorrectly reports success despite security failure [scripts/test-secrets-masking.sh:23-123] |
| 2025-11-13 | 1.3 | 1 | Security | Critical | TBD | Open | Implement proper secrets masking that survives environment variable substitution [docker-compose.yaml:11-242] |
| 2025-11-13 | 1.3 | 1 | Process | High | TBD | Open | Remove false completion claim for Task 3 - secrets masking completely non-functional [story tasks section] |
| 2025-11-10 | 1.3 | 1 | Security | Critical | darius | Open | **CRITICAL**: Fix complete secrets masking failure - docker compose config exposes all secrets when actual values present |
| 2025-11-10 | 1.3 | 1 | Security | Critical | TBD | Open | **CRITICAL**: Fix environment variable precedence - environment variables do NOT override .env.local values |
| 2025-11-13 | 1.3 | 1 | Security | Critical | darius | Open | **CRITICAL**: AC #5 NOT IMPLEMENTED - secrets masking completely broken in standard docker-compose.yaml |
| 2025-11-13 | 1.3 | 1 | Security | Critical | darius | Open | **CRITICAL**: Multiple secrets exposed in docker compose config (TOGETHER_API_KEY, DEEPSEEK_API_KEY, GOOGLE_CLIENT_SECRET, ENCRYPTION_KEY) |
| 2025-11-13 | 1.3 | 1 | Process | High | darius | Open | Correct Task 3 completion status - falsely marked complete despite critical security failure |
| 2025-11-10 | 1.3 | 1 | Security | Critical | TBD | Open | **CRITICAL**: Resolve Docker Compose configuration conflicts preventing proper secrets masking |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Implement proper Docker secrets for production environment (replace environment variable approach) |
| 2025-11-10 | 1.3 | 1 | Process | High | TBD | Open | Update validation scripts to test environment variable override functionality |
| 2025-11-10 | 1.3 | 1 | Process | Critical | darius | Open | **CRITICAL**: Fix validation scripts - test with actual secret values, not empty ones |
| 2025-11-10 | 1.3 | 1 | Architecture | Critical | darius | Open | **CRITICAL**: Replace environment variable approach with Docker secrets for production |
| 2025-11-10 | 1.3 | 1 | Security | High | darius | Open | Implement production-ready secrets management (Docker secrets or external secret manager) |
| 2025-11-10 | 1.3 | 1 | Process | High | darius | Open | Review why multiple previous reviews missed critical security vulnerability |
| 2025-11-10 | 1.4 | 1 | Security | Med | TBD | Open | Pin all GitHub Actions to commit SHAs instead of version tags [.github/workflows/main.yml:22,25,47,123,132,141,144,155,164] |
| 2025-11-10 | 1.4 | 1 | Security | Med | TBD | Open | Add container vulnerability scanning step in pipeline [.github/workflows/main.yml:173] |
| 2025-11-10 | 1.4 | 1 | Security | Med | TBD | Open | Add CodeQL code security scanning [.github/workflows/main.yml:110] |
| 2025-11-10 | 1.4 | 1 | Security | Med | TBD | Open | Generate SBOM for built images [.github/workflows/main.yml:172] |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Replace placeholder values in production environment with proper variable references (AC #4) [.env.production:19-21] |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Add runtime secret validation to prevent deployment with placeholder values [scripts/validate-runtime-secrets.sh] |
| 2025-11-10 | 1.3 | 1 | Security | High | TBD | Open | Implement production-ready secrets management (Docker secrets or external secret manager) [docker-compose.secrets.yaml] |

## Notes

- Story 1.2 has HIGH severity SSL certificate issue that must be resolved before HTTPS functionality
- Foundation infrastructure is production-ready except for missing SSL certificates
- Consider addressing CORS origin restriction ("*") before production deployment
- Story 1.2 items include both critical fixes and enhancements for maintainability