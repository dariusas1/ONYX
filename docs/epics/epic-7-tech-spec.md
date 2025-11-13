# Epic Technical Specification: Web Automation & Search

Date: 2025-11-13
Author: Technical Architect
Epic ID: epic-7
Status: Draft

---

## Overview

Epic 7 enables Manus Internal to perform autonomous web research, market analysis, and competitive intelligence through headless browser automation and intelligent web search. This epic implements Playwright-based browser automation, integration with premium search APIs (SerpAPI/Exa), content extraction from web pages, form interaction capabilities, and screenshot capture. Together, these capabilities transform Manus from an internal knowledge assistant into a comprehensive strategic intelligence platform capable of gathering external market data, analyzing competitor moves, and extracting insights from the broader web.

The web automation layer provides the foundation for agent-driven research workflows where Manus can autonomously search for information, navigate websites, extract relevant content, and compile comprehensive reports without human intervention beyond initial task specification and approval gates.

## Objectives and Scope

### In-Scope:
- **Playwright Browser Automation**: Headless Chrome/Firefox setup in Docker with full page interaction capabilities
- **Web Search Integration**: SerpAPI and Exa API integration for Google/Bing search with semantic search capabilities
- **Content Extraction**: Intelligent web scraping with Readability-based clean text extraction and Markdown conversion
- **Form Interaction**: Automated form filling with support for text inputs, selects, checkboxes, radio buttons
- **Screenshot Capture**: Full-page screenshot functionality with configurable resolution and format options
- **Rate Limiting & Caching**: Request throttling, result caching, and respectful web scraping practices
- **Error Handling**: Robust handling of timeouts, 404s, CAPTCHAs, and blocked requests

### Out-of-Scope:
- JavaScript-heavy single-page application (SPA) advanced interaction (defer to future enhancements)
- CAPTCHA solving automation (manual intervention required)
- Proxy rotation and IP management (single IP from VPS)
- Video/audio content extraction
- Browser session persistence across multiple tasks
- Advanced anti-bot detection circumvention
- Distributed browser pool (single browser instance for MVP)

## System Architecture Alignment

Epic 7 implements the web automation and search layer defined in the architecture document (Epic 7: Web Automation). This epic extends the Onyx Core Python service with new browser automation capabilities via Playwright, integrates external search APIs, and provides tools that the Agent Mode (Epic 5) can invoke for web-based research tasks. The web automation module operates as part of the tool ecosystem, enabling the LLM agent to autonomously gather external intelligence while maintaining approval gates for sensitive actions.

The browser automation runs in a dedicated Docker container with Playwright and headless browsers, communicating with the main Onyx Core service via internal APIs. Search operations utilize external APIs (SerpAPI/Exa) with caching to minimize costs. Content extraction leverages Mozilla's Readability algorithm for clean text extraction, and all operations include comprehensive logging for debugging and audit trails.

## Detailed Design

### Services and Modules

| Module | Purpose | Technology | Responsibilities | Integration Points |
|--------|---------|------------|------------------|-------------------|
| **playwright-service** | Browser automation | Playwright + Chrome | Page navigation, interaction, screenshots | Onyx Core → Playwright API |
| **search-service** | Web search | SerpAPI/Exa SDK | Query execution, result parsing, caching | Onyx Core → External APIs |
| **scraper-service** | Content extraction | Readability + Cheerio | HTML parsing, text extraction, Markdown conversion | Playwright → Scraper |
| **form-service** | Form interaction | Playwright selectors | Field detection, value injection, submission | Playwright → Form logic |
| **screenshot-service** | Page capture | Playwright screenshot API | Full-page capture, format conversion, storage | Playwright → Storage |
| **cache-layer** | Result caching | Redis | Search results, scraped content (24h TTL) | All services → Redis |
| **rate-limiter** | Request throttling | Redis + token bucket | API rate limiting, request queuing | All external calls |

