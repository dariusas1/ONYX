# Story 6.2: Google Docs Creation Tools

Status: drafted

## Story

As an agent,
I want to create Google Docs with formatted content from my analysis,
so that I can generate strategic documents, reports, and insights that users can access, edit, and share through Google Workspace.

## Acceptance Criteria

1. **AC6.2.1**: Agent can invoke `create_google_doc` tool with title and content parameters
2. **AC6.2.2**: Google Doc created successfully in user's Google Drive with proper permissions
3. **AC6.2.3**: Content formatting preserved (headings, lists, bold, italics, links)
4. **AC6.2.4**: Markdown content properly converted to Google Docs format
5. **AC6.2.5**: Document accessible via shareable Google Docs URL returned to user
6. **AC6.2.6**: Document creation respects user's Google Drive folder structure
7. **AC6.2.7**: Error handling for permission issues, quota limits, and API failures
8. **AC6.2.8**: Performance target: document creation completes in <2 seconds
9. **AC6.2.9**: Document metadata tracked (creation time, agent, task context)
10. **AC6.2.10**: Integration with existing OAuth2 foundation for authentication

## Tasks / Subtasks

- [ ] Task 1: Google Docs API Integration (AC: 6.2.1, 6.2.7, 6.2.8, 6.2.10)
  - [ ] Subtask 1.1: Implement Google Docs API client service
  - [ ] Subtask 1.2: Add Docs API scopes to OAuth2 configuration
  - [ ] Subtask 1.3: Create document creation endpoint with authentication
  - [ ] Subtask 1.4: Implement comprehensive error handling
  - [ ] Subtask 1.5: Add performance monitoring and timing

- [ ] Task 2: Content Processing & Formatting (AC: 6.2.3, 6.2.4)
  - [ ] Subtask 2.1: Implement Markdown to Google Docs conversion
  - [ ] Subtask 2.2: Handle headings (H1-H6) with proper styling
  - [ ] Subtask 2.3: Process lists (ordered and unordered) correctly
  - [ ] Subtask 2.4: Convert text formatting (bold, italics, strikethrough)
  - [ ] Subtask 2.5: Handle links and references properly
  - [ ] Subtask 2.6: Support code blocks and inline code formatting

- [ ] Task 3: File Management & Permissions (AC: 6.2.2, 6.2.6, 6.2.9)
  - [ ] Subtask 3.1: Implement folder placement logic
  - [ ] Subtask 3.2: Handle Drive permission inheritance
  - [ ] Subtask 3.3: Create ONYX folder structure if needed
  - [ ] Subtask 3.4: Store document metadata in database
  - [ ] Subtask 3.5: Link document to original agent task

- [ ] Task 4: Agent Tool Integration (AC: 6.2.1, 6.2.5)
  - [ ] Subtask 4.1: Create agent tool interface for Google Docs creation
  - [ ] Subtask 4.2: Implement tool parameter validation
  - [ ] Subtask 4.3: Add shareable URL generation and return
  - [ ] Subtask 4.4: Integrate with agent approval gates system
  - [ ] Subtask 4.5: Add tool usage logging and audit trails

- [ ] Task 5: Testing & Validation (AC: All)
  - [ ] Subtask 5.1: Unit tests for Docs API integration
  - [ ] Subtask 5.2: Integration tests with Google Workspace
  - [ ] Subtask 5.3: End-to-end agent workflow testing
  - [ ] Subtask 5.4: Performance testing and optimization
  - [ ] Subtask 5.5: Error scenario testing and validation

## Dev Notes

- **OAuth2 Foundation**: Build upon existing OAuth2 implementation from Story 6.1
- **Google Docs API**: Use Google Docs API v1 for document creation and formatting
- **Content Processing**: Implement robust Markdown to Google Docs conversion
- **Error Handling**: Comprehensive error handling for Google API limitations
- **Performance**: Target <2s document creation time including formatting
- **Security**: Ensure proper permission handling and data privacy

### Project Structure Notes

- **Service Integration**: Extend `onyx-core/services/google_oauth.py` for Docs API
- **API Endpoints**: Add to existing `onyx-core/api/google_drive.py` router
- **Database**: Extend existing OAuth tables for document metadata tracking
- **Agent Tools**: Add to agent tool system alongside other Google Workspace tools
- **Configuration**: Update OAuth2 scopes to include Google Docs API access

### References

- [Source: docs/stories/6-1-oauth2-setup-integration.context.xml] - OAuth2 foundation implementation
- [Source: docs/epics.md#epic-6] - Epic 6 requirements and context
- [Source: docs/sprint-status.yaml] - Current sprint status and Epic 6 progress
- [Source: Google Docs API v1 documentation] - API reference for document operations
- [Source: Google Workspace authentication guides] - OAuth2 scope requirements

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List