# Epic Technical Specification: Google Workspace Tools

Date: 2025-11-15
Author: darius
Epic ID: epic-6
Status: Draft

---

## Overview

This technical specification defines the implementation architecture for Google Workspace Tools integration within the ONYX (Manus Internal) strategic intelligence system. The epic builds upon the existing OAuth2 foundation (70% complete) to provide comprehensive document creation, editing, and management capabilities for autonomous agent workflows.

**Current State**: OAuth2 authentication infrastructure is complete and operational. The remaining work focuses on implementing Google Docs API integration, Google Sheets API integration, comprehensive error handling, rate limiting, and seamless integration with the existing ONYX architecture.

**Target Completion**: Enable autonomous agents to create, edit, and manage Google Workspace documents as part of multi-step strategic workflows, with full permission awareness and audit capabilities.

## Objectives and Scope

### In-Scope Components:
- **Google Docs API Integration**: Create, read, update, and format Google Docs documents
- **Google Sheets API Integration**: Create, read, update, and manipulate Google Sheets with advanced formatting
- **Enhanced File Management**: Drive file listing, organization, and permission-aware operations
- **Content Processing**: Automated document summarization and content extraction
- **Error Handling & Resilience**: Comprehensive error handling, retry logic, and rate limiting
- **Security & Audit**: Full audit logging, permission validation, and secure credential management
- **Integration Layer**: Seamless integration with existing ONYX agent tool ecosystem

### Out-of-Scope Components:
- Google Slides integration (future enhancement)
- Google Forms integration (future enhancement)
- Real-time collaboration features (beyond basic sharing)
- Advanced document templates and styling (beyond basic formatting)

## System Architecture Alignment

The Google Workspace Tools epic aligns with the existing ONYX multi-service architecture:

### Service Integration Points:
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Suna Frontend  │────│ Agent Tool Layer │────│ Google APIs     │
│   (Next.js)      │    │  (Tool Router)   │    │   (REST/HTTPS)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────┐         │
         └──────────────│ Google Tools │─────────┘
                        │  Service    │
                        └──────────────┘
                               │
                    ┌──────────────┐
                    │   Onyx Core  │
                    │ (Python)     │
                    └──────────────┘
```

### Existing Infrastructure Utilization:
- **Authentication Layer**: Leverages existing OAuth2 tokens and encrypted credential storage in Supabase
- **Agent Framework**: Integrates with existing tool selection and approval gates system
- **Memory Layer**: Stores Google Workspace operation history and document references
- **Monitoring**: Utilizes existing logging and audit trail infrastructure
- **Database**: Extends existing PostgreSQL schema with Google Workspace metadata

## Detailed Design

### Services and Modules

#### 1. Google Tools Service (Python)
**Location**: `onyx-core/services/google_tools.py`

**Responsibilities**:
- OAuth2 token management and refresh
- Google Docs API operations
- Google Sheets API operations
- Drive file management
- Permission validation and caching
- Rate limiting and quota management

**Key Methods**:
```python
class GoogleToolsService:
    async def create_document(title: str, content: str, folder_id: str = None) -> DocResult
    async def edit_document(doc_id: str, action: EditAction, content: str) -> EditResult
    async def create_spreadsheet(title: str, headers: List[str], data: List[List]) -> SheetResult
    async def edit_spreadsheet(sheet_id: str, range: str, data: List[List]) -> SheetResult
    async def list_files(folder_id: str = None, file_type: str = None, query: str = None) -> List[FileResult]
    async def summarize_document(doc_id: str) -> SummaryResult
    async def validate_permissions(file_id: str) -> PermissionResult