### Service Architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Suna (Frontend) - Agent Mode UI                       │
└─────────────────┬───────────────────────────────────────┘
                  │ POST /api/agent (task submission)
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Onyx Core (Python) - Tool Orchestration               │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Tool Router: select_tool(task) → web_search      │ │
│  │             → scrape_url → fill_form → screenshot │ │
│  └───────────────────────────────────────────────────┘ │
└────┬─────────┬──────────┬──────────┬──────────────┬────┘
     │         │          │          │              │
     ↓         ↓          ↓          ↓              ↓
┌─────────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
│SerpAPI/ │ │Redis │ │Playwright│ │Scraper│ │Screenshot   │
│Exa API  │ │Cache │ │Browser   │ │Service│ │Service      │
└─────────┘ └──────┘ └────────┘ └────────┘ └──────────────┘
```

### Data Models and Contracts

#### Web Search Result Schema:
```python
class SearchResult(BaseModel):
    query: str
    source: Literal["serpapi", "exa"]
    results: List[SearchResultItem]
    total_results: int
    search_time_ms: int
    cached: bool
    timestamp: datetime

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str  # 100-200 chars
    position: int
    domain: str
    publish_date: Optional[datetime]
    relevance_score: Optional[float]  # Exa only
```

#### Scraped Content Schema:
```python
class ScrapedContent(BaseModel):
    url: str
    title: str
    author: Optional[str]
    publish_date: Optional[datetime]
    content_markdown: str
    content_text: str  # plain text
    word_count: int
    language: str
    metadata: Dict[str, Any]
    scrape_time_ms: int
    cached: bool
```

#### Form Interaction Schema:
```python
class FormFillRequest(BaseModel):
    url: str
    fields: Dict[str, str]  # {field_name: value}
    submit: bool = False
    wait_after_submit: int = 3000  # ms
    selector_strategy: Literal["name", "id", "label", "placeholder"] = "name"

class FormFillResult(BaseModel):
    success: bool
    fields_filled: List[str]
    fields_failed: List[str]
    result_url: Optional[str]
    result_content: Optional[str]
    screenshots: List[str]  # before/after
```

#### Screenshot Request Schema:
```python
class ScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True
    width: int = 1920
    height: int = 1080
    format: Literal["png", "jpeg", "pdf"] = "png"
    quality: int = 90  # for JPEG
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load"

class ScreenshotResult(BaseModel):
    url: str
    image_base64: Optional[str]
    image_url: Optional[str]  # if stored in Drive
    width: int
    height: int
    format: str
    file_size_bytes: int
```

### APIs and Interfaces

#### Tool API Endpoints (Onyx Core):

```python
# Web Search Tool
POST /tools/search_web
{
    "query": "Anthropic Claude 3 pricing",
    "source": "serpapi",  # or "exa"
    "time_range": "past_month",  # optional
    "num_results": 5
}

Response:
{
    "success": true,
    "data": {
        "query": "Anthropic Claude 3 pricing",
        "results": [
            {
                "title": "Claude 3 Pricing - Anthropic",
                "url": "https://www.anthropic.com/pricing",
                "snippet": "Claude 3 offers flexible pricing...",
                "position": 1,
                "domain": "anthropic.com"
            }
        ],
        "total_results": 127000,
        "search_time_ms": 450,
        "cached": false
    }
}

# URL Scraping Tool
POST /tools/scrape_url
{
    "url": "https://example.com/article",
    "format": "markdown",  # or "text", "html"
    "extract_metadata": true
}

Response:
{
    "success": true,
    "data": {
        "url": "https://example.com/article",
        "title": "How to Build AI Agents",
        "content_markdown": "# How to Build AI Agents\n\n...",
        "word_count": 2340,
        "author": "John Doe",
        "publish_date": "2025-11-01T00:00:00Z",
        "scrape_time_ms": 1200
    }
}

# Form Filling Tool
POST /tools/fill_form
{
    "url": "https://example.com/survey",
    "fields": {
        "name": "Manus",
        "email": "manus@m3rcury.com",
        "company": "M3rcury",
        "feedback": "Excellent product"
    },
    "submit": false,
    "selector_strategy": "label"
}

