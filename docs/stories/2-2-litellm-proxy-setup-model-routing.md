# Story 2.2: LiteLLM Proxy Setup & Model Routing

**Project:** ONYX (Manus Internal)
**Story ID:** 2-2-litellm-proxy-setup-model-routing
**Epic:** Epic 2 - Chat Interface & Core Intelligence
**Author:** Technical Architect
**Date:** 2025-11-14
**Version:** 1.0
**Status:** Drafted

---

## User Story

**As a** developer working on the ONYX chat system,
**I want** a unified LLM interface with DeepSeek as the primary model and Ollama as fallback,
**So that** the chat system has reliable, fault-tolerant LLM capabilities with automatic failover.

---

## Story Metadata

| Field | Value |
|-------|-------|
| **Priority** | P1 (High) |
| **Story Points** | 8 |
| **Sprint** | Sprint 2 |
| **Assigned To** | TBD |
| **Dependencies** | Epic 1 (Foundation & Infrastructure) |
| **Estimated Effort** | 1-2 days |
| **Risk Level** | Medium |
| **Complexity** | Medium |

---

## Technical Implementation Summary

This story implements a LiteLLM proxy service that provides a unified OpenAI-compatible interface for multiple LLM providers. The solution includes:

1. **LiteLLM Proxy Service** - Central routing and load balancing
2. **Primary Model** - DeepSeek via Together AI API
3. **Fallback Model** - Ollama with Mistral 7B Instruct
4. **Circuit Breaker Pattern** - Automatic failover and recovery
5. **Monitoring & Logging** - Comprehensive observability

---

## Detailed Implementation

### LiteLLM Configuration

```yaml
# litellm-config.yaml
model_list:
  - model_name: "manus-primary"
    litellm_params:
      model: "together_ai/deepseek-chat"
      api_key: "${TOGETHER_API_KEY}"
      max_tokens: 4096
      temperature: 0.7
      stream: true

  - model_name: "manus-fallback"
    litellm_params:
      model: "ollama/mistral:7b-instruct"
      api_base: "http://ollama:11434"
      stream: true

# Fallback routing configuration
router_settings:
  routing_strategy: "simple-fallback"
  allowed_fails: 3
  fallback_models: ["manus-fallback"]

# Rate limiting and monitoring
litellm_settings:
  success_callback: ["prometheus"]
  failure_callback: ["sentry"]
  rate_limit:
    rpm: 100
    tpm: 100000
```

### Docker Services

```yaml
# Additional services for docker-compose.yaml
services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:latest
    container_name: onyx-litellm
    ports:
      - "4000:4000"
    environment:
      TOGETHER_API_KEY: ${TOGETHER_API_KEY}
      LITELLM_CONFIG_PATH: /app/config.yaml
    volumes:
      - ./litellm-config.yaml:/app/config.yaml
    depends_on:
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: onyx-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Backend Integration

```typescript
// src/lib/llm-client.ts
import { OpenAI } from 'openai';

export const llmClient = new OpenAI({
  apiKey: 'dummy-key', // LiteLLM doesn't validate
  baseURL: 'http://litellm-proxy:4000',
});

export async function streamChatCompletion(
  messages: Array<{ role: string; content: string }>,
  onChunk: (chunk: string) => void,
  onError: (error: Error) => void
) {
  try {
    const stream = await llmClient.chat.completions.create({
      model: 'manus-primary',
      messages,
      stream: true,
      max_tokens: 4096,
      temperature: 0.7,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        onChunk(content);
      }
    }
  } catch (error) {
    console.error('LLM streaming error:', error);
    onError(error as Error);
  }
}
```

### Circuit Breaker Pattern

```typescript
// src/lib/circuit-breaker.ts
class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime = 0;
  private readonly failureThreshold = 3;
  private readonly resetTimeout = 60000; // 1 minute

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.isOpen()) {
      throw new Error('Circuit breaker is OPEN - using fallback');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private isOpen(): boolean {
    if (this.failureCount >= this.failureThreshold) {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      return timeSinceLastFailure < this.resetTimeout;
    }
    return false;
  }

  private onSuccess() {
    this.failureCount = 0;
  }

  private onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
  }
}
```

### Logging & Monitoring

```typescript
// Structured logging for LLM calls
interface LLMLogEntry {
  timestamp: string;
  model: string;
  tokens: {
    prompt: number;
    completion: number;
    total: number;
  };
  latency_ms: number;
  success: boolean;
  error?: string;
}