```

#### 2. Agent Tool Integration Layer
**Location**: `suna/api/tools/google-workspace/`

**Tool Endpoints**:
- `POST /api/tools/create_doc`
- `PATCH /api/tools/edit_doc`
- `POST /api/tools/create_sheet`
- `PATCH /api/tools/edit_sheet`
- `GET /api/tools/list_drive_files`
- `GET /api/tools/summarize_drive_link`

#### 3. Permission Management Service
**Location**: `onyx-core/services/permission_manager.py`

**Features**:
- Permission validation before operations
- User access rights checking
- Folder permission inheritance
- Share link generation with appropriate access levels

### Data Models and Contracts

#### Database Schema Extensions

```sql
-- Google Workspace Documents Metadata
CREATE TABLE google_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    google_file_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'document', 'spreadsheet', 'folder'
    mime_type TEXT NOT NULL,
    parent_folder_id TEXT,
    permissions JSONB, -- Store permission details
    created_at TIMESTAMP DEFAULT NOW(),
    modified_at TIMESTAMP,
    last_synced_at TIMESTAMP,
    file_url TEXT, -- Shareable link
    file_size BIGINT,
    owner_email TEXT
);

-- Google Workspace Operation History
CREATE TABLE google_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    task_id UUID REFERENCES tasks(id), -- Link to agent task
    operation_type TEXT NOT NULL, -- 'create_doc', 'edit_sheet', etc.
    operation_details JSONB,
    google_file_id TEXT,
    status TEXT NOT NULL, -- 'pending', 'success', 'failed'
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Google API Quota Tracking
CREATE TABLE google_quota_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    api_endpoint TEXT NOT NULL,
    operation_count INTEGER DEFAULT 1,
    quota_reset_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### API Data Contracts

**Document Creation Request**:
```typescript
interface CreateDocRequest {
  title: string;
  content: string;
  folder_id?: string;
  permissions?: {
    share_with?: string[];
    access_level?: 'viewer' | 'commenter' | 'editor';
  };
}
```

**Document Edit Request**:
```typescript
interface EditDocRequest {
  doc_id: string;
  action: 'insert' | 'replace' | 'append' | 'delete';
  content?: string;
  location?: {
    index?: number;
    range?: string;
  };
  format?: {
    heading?: 1 | 2 | 3;
    list?: 'bullet' | 'numbered';
    bold?: boolean;
    italic?: boolean;
  };
}
```

**Spreadsheet Operations**:
```typescript
interface SheetRequest {
  sheet_id: string;
  range?: string; // e.g., "Sheet1!A1:C5"
  data?: any[][]; // 2D array
  headers?: string[];
  formatting?: {
    bold_headers?: boolean;
    column_widths?: number[];
    freeze_panes?: string;
  };
}
```

### APIs and Interfaces

#### Google Docs API Integration Patterns

**Document Creation Flow**:
```python
async def create_document(title: str, content: str, folder_id: str = None) -> Dict:
    # 1. Validate user permissions for target folder
    if folder_id and not await validate_folder_access(folder_id):
        raise PermissionError("Insufficient access to target folder")

    # 2. Create document via Google Docs API
    doc_request = {
        'title': title,
        'parents': [folder_id] if folder_id else []
    }

    doc = docs_service.documents().create(body=doc_request).execute()
    doc_id = doc.get('documentId')

    # 3. Insert content with formatting
    content_requests = self._parse_markdown_to_requests(content)
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': content_requests}
    ).execute()

    # 4. Set sharing permissions
    share_link = await self._create_share_link(doc_id)

    # 5. Store metadata in database
    await self._store_document_metadata(doc_id, title, 'document', folder_id, share_link)

    return {
        'doc_id': doc_id,
        'share_link': share_link,
        'title': title
    }
```

**Document Edit Operations**:
```python
async def edit_document(doc_id: str, action: str, content: str = None, location: Dict = None) -> Dict:
    # 1. Validate permissions and document access
    if not await validate_document_access(doc_id):
        raise PermissionError("No access to document")

    # 2. Build edit request based on action type
    requests = []

    if action == 'insert':
        requests.append({
            'insertText': {
                'location': location or {'index': 1},
                'text': content
            }
        })
    elif action == 'replace':
        if location and 'range' in location:
            requests.append({
                'replaceText': {
                    'range': location['range'],
                    'text': content
                }
            })
    elif action == 'append':
        requests.append({
            'insertText': {
                'location': {'index': -1},
                'text': '\n' + content
            }
        })

    # 3. Execute batch update
    result = docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()

    # 4. Log operation for audit
    await self._log_operation('edit_doc', doc_id, action, result)

    return {
        'success': True,
        'doc_id': doc_id,
        'changes_made': len(requests)
    }
```