Response:
{
    "success": true,
    "data": {
        "fields_filled": ["name", "email", "company", "feedback"],
        "fields_failed": [],
        "result_url": "https://example.com/survey",
        "screenshots": ["base64_before", "base64_after"]
    }
}

# Screenshot Tool
POST /tools/screenshot
{
    "url": "https://example.com",
    "full_page": true,
    "format": "png"
}

Response:
{
    "success": true,
    "data": {
        "url": "https://example.com",
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
        "width": 1920,
        "height": 3840,
        "file_size_bytes": 245670
    }
}
```

#### Playwright Browser Manager API:

```python
class BrowserManager:
    async def navigate(self, url: str, wait_until: str = "load") -> Page
    async def extract_text(self, page: Page) -> str
    async def fill_field(self, page: Page, selector: str, value: str) -> bool
    async def click_element(self, page: Page, selector: str) -> bool
    async def screenshot(self, page: Page, full_page: bool = True) -> bytes
    async def close_page(self, page: Page) -> None
```

#### External API Integration:

**SerpAPI Search:**
```python
# Google Search via SerpAPI
GET https://serpapi.com/search
Params:
    q: {query}
    api_key: {SERPAPI_API_KEY}
    engine: google
    num: 5
    tbm: (optional: nws for news, isch for images)
```

**Exa AI Search:**
```python
# Semantic search via Exa
POST https://api.exa.ai/search
Headers:
    Authorization: Bearer {EXA_API_KEY}
Body:
{
    "query": "latest AI developments",
    "num_results": 5,
    "use_autoprompt": true,
    "type": "neural"  # semantic search
}
```

### Workflows and Sequencing

#### Web Search Workflow:
```
1. Agent receives task: "Research Anthropic Claude pricing"
2. Tool router selects: search_web
3. Check cache (Redis): key = "search:serpapi:anthropic_claude_pricing"
4. If cached → return cached results
5. If not cached:
   a. Call SerpAPI with query
   b. Parse results into SearchResult schema
   c. Cache results (TTL: 24h)
   d. Return to agent
6. Agent synthesizes results into response
```

#### URL Scraping Workflow:
```
1. Agent needs to read article content
2. Tool router selects: scrape_url
3. Check cache: key = "scrape:{url_hash}"
4. If not cached:
   a. Launch Playwright browser (headless)
   b. Navigate to URL (timeout: 10s)
   c. Wait for page load (networkidle or domcontentloaded)
   d. Extract HTML content
   e. Pass to Readability for cleaning
   f. Convert to Markdown
   g. Extract metadata (title, author, date)
   h. Cache result (TTL: 24h)
5. Return clean content to agent
6. Close browser page
```

#### Form Filling Workflow:
```
1. Agent task: "Fill out survey at URL"
2. Tool requires approval (sensitive action)
3. User approves via UI
4. scrape_url:
   a. Launch browser, navigate to URL
   b. Take "before" screenshot
   c. Identify form fields using selector strategy:
      - Try by 'name' attribute
      - Fallback to 'id'
      - Fallback to <label> text matching
      - Fallback to 'placeholder' text
   d. Fill each field with provided value
   e. Validate field populated correctly
   f. If submit=true: click submit button
   g. Wait for navigation/response
   h. Take "after" screenshot
5. Return result with screenshots
6. Close browser
```

#### Screenshot Workflow:
```
1. Agent needs visual record of page
2. Tool router selects: screenshot
3. Launch browser, navigate to URL
4. Wait for page load (configurable: load/networkidle)
5. If full_page=true:
   - Get full scrollHeight
   - Set viewport to capture entire page
6. Capture screenshot:
   - Format: PNG (lossless) or JPEG (smaller)
   - Quality: 90 (for JPEG)
7. Encode as base64 or upload to Drive
8. Return image data to agent
9. Close browser
```

#### Rate Limiting Strategy:
```
Token Bucket Algorithm (per API):
- SerpAPI: 100 searches/day → ~4/hour → 1 token every 15 min
- Exa: 1000 searches/month → ~33/day → 1 token every 45 min
- Browser automation: 3 concurrent max, queue excess