function logLLMCall(entry: LLMLogEntry) {
  console.log(JSON.stringify({
    level: 'info',
    service: 'llm-proxy',
    action: 'completion',
    ...entry,
  }));
}
```

---

## Acceptance Criteria

| AC ID | Criteria | Status |
|-------|----------|--------|
| **AC2.2.1** | LiteLLM proxy running on port 4000 with health check endpoint | ❌ To Do |
| **AC2.2.2** | DeepSeek requests route successfully through LiteLLM proxy | ❌ To Do |
| **AC2.2.3** | Ollama fallback activates when DeepSeek fails (3 failure threshold) | ❌ To Do |
| **AC2.2.4** | Streaming responses work end-to-end with <500ms first token latency | ❌ To Do |
| **AC2.2.5** | Rate limiting enforced (100 req/min per user) with monitoring | ❌ To Do |
| **AC2.2.6** | Structured logs include model, tokens, latency, and success/error status | ❌ To Do |

---

## Technical Requirements

### Environment Variables
```bash
# Required for this story
TOGETHER_API_KEY=sk-...                    # Together AI API key for DeepSeek
LITELLM_CONFIG_PATH=/app/config.yaml      # LiteLLM configuration path
OLLAMA_BASE_URL=http://ollama:11434       # Ollama service URL
```

### Performance Targets
- **First Token Latency**: <500ms (95th percentile)
- **Failover Time**: <3 seconds to activate fallback
- **Throughput**: >20 requests/second sustained
- **Availability**: >99.5% uptime with fallback

### Security Requirements
- API keys stored in Docker secrets or environment variables
- Rate limiting per user session
- Input validation and sanitization
- Audit logging for all LLM interactions

---

## Dependencies & Blockers

### Prerequisites (Must be Complete)
- [x] Epic 1 Technical Specification reviewed
- [ ] Epic 1 Implementation complete (Docker, Postgres, Redis, Nginx)
- [ ] Environment variables configured
- [ ] Docker Compose environment operational

### Blocked By
- **Epic 1**: Foundation & Infrastructure (critical path)
- Network connectivity between Docker containers
- API credentials provisioned

### Blocks
- **Story 2.4**: Message Streaming & Real-Time Response Display
- **Story 2.5**: System Prompt & Strategic Advisor Tone
- All subsequent chat functionality stories

---

## Testing Strategy

### Unit Tests
```typescript
// __tests__/lib/llm-client.test.ts
describe('streamChatCompletion', () => {
  it('streams response from primary model');
  it('handles streaming errors gracefully');
  it('validates message format');
});

// __tests__/lib/circuit-breaker.test.ts
describe('CircuitBreaker', () => {
  it('opens after failure threshold');
  it('resets after timeout');
  it('passes through successful calls');
});
```

### Integration Tests
- LiteLLM proxy health check
- DeepSeek API connectivity
- Ollama fallback activation
- End-to-end streaming test
- Rate limiting validation

### Performance Tests
- First token latency measurement
- Concurrent request handling
- Failover response time
- Memory usage under load

---

## Deployment Notes

### Pre-deployment Checklist
- [ ] TOGETHER_API_KEY configured and tested
- [ ] LiteLLM configuration validated
- [ ] Docker services health checks passing
- [ ] Network connectivity between services verified
- [ ] Monitoring dashboards configured

### Rollback Strategy
- Maintain previous Docker image tags
- Database schema changes are backward compatible
- Configuration versioning with Git
- Service health monitoring

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Primary Model Success Rate | >95% | LiteLLM logs |
| Fallback Activation Rate | <5% | Error tracking |
| First Token Latency | <500ms | Frontend timing |
| Streaming Throughput | >20 tokens/sec | Token count / duration |
| Service Uptime | >99.5% | Health checks |
| Error Rate | <1% | Failed requests / total |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| DeepSeek API outage | Medium | High | Ollama fallback, circuit breaker |
| Network latency to Together AI | Medium | Medium | Local Ollama caching |
| Rate limit exceeded | Low | Medium | Intelligent queuing |
| LiteLLM proxy crashes | Low | High | Docker restart policies, health checks |

---

## File Structure

```
/
├── litellm-config.yaml          # LiteLLM configuration
├── docker-compose.yaml          # Updated with new services
└── src/
    └── lib/
        ├── llm-client.ts        # OpenAI client integration
        ├── circuit-breaker.ts   # Failover logic
        └── monitoring.ts        # Logging and metrics
```

---

## Next Steps

1. **Immediate**: Configure environment variables
2. **Week 1**: Implement LiteLLM proxy and Ollama services
3. **Week 1**: Build backend integration and circuit breaker
4. **Week 1**: Add monitoring and logging
5. **Week 1**: Comprehensive testing and validation
6. **Week 1**: Deploy to staging environment

---

**Story Status:** Drafted - Ready for development assignment
**Last Updated:** 2025-11-14
**Next Review:** Sprint Planning