#### Google Sheets API Integration Patterns

**Spreadsheet Creation Flow**:
```python
async def create_spreadsheet(title: str, headers: List[str], data: List[List]) -> Dict:
    # 1. Create new spreadsheet
    spreadsheet_request = {
        'properties': {
            'title': title
        }
    }

    spreadsheet = sheets_service.spreadsheets().create(
        body=spreadsheet_request
    ).execute()

    sheet_id = spreadsheet.get('spreadsheetId')
    sheet_title = spreadsheet.get('sheets')[0].get('properties').get('title')

    # 2. Prepare data for insertion (headers + data)
    all_data = [headers] + data

    # 3. Insert data in batch
    range_notation = f'{sheet_title}!A1'
    body = {
        'values': all_data,
        'majorDimension': 'ROWS'
    }

    result = sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_notation,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

    # 4. Apply formatting to headers
    await self._format_spreadsheet_headers(sheet_id, sheet_title, len(headers))

    # 5. Generate share link
    share_link = await self._create_share_link(sheet_id, 'spreadsheets')

    return {
        'sheet_id': sheet_id,
        'share_link': share_link,
        'title': title,
        'rows_updated': result.get('updatedRows')
    }
```

**Advanced Spreadsheet Operations**:
```python
async def edit_spreadsheet_advanced(sheet_id: str, operations: List[Dict]) -> Dict:
    """Handle complex spreadsheet operations including formatting and formulas"""

    requests = []

    for op in operations:
        if op['type'] == 'update_cells':
            requests.append({
                'updateCells': {
                    'rows': op['data'],
                    'fields': 'userEnteredValue,userEnteredFormat'
                }
            })
        elif op['type'] == 'format_range':
            requests.append({
                'repeatCell': {
                    'range': op['range'],
                    'cell': {
                        'userEnteredFormat': op['format']
                    }
                }
            })
        elif op['type'] == 'add_conditional_formatting':
            requests.append({
                'addConditionalFormatRule': {
                    'rule': op['rule'],
                    'ranges': op['ranges']
                }
            })

    # Execute all operations in batch
    batch_update_body = {'requests': requests}
    result = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body=batch_update_body
    ).execute()

    return {
        'success': True,
        'operations_completed': len(requests),
        'updated_cells': result.get('totalUpdatedCells', 0)
    }
```

### Workflows and Sequencing

#### Agent Tool Integration Workflow

```
1. Agent Request → Tool Router → Google Tools Service
2. Permission Validation → OAuth Token Check → Google API Call
3. API Response → Result Processing → Storage & Logging
4. Success/Failure → Agent Feedback → User Notification
```

#### Document Creation Sequence

```python
class DocumentCreationWorkflow:
    async def execute(self, task: AgentTask):
        # 1. Parse agent request for document requirements
        doc_spec = self._parse_document_request(task.description)

        # 2. Validate permissions and quota
        await self._validate_permissions_and_quota(doc_spec)

        # 3. Create document with retry logic
        try:
            result = await self.google_tools.create_document(
                title=doc_spec['title'],
                content=doc_spec['content'],
                folder_id=doc_spec.get('folder_id')
            )

            # 4. Update agent task status
            await self._update_task_success(task.task_id, result)

            # 5. Store operation in audit log
            await self._audit_log_operation('create_doc', task.user_id, result)

        except QuotaExceededError:
            # Implement exponential backoff and queueing
            await self._queue_for_retry(task, 'quota_exceeded')

        except PermissionError as e:
            await self._handle_permission_error(task, e)
```