Implementation:
def acquire_token(service: str) -> bool:
    key = f"ratelimit:{service}"
    tokens = redis.get(key) or BUCKET_SIZE
    if tokens > 0:
        redis.decr(key)
        return True
    return False  # rate limited

Background job refills tokens every interval
```

## Non-Functional Requirements

### Performance

#### Browser Operations:
- **Page Load**: <5s for 95th percentile (timeout: 10s)
- **Screenshot**: <3s for full-page capture
- **Form Fill**: <5s for typical form (5-10 fields)
- **Scraping**: <5s from navigation to clean content
- **Browser Startup**: <2s (reuse browser context when possible)

#### Search Operations:
- **SerpAPI**: <2s for search results (external API)
- **Exa**: <3s for semantic search (external API)
- **Cache Hit**: <50ms for cached results
- **Result Parsing**: <100ms for 10 results

#### Resource Management:
- **Memory**: Single browser instance: <500MB RAM
- **CPU**: <30% during page load, <10% idle
- **Concurrent Browsers**: Max 1 instance (serial execution)
- **Cache Size**: Max 1GB for scraped content (Redis LRU eviction)

#### Throughput:
- **Web Searches**: 100/day (SerpAPI limit)
- **URL Scraping**: Unlimited (respectful rate limiting per domain)
- **Screenshots**: 50/day (to avoid storage bloat)
- **Form Fills**: 20/day (sensitive action limit)

### Security

#### Browser Isolation:
- Headless browser runs in dedicated Docker container
- No access to host filesystem beyond mounted volumes
- JavaScript execution sandboxed within browser context
- Cookies/storage cleared after each session

#### Credential Protection:
- API keys (SerpAPI, Exa) stored encrypted in environment variables
- No API keys logged or exposed in error messages
- Browser automation credentials (if any) encrypted at rest
- User input sanitized before injection into forms

#### Safe Browsing:
- URL validation before navigation (block known malicious domains)
- SSL certificate verification enabled
- Timeout enforcement to prevent long-running requests
- Content-type validation (no executable downloads)

#### Data Privacy:
- Scraped content cached with user_id isolation
- Screenshots stored with access control
- Search history logged for audit but not shared
- No telemetry sent to external services

### Reliability/Availability

#### Error Handling:
- **Network Failures**: Retry with exponential backoff (3 attempts)
- **Timeouts**: Hard timeout at 10s for page load, 30s for full operation
- **404/500 Errors**: Return structured error, don't crash
- **CAPTCHA Detection**: Return error with manual intervention request
- **Blocked Requests**: Detect anti-bot measures, return error gracefully

#### Fallback Strategies:
- If SerpAPI fails → try Exa
- If Exa fails → return cached results (if available)
- If browser fails → return text-only scrape (no JS rendering)
- If screenshot fails → return error but continue task

#### Resource Cleanup:
- Always close browser pages after operation
- Clear browser cache after each session
- Release memory with page.close() and context.close()
- Monitor for zombie browser processes

#### Circuit Breaker:
- If SerpAPI fails 3 times consecutively → disable for 5 minutes
- If browser crashes 5 times → disable web automation for 10 minutes
- Alert ops team if circuit breaker triggered

### Observability

#### Logging:
```json
// Web search log
{
  "timestamp": "2025-11-13T10:30:00Z",
  "level": "info",
  "service": "search-service",
  "action": "web_search_completed",
  "query": "anthropic claude pricing",
  "source": "serpapi",
  "results_count": 5,
  "cached": false,
  "latency_ms": 450,
  "user_id": "uuid"
}

// URL scrape log
{
  "timestamp": "2025-11-13T10:31:00Z",
  "level": "info",
  "service": "scraper-service",
  "action": "url_scrape_completed",
  "url": "https://example.com/article",
  "word_count": 2340,
  "latency_ms": 1200,
  "cached": false,
  "user_id": "uuid"
}

