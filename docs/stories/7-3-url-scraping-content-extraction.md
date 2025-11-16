# Story 7.3: URL Scraping & Content Extraction

Status: drafted

## Story

As a research agent,
I want to scrape and extract clean content from web pages,
so that I can access and process the main content of articles and documents for analysis and knowledge acquisition.

## Acceptance Criteria

1. **AC7.3.1**: Agent can invoke scrape_url tool with URL parameter
2. **AC7.3.2**: Page loaded and HTML rendered (handles JavaScript)
3. **AC7.3.3**: HTML cleaned (remove ads, scripts, navigation) using Readability
4. **AC7.3.4**: Main content extracted and converted to Markdown
5. **AC7.3.5**: Execution time <5s from navigation to clean content
6. **AC7.3.6**: Returns text_content, metadata (title, author, publish_date)
7. **AC7.3.7**: Error handling: 404s, timeouts, blocked sites return structured errors

## Tasks / Subtasks

- [ ] Task 1: Implement scrape_url tool API endpoint (AC: 7.3.1, 7.3.5, 7.3.6, 7.3.7)
  - [ ] Subtask 1.1: Create scrape_url tool registration in Onyx Core tool registry
  - [ ] Subtask 1.2: Implement /tools/scrape_url API endpoint with request/response validation
  - [ ] Subtask 1.3: Add ScrapedContent schema validation and response formatting
  - [ ] Subtask 1.4: Implement comprehensive error handling for all failure scenarios
  - [ ] Subtask 1.5: Add performance timing and latency monitoring

- [ ] Task 2: Build content extraction service with Readability (AC: 7.3.2, 7.3.3, 7.3.4)
  - [ ] Subtask 2.1: Integrate Mozilla Readability library for content cleaning
  - [ ] Subtask 2.2: Implement HTML preprocessing (remove ads, scripts, navigation)
  - [ ] Subtask 2.3: Add Markdown conversion using html2text or similar library
  - [ ] Subtask 2.4: Implement metadata extraction (title, author, publish_date)
  - [ ] Subtask 2.5: Add language detection and word count calculation

- [ ] Task 3: Implement browser automation integration (AC: 7.3.2, 7.3.5)
  - [ ] Subtask 3.1: Integrate with existing Playwright browser manager from Story 7.1
  - [ ] Subtask 3.2: Implement page navigation with proper wait conditions
  - [ ] Subtask 3.3: Add JavaScript rendering support for dynamic content
  - [ ] Subtask 3.4: Implement timeout handling and page cleanup
  - [ ] Subtask 3.5: Add performance optimization for sub-5s execution target

- [ ] Task 4: Add caching and rate limiting (Performance & Resource Management)
  - [ ] Subtask 4.1: Implement Redis caching for scraped content with 24h TTL
  - [ ] Subtask 4.2: Add cache key generation based on URL hash
  - [ ] Subtask 4.3: Implement respectful rate limiting per domain
  - [ ] Subtask 4.4: Add cache hit/miss metrics and monitoring

- [ ] Task 5: Comprehensive testing and validation (All ACs)
  - [ ] Subtask 5.1: Unit tests for content extraction and metadata parsing
  - [ ] Subtask 5.2: Integration tests for end-to-end scraping workflow
  - [ ] Subtask 5.3: Performance tests to verify <5s execution time
  - [ ] Subtask 5.4: Error case testing (404s, timeouts, blocked sites)
  - [ ] Subtask 5.5: JavaScript rendering tests with dynamic content sites

## Dev Notes

### Architecture Integration
This story extends the web automation layer established in Story 7.1 (Playwright Browser Setup) and implements the content extraction capabilities defined in Epic 7 Technical Specification [Source: docs/epics/epic-7-tech-spec.md#Services-and-Modules]. The scraper-service will integrate with the existing Playwright browser manager and provide clean content extraction for the Agent Mode tool ecosystem.

### Key Components
- **scraper-service**: Main content extraction service using Readability and HTML parsing
- **Browser Manager Integration**: Leverage existing Playwright setup from Story 7.1 for page navigation
- **Content Cleaning**: Mozilla Readability algorithm for removing ads, scripts, navigation
- **Markdown Conversion**: Convert cleaned HTML to readable Markdown format
- **Metadata Extraction**: Parse title, author, publish_date from HTML metadata
- **Cache Layer**: Redis integration for 24h content caching to minimize repeated requests

### Project Structure Notes
- **Tool Registration**: Register scrape_url in Onyx Core tool registry alongside search_web
- **API Consistency**: Follow same request/response pattern as other web automation tools
- **Service Location**: Implement scraper-service in onyx-core/services/web_automation/
- **Configuration**: Extend existing web automation configuration for scraper settings
- **Testing**: Add scraper tests to existing web automation test suite

### Performance Requirements
- **Execution Time**: <5s from navigation to clean content (95th percentile)
- **Page Load Timeout**: 10s hard timeout with graceful fallback
- **Memory Usage**: Leverage single browser instance from Story 7.1
- **Cache Hit Target**: >70% cache hit rate for repeated URLs
- **Error Rate**: <5% failure rate for well-formed requests

### Dependencies
- **Story 7.1**: Depends on Playwright browser setup for page navigation and JavaScript rendering [Source: docs/sprint-status.yaml#story-7-1]
- **Epic 1**: Uses Redis cache layer from foundation infrastructure
- **Epic 5**: Integrates with Agent Mode tool registry and approval system

### References
- [Source: docs/epics/epic-7-tech-spec.md#Acceptance-Criteria-Story-73] - Complete acceptance criteria and technical requirements
- [Source: docs/epics/epic-7-tech-spec.md#Data-Models-and-Contracts] - ScrapedContent schema and API contracts
- [Source: docs/epics/epic-7-tech-spec.md#Workflows-and-Sequencing] - URL scraping workflow implementation
- [Source: docs/epics/epic-7-tech-spec.md#External-Dependencies] - Readability library and HTML parsing dependencies
- [Source: docs/sprint-status.yaml#story-7-3] - Current story status and dependencies

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->
Context XML generated: `/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX/docs/stories/7-3-url-scraping-content-extraction.context.xml`

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List