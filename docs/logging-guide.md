# ONYX Logging Guide

## Overview

ONYX provides comprehensive structured JSON logging across all services with centralized log aggregation and real-time viewing capabilities.

## Services and Logging

### Services Overview

| Service | Technology | Log Location | Log Format |
|---------|------------|--------------|------------|
| **Suna** | Next.js (Node.js) | `./logs/suna/` | Structured JSON |
| **Onyx Core** | Python (FastAPI) | `./logs/onyx-core/` | Structured JSON |
| **Nginx** | Reverse Proxy | `./logs/nginx/` | Structured JSON |

### Log Entry Format

All services output structured JSON logs with consistent schema:

```json
{
  "timestamp": "2025-11-13T10:30:00.000Z",
  "level": "info",
  "service": "suna",
  "action": "user_request",
  "request_id": "req_1234567890_abcdef123",
  "user_id": "user_456",
  "metadata": {
    "method": "POST",
    "path": "/api/chat",
    "status_code": 200,
    "response_time_ms": 150
  },
  "error": null,
  "duration_ms": 150,
  "operation_id": "api_request_1234567890"
}
```

## Log Levels

| Level | Description | Usage |
|-------|-------------|-------|
| **debug** | Detailed debugging information | Development troubleshooting |
| **info** | General information about normal operation | Regular operational events |
| **warn** | Warning conditions that don't prevent operation | Potential issues |
| **error** | Error conditions that may affect functionality | Problems requiring attention |

## Viewing Logs

### Method 1: Using the Log Viewer Script (Recommended)

The `scripts/view-logs.sh` script provides powerful log viewing capabilities:

```bash
# View last 50 lines from all services
./scripts/view-logs.sh

# Follow logs in real-time
./scripts/view-logs.sh -f

# View specific service logs
./scripts/view-logs.sh onyx-core
./scripts/view-logs.sh suna
./scripts/view-logs.sh nginx

# View last 100 lines
./scripts/view-logs.sh -n 100

# Filter by log level
./scripts/view-logs.sh -l error
./scripts/view-logs.sh -l warn

# Filter by request ID (for distributed tracing)
./scripts/view-logs.sh -r req_1234567890_abcdef123

# View logs with human-readable timestamps
./scripts/view-logs.sh -t

# View raw JSON output
./scripts/view-logs.sh -j
```

### Method 2: Docker Compose Logs

```bash
# View all service logs
docker-compose logs

# Follow all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs suna
docker-compose logs onyx-core
docker-compose logs nginx

# View logs with timestamps
docker-compose logs -t

# View recent logs (last 100 lines)
docker-compose logs --tail=100
```

### Method 3: Direct Log Files

```bash
# View service log files directly
tail -f logs/suna/*.log
tail -f logs/onyx-core/*.log
tail -f logs/nginx/*.log

# Search logs with grep
grep "error" logs/onyx-core/*.log
grep "request_id" logs/suna/*.log
```

## Log Analysis and Debugging

### Searching for Patterns

```bash
# Find all errors
./scripts/view-logs.sh -l error

# Find all warnings
./scripts/view-logs.sh -l warn

# Find requests by user
grep "user_id:user_456" logs/*/access.log

# Find slow requests (response time > 1000ms)
grep '"response_time_ms":[0-9]\{4,\}' logs/*/access.log
```

### Request Tracing

Use request IDs to trace requests across services:

```bash
# Find the request ID from a frontend log
./scripts/view-logs.sh -j suna | grep "api_request"

# Use the request ID to find related logs in all services
./scripts/view-logs.sh -r req_1234567890_abcdef123
```

### Performance Analysis

```bash
# Find slow operations
./scripts/view-logs.sh -j | jq 'select(.duration_ms > 1000)'

# Monitor response times
./scripts/view-logs.sh -f | grep "response_time_ms"

# Find database operations
./scripts/view-logs.sh -j onyx-core | grep "database"
```