#### Error Handling and Recovery Patterns

```python
class GoogleAPIErrorHandler:
    async def handle_api_error(self, error: Exception, context: Dict) -> Dict:
        """Comprehensive error handling for Google API operations"""

        if isinstance(error, HttpError):
            if error.resp.status == 403:
                # Permission or quota error
                return await self._handle_auth_quota_error(error, context)
            elif error.resp.status == 429:
                # Rate limiting
                return await self._handle_rate_limit_error(error, context)
            elif error.resp.status >= 500:
                # Server error - implement retry with backoff
                return await self._handle_server_error(error, context)

        elif isinstance(error, RefreshError):
            # Token refresh failed
            return await self._handle_token_refresh_error(error, context)

        else:
            # Unexpected error
            return await self._handle_unexpected_error(error, context)

    async def _handle_rate_limit_error(self, error: HttpError, context: Dict) -> Dict:
        """Implement exponential backoff for rate limiting"""
        retry_after = int(error.resp.headers.get('Retry-After', 10))

        # Calculate exponential backoff (min 1s, max 60s)
        backoff_time = min(60, max(1, 2 ** context.get('retry_count', 0)))

        if backoff_time < retry_after:
            backoff_time = retry_after

        # Log for monitoring
        await self._log_rate_limit_hit(context['user_id'], backoff_time)

        return {
            'retry_after': backoff_time,
            'error_type': 'rate_limit',
            'message': f'Rate limit exceeded. Retry after {backoff_time} seconds.'
        }
```

## Non-Functional Requirements

### Performance

**Response Time Targets**:
- Document creation: <2s (95th percentile)
- Document editing: <1.5s (95th percentile)
- Spreadsheet operations: <3s for large datasets
- File listing: <1s (paginated)
- Document summarization: <5s (depending on size)

**Throughput**:
- Concurrent operations: Max 3 per user (respecting agent limits)
- API rate limits: 100 requests/min per user (Google API limits)
- Batch operations: Up to 100 cells per spreadsheet update

### Security

**Authentication**:
- OAuth2 with minimal required scopes: `drive`, `drive.file`, `spreadsheets`
- Token refresh with 1-hour buffer before expiry
- Encrypted credential storage (AES-256)
- Session-based access control

**Authorization**:
- Permission validation before all operations
- Folder access inheritance checking
- Share link access control
- Audit logging for all data operations

**Data Protection**:
- No credentials in logs or error messages
- Sanitized API responses
- Encrypted storage of Google tokens
- GDPR compliance for user data

### Reliability/Availability

**Error Handling**:
- Comprehensive error classification and handling
- Automatic retry with exponential backoff for transient failures
- Graceful degradation when Google services are unavailable
- Queue-based handling for quota exceeded scenarios

**Recovery**:
- Token refresh automation
- Operation history for recovery and rollback
- Connection pool management for API clients
- Circuit breaker pattern for API unavailability

### Observability

**Logging**:
- Structured JSON logging for all operations
- Performance metrics (latency, success rate)
- Error categorization and alerting
- User activity audit trails

**Metrics**:
- API call success/failure rates
- Response time distributions
- Quota usage tracking
- Document operation counts by type

## Dependencies and Integrations

### External Dependencies

**Google APIs**:
- Google Drive API v3 - File management and permissions
- Google Docs API v1 - Document creation and editing
- Google Sheets API v4 - Spreadsheet operations
- Google OAuth2 - Authentication and token management

**Google API Libraries**:
- `google-api-python-client` - Main Python client library
- `google-auth-httplib2` - Authentication library
- `google-auth-oauthlib` - OAuth2 flow handling

### Internal Dependencies

**ONYX Core Services**:
- Permission management service
- Agent tool router
- Database abstraction layer (PostgreSQL)
- Caching layer (Redis) for permissions and quota tracking