// Browser error log
{
  "timestamp": "2025-11-13T10:32:00Z",
  "level": "error",
  "service": "playwright-service",
  "action": "page_load_timeout",
  "url": "https://slow-site.com",
  "error": "TimeoutError: Navigation timeout of 10000ms exceeded",
  "user_id": "uuid"
}
```

#### Metrics:
- **Search API Usage**: Counters for SerpAPI/Exa calls (track quota)
- **Cache Hit Rate**: Cache hits / total requests (target: >70%)
- **Browser Latency**: p50, p95, p99 for page loads
- **Error Rate**: Errors / total operations (target: <5%)
- **Scrape Success Rate**: Successful scrapes / attempts (target: >90%)

#### Health Monitoring:
- Browser health: Can launch and navigate to google.com
- SerpAPI health: Test query returns results
- Exa health: Test query returns results
- Cache health: Redis ping responds

## Dependencies and Integrations

### External Dependencies:
| Service | Version | Purpose | Cost/Limits |
|---------|---------|---------|-------------|
| **SerpAPI** | v1 | Google/Bing search | $50/month (100 searches/day) |
| **Exa AI** | v1 | Semantic search | $20/month (1000 searches/month) |
| **Playwright** | 1.40+ | Browser automation | Free, self-hosted |
| **Readability** | 0.5+ | Content extraction | Free, self-hosted |
| **Cheerio** | 1.0+ | HTML parsing | Free, Node.js library |
| **Redis** | 7.0+ | Result caching | Self-hosted (Epic 1) |

### Internal Service Dependencies:
```
Epic 7 (Web Automation) depends on:
├── Epic 1 (Foundation) → Docker environment, Redis cache
├── Epic 5 (Agent Mode) → Tool selection, approval gates
└── Epic 2 (Chat) → Task submission interface

Epic 7 enables:
├── Epic 5 (Agent Mode) → External research tools
└── Epic 6 (Google Workspace) → Web-sourced content for docs
```

### Integration Points:
- **Onyx Core**: Web automation tools registered in tool registry
- **Agent Mode**: Tool selection logic routes web tasks correctly
- **Approval Gates**: Form fills and sensitive actions require approval
- **Task History**: All web operations logged to task execution history
- **Memory Layer**: Search results can be stored as memories

### Python Package Dependencies:
```python
# requirements.txt additions for Epic 7
playwright==1.40.0
beautifulsoup4==4.12.0
readability-lxml==0.8.1
html2text==2020.1.16
requests==2.31.0
aiohttp==3.9.0
serpapi==0.1.5
exa-py==1.0.0  # Exa SDK
pillow==10.1.0  # Image processing
```

### Docker Container Configuration:
```yaml
# docker-compose.yaml additions
services:
  playwright:
    image: mcr.microsoft.com/playwright/python:v1.40.0
    volumes:
      - ./onyx-core:/app
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
    command: python -m playwright install chromium
