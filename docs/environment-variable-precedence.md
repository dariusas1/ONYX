# Environment Variable Precedence and Override Behavior

This document explains how environment variables are loaded and prioritized in the ONYX platform.

## Loading Order

Environment variables are loaded in the following order (higher priority overrides lower):

1. **Docker Secrets** (highest priority)
   - Used in production deployments
   - Loaded from Docker Swarm secrets
   - Accessed via `/run/secrets/{secret_name}` file paths

2. **Environment Files** (.env.local, .env.production, etc.)
   - Loaded via Docker Compose `env_file` directive
   - Service-specific environment files override global ones

3. **Shell Environment** 
   - Variables set in the shell before running Docker Compose
   - Can override values from environment files

4. **Docker Compose Environment Section** (lowest priority)
   - Hardcoded values in `docker-compose.yaml`
   - Should be avoided for sensitive values

## File Precedence

When using environment switching, files are prioritized as follows:

1. `.env.local` - Current/development environment (default)
2. `.env.development` - Development-specific overrides
3. `.env.staging` - Staging environment configuration
4. `.env.production` - Production environment configuration
5. `.env.example` - Template with all required variables

## Override Examples

### Development Override
```bash
# Override specific values for development
export LOG_LEVEL=debug
export NODE_ENV=development
docker compose up
```

### Production Override
```bash
# Use production environment file
cp .env.production .env.local
docker compose up
```

### Docker Secrets Override
```bash
# Use Docker secrets (production)
docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml up
```

## Variable Categories

### Sensitive Variables (Use Docker Secrets in Production)
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `QDRANT_API_KEY`
- `TOGETHER_API_KEY`
- `DEEPSEEK_API_KEY`
- `GOOGLE_CLIENT_SECRET`
- `ENCRYPTION_KEY`
- `SESSION_SECRET`
- `GRAFANA_PASSWORD`

### Non-Sensitive Variables (Can Use Environment Files)
- `NODE_ENV`
- `LOG_LEVEL`
- `LOG_FORMAT`
- `DATABASE_URL` (constructed from password)
- `REDIS_URL`
- `QDRANT_URL`
- `API_TITLE`
- `API_DESCRIPTION`
- `CORS_ORIGINS`

### Configuration Variables
- `PYTHONPATH`
- `SERVICE_NAME`
- `NEXT_PUBLIC_*` (frontend-only variables)

## Security Implementation

### Secrets Masking

**CRITICAL SECURITY FIX IMPLEMENTED**: All secrets are now properly masked in docker compose config.

- **Production environments** use pure variable substitution: `${SECRET_VAR}`
- **Development environments** may use defaults: `${SECRET_VAR:-dev-value}`
- **Docker Compose config** shows masked secrets as empty strings when variables are not set

### Variable Format Rules

```bash
# ✅ CORRECT - Masks secrets in docker compose config
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ❌ WRONG - Exposes secrets in docker compose config
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-default-secret}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-dev-password}
```

## Best Practices

1. **Never commit actual secrets** to version control
2. **Use variable substitution** for all sensitive values in production
3. **Validate secrets masking** with `docker compose config` before deployment
4. **Run validation scripts** to ensure no exposed secrets
5. **Use environment switching** for different deployment environments
6. **Test configuration** in staging before production deployment

### Security Validation Commands

```bash
# CRITICAL: Always run before deployment
./scripts/validate-runtime-secrets.sh

# Verify secrets are masked (should show empty strings)
docker compose config | grep -E "(PASSWORD|KEY|SECRET)"

# Test environment switching
./scripts/switch-env.sh production
```

## Validation

Use the provided validation scripts to ensure proper configuration:

```bash
# Validate runtime secrets
./scripts/validate-runtime-secrets.sh

# Test secrets masking
./scripts/test-secrets-masking.sh

# Switch environments
./scripts/switch-env.sh production
```

## Troubleshooting

### Common Issues

1. **Placeholders still visible**: Ensure actual values replace placeholders in `.env.local`
2. **Variables not loading**: Check that `env_file` directive is present in docker-compose.yaml
3. **Docker secrets not working**: Ensure Docker Swarm is initialized and secrets are created
4. **Environment switching fails**: Verify target environment file exists

### Debug Commands

```bash
# Check current environment variables
docker compose config

# Test specific environment file
ENV_FILE=.env.production ./scripts/validate-runtime-secrets.sh

# List Docker secrets
docker secret ls

# Check service environment
docker exec <container> env | grep -E "(PASSWORD|KEY|SECRET)"
```