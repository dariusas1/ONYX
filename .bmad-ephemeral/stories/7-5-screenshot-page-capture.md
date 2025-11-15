# Story 7.5: Screenshot & Page Capture

**Status:** drafted
**Epic:** 7 - Web Automation & Search
**Priority:** Medium
**Estimated Effort:** 3-5 points (Medium)

---

## User Story

**As a** user
**I want** agent to capture screenshots of web pages
**So that** agent can document page states, capture visual information, and provide visual evidence of web interactions

---

## Acceptance Criteria

**AC 1:** Given agent invokes screenshot tool
When tool called with URL parameter
Then browser navigates and waits for page load completion

**AC 2:** Given page loaded completely
When screenshot capture initiates
Then full page screenshot captured (entire scrollHeight)

**AC 3:** Given screenshot captured
When processing image output
Then image returned as base64 or stored in Drive with URL

**AC 4:** Given resolution requirements
When configuring screenshot capture
Then resolution configurable (default: 1920x1080)

**AC 5:** Given performance requirements
When screenshot capture executes
Then execution time <5s for screenshot capture

**AC 6:** Given format requirements
When saving screenshot
Then supports PNG (lossless) and JPEG (smaller file size) formats

---

## Tasks & Subtasks

### Task 7.5.1: Screenshot Service Implementation
- Create ScreenshotService with Playwright integration
- Implement full-page screenshot capture (scrollHeight handling)
- Support multiple viewport configurations
- Handle image encoding and format conversion

### Task 7.5.2: Storage & Output Options
- Base64 encoding for direct response
- Google Drive integration for storage and sharing
- Configurable quality settings for JPEG compression
- Temporary file management and cleanup

### Task 7.5.3: Configuration & Customization
- Configurable resolution (default: 1920x1080)
- Mobile and tablet viewport presets
- PNG and JPEG format support
- Quality and compression settings

### Task 7.5.4: Screenshot Capture API
- Create API endpoint: POST /tools/screenshot_page
- Accept parameters: url, format, quality, resolution, store_in_drive
- Return image data or storage URL
- Performance optimization for <5s capture target

### Task 7.5.5: Error Handling & Security
- URL validation and malicious URL detection
- Timeout management and browser recovery
- Content filtering and safe browsing
- Rate limiting for screenshot requests

### Task 7.5.6: Testing & Validation
- Unit tests for screenshot service
- Integration tests with various page types
- Performance benchmarks (<5s capture)
- Security and content filtering tests

---

## Dev Notes

### Technical Implementation
- **Primary Technology:** Playwright (already in project from story 7.1)
- **API Design:** RESTful endpoint following agent tool pattern
- **Image Processing:** Base64 encoding, JPEG compression, PNG handling
- **Performance:** Target <5s for complete screenshot capture

### API Specification
```yaml
POST /tools/screenshot_page
Parameters:
  url: string (required) - Target page URL
  format: string (optional, default: 'png') - 'png' or 'jpeg'
  quality: number (optional, default: 80) - JPEG quality 1-100
  width: number (optional, default: 1920) - Viewport width
  height: number (optional, default: 1080) - Viewport height
  full_page: boolean (optional, default: true) - Capture entire page
  store_in_drive: boolean (optional, default: false) - Store in Google Drive

Response:
  success: boolean
  message: string
  image_data: string (base64, if not stored in Drive)
  drive_url: string (if stored in Drive)
  screenshot_size: number (bytes)
  page_title: string
  capture_time: number (milliseconds)
```

### Screenshot Capture Strategy
1. **Page Load:** Wait for network idle and DOM content loaded
2. **Viewport Setup:** Configure browser dimensions and device pixel ratio
3. **Full Page:** Handle scrollHeight with multiple screenshots if needed
4. **Encoding:** Convert to base64 or upload to Drive based on preference

### Error Handling Scenarios
- **Invalid URL:** Return validation error with malformed URLs
- **Page Timeout:** Return timeout error with retry suggestion
- **Blocked Content:** Return error for inaccessible or blocked pages
- **Browser Crash:** Automatic browser recovery and retry

### Integration Points
- **Story 7.1:** Reuse Playwright browser setup and management
- **Story 7.3:** Integrate with content extraction for page context
- **Story 7.4:** Use as audit trail for form interactions
- **Google Drive:** Leverage existing Drive integration from Epic 3

### Security Considerations
- Validate and sanitize URLs before navigation
- Detect and block malicious or inappropriate content
- Implement rate limiting for screenshot requests
- Respect robots.txt and website terms of service
- Filter sensitive information from screenshots if required

### Performance Optimization
- Efficient browser resource usage and cleanup
- Parallel processing for multiple screenshots
- Caching for repeated screenshot requests
- Optimized image encoding and compression

---

## Dependencies

### Prerequisites
- Story 7.1: Playwright Browser Setup & Headless Automation ✅ (completed)
- Story 1.1: Project Setup & Repository Initialization ✅ (completed)

### Optional Dependencies
- Story 3.2: Google Drive Connector & Auto-Sync ✅ (completed) - for Drive storage feature

### Blocking Stories
- None (can be developed in parallel with other Epic 7 stories)

---

## Success Metrics

- **Functional:** >95% successful screenshot capture on test pages
- **Performance:** <5s average capture time for standard web pages
- **Reliability:** <2% error rate on accessible websites
- **Quality:** Clear, readable screenshots with proper resolution

---

## Definition of Done

- [ ] Screenshot service working with Playwright integration
- [ ] Full-page screenshot capture implemented
- [ ] API endpoint implemented and tested
- [ ] PNG and JPEG format support working
- [ ] Configurable resolution and quality settings
- [ ] Google Drive integration working (optional)
- [ ] Error handling for timeouts and blocked pages
- [ ] Performance benchmarks met (<5s capture)
- [ ] Integration tests passing with sample pages
- [ ] Documentation updated with API specification
- [ ] Security review completed
- [ ] Story context generated and ready for development

---

**Created:** 2025-11-14
**Author:** BMAD System
**Status:** drafted → ready-for-dev (pending context generation)