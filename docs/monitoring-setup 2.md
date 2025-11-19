# ONYX Monitoring Setup

This document describes the comprehensive monitoring infrastructure implemented for ONYX as part of Story 9-1.

## Overview

The monitoring system consists of:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Custom Metrics**: Business and application-level metrics
- **Infrastructure Monitoring**: System and container metrics

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Applications  │───▶│   Prometheus     │───▶│   Grafana        │
│   (6 Services)  │    │   (Scraping)     │    │   (Dashboards)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                       │
        ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Custom Metrics  │    │  Time Series DB  │    │  10s Refresh    │
│ Business Logic  │    │  (200h Retention)│    │   Authentication │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Services Monitored

### Core Applications (15s scrape interval)
1. **Suna Frontend** (Next.js) - `http://suna:3000/api/metrics`
2. **Onyx Core** (Python/FastAPI) - `http://onyx-core:8080/metrics`
3. **Qdrant** (Vector DB) - `http://qdrant:6333/metrics`
4. **PostgreSQL** - `http://postgres:5432/metrics`
5. **Redis** - `http://redis:6379/metrics`
6. **LiteLLM Proxy** - `http://litellm-proxy:4000/metrics`

### Infrastructure Monitoring
- **Node Exporter** - System metrics (CPU, memory, disk, network)
- **cAdvisor** - Container metrics and resource usage

## Metrics Collected

### HTTP/Application Metrics
- `http_request_duration_seconds` - Request latency percentiles
- `http_requests_total` - Request counts by method, route, status
- `http_requests_active` - Concurrent requests

### ONYX Business Metrics
- `onyx_chat_duration_seconds` - LLM chat interaction duration
- `onyx_rag_retrieval_duration_seconds` - RAG retrieval performance
- `onyx_task_completion_total` - Task completion tracking
- `onyx_active_agents` - Active agent counts
- `onyx_active_connections_total` - Active connection count

### Quality Metrics
- `onyx_rag_retrieval_accuracy_score` - RAG accuracy (0-1)
- `onyx_rag_retrieval_relevance_score` - RAG relevance (0-1)

## Grafana Dashboards

### 1. System Overview (`onyx-system-overview`)
- CPU usage by container
- Memory usage by container
- Disk space available
- Network I/O
- Container status and uptime

### 2. Application Performance (`onyx-application-performance`)
- HTTP request duration (95th and 50th percentiles)
- Error rates (4xx and 5xx)
- Request throughput
- Active connections
- Response time distribution

### 3. LLM Metrics (`onyx-llm-metrics`)
- LLM call duration by model
- Success rates by model
- Call rate by model
- Token usage statistics
- LiteLLM proxy latency
- Active users by model

### 4. RAG Performance (`onyx-rag-performance`)
- RAG retrieval latency
- Vector search performance
- Retrieval accuracy and relevance scores
- Vector storage usage
- Total vector count
- Operations throughput

### 5. Infrastructure Health (`onyx-infrastructure-health`)
- Service status overview
- Container restart counts
- Database connection pool
- Memory usage breakdown
- Error rate trends
- Disk I/O performance

## Configuration Files

### Prometheus Configuration
- **File**: `prometheus/prometheus.yml`
- **Scrape Interval**: 15 seconds
- **Retention**: 200 hours (8 days)
- **Targets**: All 6 core services + infrastructure metrics

### Grafana Configuration
- **Datasources**: `grafana/provisioning/datasources/prometheus.yml`
- **Dashboards**: `grafana/provisioning/dashboards/dashboards.yml`
- **Auto-provisioning**: Dashboards update every 10 seconds

## Authentication

### Metrics Endpoints
- **Username**: `admin` (configurable via `METRICS_USERNAME`)
- **Password**: `admin` (configurable via `METRICS_PASSWORD`)
- **Method**: Basic Authentication

### Grafana
- **Admin Password**: `GRAFANA_PASSWORD` environment variable
- **Sign-up**: Disabled
- **Anonymous Access**: Disabled