```

## Acceptance Criteria (Authoritative)

### Story 7.1: Playwright Browser Setup & Headless Automation
- **AC7.1.1**: Playwright browser starts without GUI in Docker container
- **AC7.1.2**: Browser can navigate to URLs and interact with pages (<3s load time)
- **AC7.1.3**: Supports screenshots and data extraction from rendered pages
- **AC7.1.4**: Performance: page load <3s, interaction <1s for typical sites
- **AC7.1.5**: Max 1 browser instance active (serial execution, no parallel browsers)
- **AC7.1.6**: Browser cleanup: all pages closed after operations complete

### Story 7.2: Web Search Tool (SerpAPI or Exa)
- **AC7.2.1**: Agent can invoke search_web tool with query parameter
- **AC7.2.2**: Returns top-5 results with title, URL, snippet, domain, position
- **AC7.2.3**: Results from Google/Bing via SerpAPI or semantic search via Exa
- **AC7.2.4**: Latency <3s for search API calls (external dependency)
- **AC7.2.5**: Supports time range filtering (past week/month/year)
- **AC7.2.6**: Results cached for 24h to minimize API costs

### Story 7.3: URL Scraping & Content Extraction
- **AC7.3.1**: Agent can invoke scrape_url tool with URL parameter
- **AC7.3.2**: Page loaded and HTML rendered (handles JavaScript)
- **AC7.3.3**: HTML cleaned (remove ads, scripts, navigation) using Readability
- **AC7.3.4**: Main content extracted and converted to Markdown
- **AC7.3.5**: Execution time <5s from navigation to clean content
- **AC7.3.6**: Returns text_content, metadata (title, author, publish_date)
- **AC7.3.7**: Error handling: 404s, timeouts, blocked sites return structured errors

### Story 7.4: Form Filling & Web Interaction
- **AC7.4.1**: Agent can invoke fill_form tool with URL and field values
- **AC7.4.2**: Browser navigates to page and finds form fields
- **AC7.4.3**: Handles text inputs, select dropdowns, checkboxes, radio buttons
- **AC7.4.4**: Can fill form without submission or submit and capture result
- **AC7.4.5**: Returns success/failure status and list of fields filled/failed
- **AC7.4.6**: Execution time <5s for typical forms (5-10 fields)
- **AC7.4.7**: Screenshots captured before/after form interaction for audit

### Story 7.5: Screenshot & Page Capture
- **AC7.5.1**: Agent can invoke screenshot tool with URL parameter
- **AC7.5.2**: Browser navigates and waits for page load completion
- **AC7.5.3**: Full page screenshot captured (entire scrollHeight)
- **AC7.5.4**: Image returned as base64 or stored in Drive with URL
- **AC7.5.5**: Resolution configurable (default: 1920x1080)
- **AC7.5.6**: Execution time <5s for screenshot capture
- **AC7.5.7**: Supports PNG (lossless) and JPEG (smaller file size) formats

## Traceability Mapping

| Acceptance Criteria | Spec Section | Component/Service | Test Strategy |
|-------------------|--------------|-------------------|---------------|
| AC7.1.1 | Services and Modules | Playwright Docker container | Integration: browser launch test |
| AC7.1.2 | Performance | Browser operations | Integration: navigation timing |
| AC7.1.3 | APIs and Interfaces | Playwright API | Unit: screenshot/data extraction |
| AC7.1.4 | Performance | Browser latency targets | Load test: p95 latency measurement |
| AC7.1.5 | Services and Modules | Browser instance management | Integration: concurrent limit test |
| AC7.1.6 | Reliability | Resource cleanup | Integration: memory leak detection |
| AC7.2.1 | APIs and Interfaces | Search tool API | Unit: tool invocation |
| AC7.2.2 | Data Models | SearchResult schema | Unit: response parsing |
| AC7.2.3 | External Dependencies | SerpAPI/Exa integration | Integration: API call verification |
| AC7.2.4 | Performance | Search latency | Integration: API timing |
| AC7.2.5 | APIs and Interfaces | Search filters | Unit: time range parameter |
| AC7.2.6 | Performance | Redis caching | Integration: cache hit verification |
| AC7.3.1 | APIs and Interfaces | Scrape tool API | Unit: tool invocation |
| AC7.3.2 | Workflows | Scraping workflow | Integration: JS rendering test |
| AC7.3.3 | External Dependencies | Readability library | Unit: content cleaning |
| AC7.3.4 | Data Models | ScrapedContent schema | Unit: Markdown conversion |
| AC7.3.5 | Performance | Scraping latency | Integration: end-to-end timing |
| AC7.3.6 | Data Models | Metadata extraction | Unit: metadata parsing |
| AC7.3.7 | Reliability | Error handling | Unit: error case coverage |
| AC7.4.1 | APIs and Interfaces | Form fill tool API | Unit: tool invocation |
| AC7.4.2 | Workflows | Form filling workflow | Integration: field detection |
| AC7.4.3 | Services and Modules | Form service | Unit: field type support |
| AC7.4.4 | APIs and Interfaces | Submit parameter | Integration: form submission |
| AC7.4.5 | Data Models | FormFillResult schema | Unit: result structure |
| AC7.4.6 | Performance | Form fill latency | Integration: timing verification |
| AC7.4.7 | Security | Audit screenshots | Integration: screenshot capture |
| AC7.5.1 | APIs and Interfaces | Screenshot tool API | Unit: tool invocation |
| AC7.5.2 | Workflows | Screenshot workflow | Integration: page load wait |
| AC7.5.3 | Services and Modules | Screenshot service | Unit: full-page capture |
| AC7.5.4 | Data Models | ScreenshotResult schema | Unit: base64/URL response |
| AC7.5.5 | APIs and Interfaces | Resolution configuration | Unit: dimension parameters |
| AC7.5.6 | Performance | Screenshot latency | Integration: capture timing |
| AC7.5.7 | Services and Modules | Format support | Unit: PNG/JPEG conversion |

## Risks, Assumptions, Open Questions

### Risks:
| Risk | Severity | Mitigation |
|------|----------|------------|
| **SerpAPI/Exa API quota exhaustion** | High | Implement aggressive caching (24h TTL), rate limiting, fallback between APIs |
| **Anti-bot detection blocking scrapes** | Medium | Use respectful user-agent, rate limiting per domain, manual intervention for sensitive sites |
| **Playwright browser memory leaks** | Medium | Always close pages/contexts, monitor memory usage, restart browser daily |
| **CAPTCHA blocking form fills** | Medium | Detect CAPTCHAs, request manual intervention, document unsupported sites |
| **Slow page load timeouts** | Low | Set reasonable timeouts (10s), retry once, return partial results |
| **Screenshot storage costs** | Low | Limit screenshots to 50/day, compress as JPEG, store in Drive with auto-pruning |

### Assumptions:
- SerpAPI and Exa APIs remain available and maintain current pricing
- Playwright supports latest Chrome/Firefox versions
- Redis cache has sufficient capacity for scraped content
- VPS has adequate resources for single browser instance
- Most target websites don't employ aggressive anti-bot measures
- CAPTCHA manual intervention is acceptable for MVP

### Open Questions:
- **Q1**: Should we support proxy rotation for IP diversity?
  **A**: No for MVP (single VPS IP), defer to future enhancement

- **Q2**: How to handle JavaScript-heavy SPAs (React/Vue)?
  **A**: Playwright handles basic SPA rendering; complex interactions defer to manual

- **Q3**: Should screenshots be stored in Drive or local storage?
  **A**: Drive for MVP (leverage existing integration), with base64 fallback

- **Q4**: What's the policy for scraping rate limits per domain?
  **A**: Default 1 request/5s per domain, configurable per use case

- **Q5**: Should we implement distributed browser pool for concurrency?
  **A**: No for MVP (serial execution sufficient), consider for scale

### Next Steps for Risk Mitigation:
1. Implement SerpAPI → Exa fallback logic with automatic switching
2. Create allowlist/blocklist for known anti-bot sites
3. Add browser memory monitoring with automatic restart threshold
4. Document CAPTCHA detection and manual intervention workflow
5. Set up screenshot storage policy with auto-pruning after 30 days

## Test Strategy Summary

### Testing Levels:
1. **Unit Tests**: Individual tool functions, response parsing, error handling
2. **Integration Tests**: End-to-end tool execution, API integration, caching
3. **Load Tests**: Browser performance under load, API rate limiting
4. **Manual Verification**: Visual inspection of screenshots, form fills, content quality

### Test Environment:
- **Local**: Docker Compose with Playwright container
- **CI**: GitHub Actions with browser automation support
- **Staging**: Test against real websites (ethical, robots.txt compliant)

### Key Test Scenarios:

```python
# Test 1: Web Search
def test_web_search_serpapi():
    result = search_web(query="test query", source="serpapi")
    assert result.success == True
    assert len(result.data.results) <= 5
    assert result.data.search_time_ms < 3000