**Suna Frontend**:
- Agent tool integration endpoints
- Permission-aware UI components
- Real-time operation status updates
- User authentication session management

## Acceptance Criteria (Authoritative)

### Authentication & Authorization
- AC6.1.1: OAuth2 flow completes successfully with valid Google account
- AC6.1.2: Tokens refreshed automatically before 1-hour expiry buffer
- AC6.1.3: User can revoke access at any time
- AC6.1.4: Permissions validated before all operations
- AC6.1.5: No credentials stored in plaintext or logs

### Document Operations
- AC6.2.1: Agent can create Google Docs with specified title and content
- AC6.2.2: Document formatting preserves headings, lists, and structure
- AC6.2.3: Created documents accessible via shareable link
- AC6.2.4: Documents respect user's Google Drive permissions
- AC6.2.5: Creation completes within 2 seconds for typical documents
- AC6.2.6: Error handling for insufficient permissions or quota exceeded

### Document Editing
- AC6.3.1: Agent can insert, replace, and append content to existing docs
- AC6.3.2: Edit operations respect Google Docs version history
- AC6.3.3: Batch updates supported for complex edits
- AC6.3.4: Markdown input properly converted to Google Docs formatting
- AC6.3.5: Edit operations complete within 1.5 seconds
- AC6.3.6: Permission validation prevents unauthorized edits

### Spreadsheet Operations
- AC6.4.1: Agent can create Google Sheets with headers and data
- AC6.4.2: Headers formatted with bold styling by default
- AC6.4.3: Data insertion supports 2D arrays and CSV/JSON import
- AC6.4.4: Sheet editing supports range operations and cell updates
- AC6.4.5: Batch updates support multiple operations in single request
- AC6.4.6: Spreadsheet operations complete within 3 seconds for typical datasets
- AC6.4.7: Formulas and basic formatting supported

### File Management
- AC6.6.1: Agent can list files with folder and type filtering
- AC6.6.2: File metadata includes ID, name, type, modified date, owner
- AC6.6.3: Results respect Google Drive permissions and access rights
- AC6.6.4: Pagination supports handling of large file sets
- AC6.6.5: Search functionality supports name and content filtering
- AC6.6.6: File listing completes within 1 second

### Content Processing
- AC6.7.1: Document summarization extracts key points in 3-5 sentences
- AC6.7.2: Summaries include citations to referenced sections
- AC6.7.3: Supports both Google Docs and Sheets content
- AC6.7.4: Processing completes within 5 seconds for typical documents
- AC6.7.5: Error handling for inaccessible or corrupted documents

### Error Handling & Performance
- AC6.8.1: Rate limit errors handled with exponential backoff
- AC6.8.2: Quota exceeded scenarios queued for retry
- AC6.8.3: Connection failures trigger automatic reconnection
- AC6.8.4: All operations logged for audit and debugging
- AC6.8.5: Performance metrics monitored and alerted on thresholds
- AC6.8.6: Graceful degradation when Google APIs are unavailable

### Integration Quality
- AC6.9.1: Google tools integrate seamlessly with existing agent workflows
- AC6.9.2: Approval gates enforced for sensitive document operations
- AC6.9.3: Tool selection logic properly routes to Google Workspace tools
- AC6.9.4: Operation history stored in agent task tracking
- AC6.9.5: Memory layer stores document references and usage patterns
- AC6.9.6: User notification system provides real-time feedback

## Traceability Mapping

| Acceptance Criteria | Spec Section | Component/API | Test Strategy |
|-------------------|---------------|---------------|--------------|
| AC6.1.1-AC6.1.5 | Authentication & Authorization | OAuth2 Service | Integration tests with Google OAuth2 |
| AC6.2.1-AC6.2.6 | Document Operations | Google Docs API | E2E tests for document creation workflows |
| AC6.3.1-AC6.3.6 | Document Editing | Document Edit Service | Unit tests for edit operations |
| AC6.4.1-AC6.4.7 | Spreadsheet Operations | Sheets API Service | Performance tests for large datasets |
| AC6.6.1-AC6.6.6 | File Management | Drive API Service | Permission validation tests |
| AC6.7.1-AC6.7.5 | Content Processing | Document Summarizer | Accuracy tests for summaries |
| AC6.8.1-AC6.8.6 | Error Handling & Performance | Error Handler | Chaos engineering tests |
| AC6.9.1-AC6.9.6 | Integration Quality | Agent Tool Router | Integration workflow tests |