## Performance Requirements

### Metrics Collection
- **Scrape Interval**: 15 seconds
- **Endpoint Response Time**: <10ms (p95)
- **Collection Overhead**: <5% CPU

### Dashboards
- **Refresh Rate**: 10 seconds
- **Load Time**: <2 seconds
- **Data Freshness**: <15 seconds

## Testing

### Automated Test Script
Run the comprehensive monitoring test:
```bash
./scripts/test-monitoring.sh
```

### Manual Validation
1. **Prometheus**: http://localhost:9090/targets - Check all targets are "UP"
2. **Grafana**: http://localhost:3001 - Login and verify dashboards
3. **Metrics**: http://localhost:3000/api/metrics - Verify basic auth works

## Troubleshooting

### Common Issues

#### Prometheus Not Scraping
- Check service connectivity: `curl http://service-name:port/metrics`
- Verify basic auth credentials
- Check Prometheus configuration syntax
- Review service logs

#### Grafana Dashboards Missing
- Restart Grafana container
- Check provisioning configuration
- Verify dashboard JSON files exist
- Review Grafana logs

#### High Metrics Latency
- Check metrics endpoint performance
- Monitor container resources
- Review custom metrics complexity
- Consider increasing scrape timeout

### Logs
```bash
# View Prometheus logs
docker compose logs prometheus

# View Grafana logs
docker compose logs grafana

# View service-specific logs
docker compose logs suna
docker compose logs onyx-core
```

## Maintenance

### Regular Tasks
1. **Monitor storage usage** - Prometheus storage grows over time
2. **Review metric cardinality** - Avoid high-cardinality labels
3. **Update dashboards** - Add new metrics as features are added
4. **Backup configuration** - Store Grafana dashboards in version control

### Scaling Considerations
- **Long-term storage**: Consider Thanos or Cortex for scale
- **Multiple instances**: Prometheus federation for distributed systems
- **Alerting**: Add AlertManager for notification rules

## Security

### Metrics Security
- Basic authentication on all metrics endpoints
- Internal network communication only
- No sensitive data in metrics labels
- Environment variables for credentials

### Grafana Security
- Admin password via environment variables
- No anonymous access
- Sign-up disabled
- SSL/TLS recommended for production

## Integration with Services

### Adding Metrics to New Services
1. Add prometheus-client dependency
2. Create metrics endpoint with basic auth
3. Add service to Prometheus configuration
4. Create relevant dashboard panels

### Custom Business Metrics
Use the helper functions provided:
- `recordChatDuration()` - Track LLM interactions
- `recordRAGRetrieval()` - Track RAG performance
- `recordTaskCompletion()` - Track task completion
- `setActiveAgents()` - Track agent status

## Files Created/Modified

### New Files
- `prometheus/prometheus.yml` - Prometheus configuration
- `prometheus/grafana/provisioning/datasources/prometheus.yml` - Grafana datasource
- `prometheus/grafana/provisioning/dashboards/dashboards.yml` - Dashboard provisioning
- `prometheus/grafana/provisioning/dashboards/dashboards-json/*.json` - Dashboard definitions
- `suna/lib/metrics.js` - Node.js metrics library
- `suna/pages/api/metrics/index.js` - Metrics API endpoint
- `onyx-core/metrics/prometheus_metrics.py` - Python metrics library
- `scripts/test-monitoring.sh` - Monitoring test script

### Modified Files
- `docker-compose.yaml` - Added monitoring services and configuration
- `docs/monitoring-setup.md` - This documentation

## Next Steps

1. **Alerting**: Configure AlertManager for notifications
2. **Log Aggregation**: Add Loki for log collection
3. **Performance Monitoring**: Add distributed tracing
4. **Automation**: Integrate monitoring with CI/CD pipeline

This monitoring setup provides comprehensive visibility into the ONYX system, meeting all acceptance criteria for Story 9-1.