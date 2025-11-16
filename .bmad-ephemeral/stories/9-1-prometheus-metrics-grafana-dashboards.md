# Story 9.1: Prometheus Metrics & Grafana Dashboards

Status: drafted

## Story

As a ops engineer,
I want Prometheus scraping metrics and Grafana displaying dashboards,
so that I can see system health, latency, and resource usage.

## Acceptance Criteria

1. AC9.1.1: Prometheus successfully scrapes metrics from all 6 core services (Suna, Onyx, Qdrant, Supabase, Redis, LiteLLM) at 15-second intervals
2. AC9.1.2: Grafana displays 5 operational dashboards (System Overview, Application Performance, LLM Metrics, RAG Performance, Infrastructure Health) updating every 10 seconds
3. AC9.1.3: Metrics endpoint response time <10ms (p95) across all services
4. AC9.1.4: Grafana dashboards accessible at http://localhost:3001 with authentication

## Tasks / Subtasks

- [ ] Task 1: Enhance Prometheus configuration (AC: 9.1.1, 9.1.3)
  - [ ] Subtask 1.1: Configure Prometheus scraping for all 6 core services at 15s intervals
  - [ ] Subtask 1.2: Implement custom metrics exporters for business metrics
  - [ ] Subtask 1.3: Add metrics middleware to track request latency and error rates
  - [ ] Subtask 1.4: Verify metrics endpoint response time <10ms (p95)

- [ ] Task 2: Create Grafana dashboards (AC: 9.1.2, 9.1.4)
  - [ ] Subtask 2.1: Set up Grafana authentication and access control
  - [ ] Subtask 2.2: Create System Overview dashboard (CPU, memory, disk usage)
  - [ ] Subtask 2.3: Create Application Performance dashboard (latency, error rates, throughput)
  - [ ] Subtask 2.4: Create LLM Metrics dashboard (call duration, success rates, model performance)
  - [ ] Subtask 2.5: Create RAG Performance dashboard (retrieval latency, vector search metrics)
  - [ ] Subtask 2.6: Create Infrastructure Health dashboard (service status, container health)
  - [ ] Subtask 2.7: Configure dashboard refresh to 10 seconds

- [ ] Task 3: Integration testing and validation (AC: All)
  - [ ] Subtask 3.1: Test Prometheus scraping from all services
  - [ ] Subtask 3.2: Verify Grafana dashboard accessibility and authentication
  - [ ] Subtask 3.3: Validate dashboard data accuracy and refresh rates
  - [ ] Subtask 3.4: Performance testing of metrics collection overhead

## Dev Notes

### Technical Context

This story enhances the existing Prometheus/Grafana setup mentioned in the sprint status notes. The monitoring infrastructure must work within the KVM 4 resource constraints (4 vCPU, 16GB RAM) and integrate with the existing Docker Compose multi-service architecture.

**Key Integration Points:**
- Leverages existing `/metrics` endpoints from Suna (Next.js), Onyx Core (Python), LiteLLM proxy, and infrastructure services
- Uses existing Docker network (`manus-network`) for service discovery and secure internal communication
- Must maintain single-VPS deployment simplicity
- Cannot impact existing service latency or functionality

### Metrics Schema Requirements

Based on the Epic 9 technical spec, the following metrics should be implemented:

```yaml
# Prometheus metrics format
onyx_chat_duration_seconds:
  type: histogram
  labels: [model, user_id, success]
  buckets: [0.1, 0.5, 1.0, 1.5, 2.0, 5.0]

onyx_rag_retrieval_duration_seconds:
  type: histogram
  labels: [vector_count, similarity_threshold]
  buckets: [0.05, 0.1, 0.2, 0.5, 1.0]

onyx_task_completion_total:
  type: counter
  labels: [task_type, success, duration_category]

onyx_active_agents:
  type: gauge
  labels: [agent_type, status]
```

### Performance Requirements

- Metrics collection overhead: <5% CPU overhead to monitored services
- Metrics endpoint response time: <10ms (p95)
- Grafana dashboard loading time: <2 seconds
- Prometheus scraping interval: 15 seconds
- Grafana dashboard refresh: 10 seconds

### Security Requirements

- Metrics endpoints require basic authentication (admin/admin)
- Grafana access restricted to internal IP ranges
- No PII stored in metrics or logs
- Sentry DSN stored in environment variables (encrypted in .env)

### Project Structure Notes

- **Docker Integration**: All monitoring services must integrate with existing Docker Compose setup
- **Network Configuration**: Use existing `manus-network` for service communication
- **Resource Constraints**: Must fit within existing KVM 4 resource allocation
- **Service Discovery**: Leverage existing Docker service definitions for Prometheus targets

### Dependencies

- **Epic 1**: Foundation & Infrastructure (completed)
- **Existing Services**: Suna, Onyx, Qdrant, Supabase, Redis, LiteLLM
- **Infrastructure**: Docker Compose, Nginx reverse proxy

### References

- [Source: docs/epics/epic-9-tech-spec.md#Services-and-Modules]
- [Source: docs/epics/epic-9-tech-spec.md#Acceptance-Criteria-Authoritative]
- [Source: docs/epics.md#Epic-9-Monitoring-DevOps-Launch]
- [Source: docs/sprint-status.yaml#Epic-9]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (model ID: 'claude-sonnet-4-5-20250929')

### Debug Log References

### Completion Notes List

### File List