## Log Configuration

### Environment Variables

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| `LOG_LEVEL` | All | `info` | Minimum log level to output |
| `LOG_FORMAT` | All | `json` | Log format (json/text) |
| `SERVICE_NAME` | Onyx Core | `onyx-core` | Service identifier |
| `NEXT_PUBLIC_SERVICE_NAME` | Suna | `suna-frontend` | Service identifier |
| `NEXT_PUBLIC_LOG_LEVEL` | Suna | `info` | Frontend log level |

### Log Rotation

Docker Compose automatically configures log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # Maximum file size: 10MB
    max-file: "3"      # Keep 3 rotated files
    labels: "service=suna,environment=development"
```

## Request ID Tracking

All services support request ID propagation for distributed tracing:

### Adding Request IDs in Code

**Suna (Next.js):**
```typescript
import { setLogContext } from '@/lib/logger';

// Set request context for API route
setLogContext('request_id', 'req_1234567890_abcdef123');
setLogContext('user_id', 'user_456');

// Your API logic here
```

**Onyx Core (Python):**
```python
from logger import get_logger

logger = get_logger()
logger.info("processing_request",
           details={"endpoint": "/api/chat"},
           request_id="req_1234567890_abcdef123",
           user_id="user_456")
```

## Health Check Logging

Health check endpoints are excluded from regular logging to reduce noise:

```bash
# Health checks are automatically filtered
# Use -l info to see operational logs instead
./scripts/view-logs.sh -l info
```

## Troubleshooting

### Common Issues

1. **No log files found**
   - Services may not have started yet
   - Check Docker Compose status: `docker-compose ps`
   - Use Docker Compose logs as fallback: `docker-compose logs`

2. **Missing JSON formatting**
   - Check service configuration
   - Verify environment variables are set correctly
   - Restart services: `docker-compose restart`

3. **Permission errors**
   - Ensure log directories are writable
   - Run: `chmod -R 755 logs/`

4. **High log volume**
   - Adjust log levels using environment variables
   - Implement log filtering in the viewing script

### Log Analysis Examples

**Finding HTTP Errors:**
```bash
./scripts/view-logs.sh -l error nginx | grep "status_code"
```

**Monitoring Database Performance:**
```bash
./scripts/view-logs.sh onyx-core | grep "database_query"
```

**Tracking User Activity:**
```bash
grep "user_id:user_456" logs/*/access.log | tail -20
```

## Integration with Monitoring Tools

### Prometheus Metrics

Log metrics are available at `/metrics` endpoints:

- `suna`: http://localhost:3000/metrics
- `onyx-core`: http://localhost:8080/metrics
- `nginx`: http://localhost/metrics

### Grafana Dashboards

Grafana is available at http://localhost:3001 with pre-configured dashboards for:
- Request latency
- Error rates
- Service health
- Log volume

## Best Practices

1. **Use appropriate log levels**
   - `debug`: Detailed troubleshooting information
   - `info`: Normal operational events
   - `warn`: Potential issues
   - `error`: Problems requiring attention

2. **Include request IDs** for distributed tracing
3. **Add structured metadata** for better filtering
4. **Use timers** for performance monitoring
5. **Avoid sensitive data** in logs

## Log File Locations

```
logs/
├── suna/
│   ├── access.log
│   └── error.log
├── onyx-core/
│   ├── access.log
│   └── error.log
└── nginx/
    ├── access.log
    └── error.log
```

## Maintenance

### Log Cleanup

Log rotation is handled automatically by Docker Compose. Files are rotated when they reach 10MB and the last 3 files are kept.

### Monitoring Disk Usage

```bash
# Check log directory size
du -sh logs/

# Find largest log files
find logs/ -name "*.log" -exec ls -lh {} \; | sort -k5 -hr
```

### Backup Logs

```bash
# Archive logs older than 7 days
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
find logs/ -name "*.log.gz" -mtime +30 -delete
```