## Risks, Assumptions, Open Questions

### Risks

**High Priority:**
- **Google API Rate Limits**: Complex agent workflows may exceed API quotas, requiring intelligent batching and queueing
- **Permission Complexity**: Google Workspace permission model is complex and may lead to unexpected access denied scenarios
- **API Reliability**: Dependence on external Google APIs introduces availability risks

**Medium Priority:**
- **Cost Management**: API calls to Google services incur costs that need monitoring and optimization
- **Data Consistency**: Maintaining consistency between local metadata and Google Drive state
- **Performance Bottlenecks**: Large document operations may impact agent response times

**Low Priority:**
- **Feature Complexity**: Rich formatting requirements may exceed Google API capabilities
- **User Training**: Users may need guidance on permission management and sharing settings

### Assumptions

- **OAuth2 Integration**: Existing OAuth2 infrastructure is functional and properly configured
- **Agent Framework**: Existing agent tool selection and approval systems will integrate seamlessly
- **Database Schema**: PostgreSQL schema can be extended without breaking changes
- **Google Account**: Users have Google Workspace accounts with necessary permissions

### Open Questions

- **Quota Strategy**: Should individual user quotas be implemented or rely on Google's default limits?
- **Template Library**: Should document templates be pre-configured for common use cases?
- **Real-time Collaboration**: Are real-time collaboration features required for initial release?
- **Multi-tenant**: How should Google Workspace integration handle multiple user accounts?
- **Backup Strategy**: Should Google Workspace documents be backed up locally for resilience?

## Test Strategy Summary

### Test Levels

**Unit Tests (70% coverage target)**:
- Google Tools Service methods
- Permission validation logic
- Error handling scenarios
- Data transformation utilities
- OAuth2 token management

**Integration Tests (80% coverage target)**:
- Google API authentication flow
- Document creation/editing end-to-end
- Spreadsheet operations validation
- Database metadata synchronization
- Agent tool router integration

**Performance Tests**:
- Load testing with concurrent operations (3 users, 10 operations each)
- Latency validation for all API operations
- Memory usage testing for large document processing
- Rate limiting behavior validation
- Quota management effectiveness

**Security Tests**:
- OAuth2 token security validation
- Permission boundary testing
- Audit trail completeness verification
- Credential encryption validation
- Unauthorized access prevention

### Test Data Management

**Test Google Workspace Setup**:
- Dedicated test Google Workspace account
- Test documents and spreadsheets with varied content
- Permission boundary test cases
- Quota monitoring during tests

**Mock Strategy**:
- Google API clients for unit tests
- Network failure scenarios
- Rate limiting simulation
- Error response mocking

### Continuous Integration

**Automated Testing Pipeline**:
- Unit tests on every commit
- Integration tests in staging environment
- Performance tests weekly
- Security scans monthly
- Compliance reporting quarterly

---

**Implementation Priority:**
1. Complete remaining Google Workspace API integrations (Stories 6.2-6.5)
2. Implement comprehensive error handling and rate limiting
3. Enhance permission management and audit logging
4. Optimize performance for agent workflows
5. Extensive testing and monitoring setup

**Dependencies:** Epic 6 builds upon the completed OAuth2 foundation (Story 6.1) and integrates with the existing agent framework (Epic 5) and database infrastructure (Epic 1-3).

*This technical specification provides the foundation for implementing the remaining Google Workspace Tools capabilities within ONYX, enabling autonomous document creation and management as part of strategic agent workflows.*