# Test 2: URL Scraping
def test_url_scraping():
    result = scrape_url(url="https://example.com")
    assert result.success == True
    assert len(result.data.content_markdown) > 0
    assert result.data.scrape_time_ms < 5000

# Test 3: Form Filling
def test_form_fill():
    result = fill_form(
        url="https://httpbin.org/forms/post",
        fields={"custname": "Test", "custtel": "123"},
        submit=False
    )
    assert result.success == True
    assert "custname" in result.data.fields_filled

# Test 4: Screenshot Capture
def test_screenshot():
    result = screenshot(url="https://example.com")
    assert result.success == True
    assert len(result.data.image_base64) > 1000
    assert result.data.width == 1920

# Test 5: Cache Hit
def test_search_cache():
    # First call (cache miss)
    result1 = search_web(query="cached query")
    assert result1.data.cached == False

    # Second call (cache hit)
    result2 = search_web(query="cached query")
    assert result2.data.cached == True
    assert result2.data.search_time_ms < 100

# Test 6: Error Handling
def test_scrape_404():
    result = scrape_url(url="https://example.com/nonexistent")
    assert result.success == False
    assert "404" in result.error.message

# Test 7: Rate Limiting
def test_rate_limiting():
    # Exceed rate limit
    for i in range(10):
        result = search_web(query=f"query {i}")

    # Next call should be rate limited
    result = search_web(query="rate limited query")
    assert result.success == False
    assert "rate limit" in result.error.message.lower()
```

### Test Coverage Requirements:
- **Web Search**: 100% of SerpAPI and Exa integration code
- **URL Scraping**: 90% coverage (edge cases for complex sites)
- **Form Filling**: 85% coverage (many site-specific edge cases)
- **Screenshots**: 95% coverage (straightforward functionality)
- **Error Handling**: 100% of error paths

### Success Criteria:
- All 5 web automation tools working end-to-end
- Web searches return results in <3s (95th percentile)
- URL scraping succeeds for >90% of standard websites
- Form filling succeeds for >80% of common form patterns
- Screenshots captured within 5s for typical pages
- Cache hit rate >70% for repeated queries
- Error rate <5% for well-formed requests

### Test Automation:
- GitHub Actions runs integration tests on each PR
- Daily automated tests against live websites (ethical scraping)
- Weekly browser performance benchmarking
- Monthly API quota usage monitoring and alerting

---

## Implementation Notes

### Story Implementation Order:
1. **Story 7.1** (Playwright Setup) - Foundation for all browser operations
2. **Story 7.2** (Web Search) - Independent of browser, enables research
3. **Story 7.3** (URL Scraping) - Depends on 7.1, core content extraction
4. **Story 7.4** (Form Filling) - Depends on 7.1, advanced interaction
5. **Story 7.5** (Screenshot) - Depends on 7.1, visual capture

### Development Checklist:
- [ ] Docker container with Playwright and browsers configured
- [ ] SerpAPI and Exa API keys obtained and secured
- [ ] Redis caching layer configured with proper TTLs
- [ ] Rate limiting implemented with token bucket algorithm
- [ ] All 5 tools registered in Agent Mode tool registry
- [ ] Approval gates configured for form fills
- [ ] Error handling and logging comprehensive
- [ ] Integration tests passing for all tools
- [ ] Documentation updated with tool usage examples

### Production Readiness:
- [ ] API quota monitoring alerts configured
- [ ] Browser memory monitoring with auto-restart
- [ ] Cache eviction policy tested and verified
- [ ] Screenshot storage limits enforced
- [ ] Respectful scraping practices documented
- [ ] robots.txt compliance verification
- [ ] User-agent identification configured
- [ ] Manual intervention workflow for CAPTCHAs documented

---

**Epic 7 Technical Specification - Complete**

_This specification provides the authoritative design for implementing web automation and search capabilities in Manus Internal, enabling autonomous market research, competitive intelligence gathering, and external knowledge acquisition._
