# Epic 6: Google Workspace Tools - Technical Specification

**Project:** ONYX (Manus Internal)
**Epic ID:** epic-6
**Author:** Technical Architect
**Date:** 2025-11-14
**Version:** 1.0
**Status:** Ready for Implementation

---

## Executive Summary

Epic 6 provides ONYX with comprehensive Google Workspace integration, enabling autonomous creation, editing, and management of Google Docs, Sheets, and Drive files. This epic transforms the agent from advisory mode into an autonomous workspace assistant that can generate strategic documents, maintain data analyses, and collaborate within the user's existing Google ecosystem.

**Goal:** Enable secure, permission-aware Google Workspace automation with enterprise-grade security and reliability

**Success Criteria:**
- Secure OAuth2 authentication with encrypted token storage
- All Google Workspace tools (Docs, Sheets, Drive) fully operational
- Permission awareness prevents unauthorized access
- <2s average latency for file operations
- 99.5% API call success rate with proper error handling
- Full audit trail of all Google Workspace operations

**Timeline:** Week 2 of development (following Epic 1 completion)

**Dependencies:**
- Epic 1 (Foundation & Infrastructure) for Docker environment and secrets management
- Epic 2 (Chat Interface & Core Intelligence) for agent tool integration
- Epic 3 (RAG Integration) for existing Google Drive connector patterns

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Epic 6 Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   User       │────────▶│  Suna (Next) │                 │
│  │   (Agent)    │◀────────│   Frontend   │                 │
│  └──────────────┘  HTTP   └──────┬───────┘                 │
│                            SSE    │                          │
│                                   │                          │
│                            ┌──────▼───────┐                 │
│                            │ Onyx Core   │                 │
│                            │ (Python)     │                 │
│                            └──────┬───────┘                 │
│                                   │                          │
│  ┌─────────────────────────────────┼──────────────────────┐  │
│  │                                 │                      │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │  │
│  │  │  OAuth2     │    │ Google API  │    │  File Ops   │ │  │
│  │  │  Manager    │    │  Connector  │    │  Handler    │ │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘ │  │
│  │                                                         │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │  │
│  │  │   Docs API  │    │  Sheets API │    │  Drive API  │ │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Supabase   │         │   Google     │                 │
│  │ PostgreSQL   │◀────────▶   Workspace  │                 │
│  │   (Storage)  │  OAuth2 │   APIs       │                 │
│  └──────────────┘         └──────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **OAuth2 Manager**: Secure authentication, token lifecycle management, encrypted storage
2. **Google API Connector**: Centralized API client with rate limiting, error handling, batch operations
3. **Document Operations Handler**: Doc/Sheet create/edit operations with formatting and collaboration
4. **Drive Operations Handler**: File listing, search, and permission management
5. **Audit & Security Layer**: Operation logging, permission validation, error tracking

---

## Technical Architecture

### 1. Authentication & Authorization

#### OAuth2 Implementation

```python
# Core OAuth2 Configuration
GOOGLE_OAUTH_CONFIG = {
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
    "redirect_uri": f"{os.getenv('ONYX_BASE_URL')}/auth/google/callback",
    "scopes": [
        "https://www.googleapis.com/auth/drive",          # Drive access
        "https://www.googleapis.com/auth/drive.file",     # File operations
        "https://www.googleapis.com/auth/documents",      # Docs access
        "https://www.googleapis.com/auth/spreadsheets",   # Sheets access
    ],
    "token_url": "https://oauth2.googleapis.com/token",
    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth"
}

# Token Storage Schema
class GoogleToken(BaseModel):
    user_id: str
    access_token: str  # Encrypted
    refresh_token: str  # Encrypted
    expires_at: datetime
    scopes: List[str]
    created_at: datetime
    last_used: datetime
    is_active: bool = True
```

#### Security Implementation

- **Token Encryption**: AES-256 encryption for all tokens stored in Supabase
- **Token Refresh**: Automatic refresh 30 minutes before expiry
- **Scope Validation**: Ensure minimum required scopes for operations
- **Session Management**: Secure session binding with user tokens
- **Revocation Handling**: Graceful handling of revoked/expired tokens

### 2. API Client Architecture

#### Google API Service

```python
class GoogleWorkspaceService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.tokens = self._load_tokens()
        self.docs_service = None
        self.sheets_service = None
        self.drive_service = None
        self._initialize_services()

    async def _initialize_services(self):
        """Initialize all Google API services with authenticated client"""
        credentials = self._build_credentials()
        self.docs_service = build('docs', 'v1', credentials=credentials)
        self.sheets_service = build('sheets', 'v4', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)

    async def execute_with_retry(self, operation: Callable, max_retries: int = 3):
        """Execute API operations with exponential backoff and retry logic"""
```

#### Rate Limiting & Quota Management

```python
class RateLimiter:
    def __init__(self):
        self.limits = {
            'docs': {'requests_per_minute': 100, 'requests_per_day': 10000},
            'sheets': {'requests_per_minute': 100, 'requests_per_day': 10000},
            'drive': {'requests_per_minute': 1000, 'requests_per_day': 10000}
        }
        self.usage = defaultdict(lambda: defaultdict(int))

    async def check_rate_limit(self, service: str) -> bool:
        """Check if operation can proceed within rate limits"""
```

### 3. Document Operations

#### Google Docs Operations

```python
class GoogleDocsHandler:
    """Handler for Google Docs creation and editing operations"""

    async def create_document(self, title: str, content: str, folder_id: str = None) -> Dict:
        """
        Create new Google Doc with formatted content

        Args:
            title: Document title
            content: Markdown content to convert
            folder_id: Optional Drive folder ID for placement

        Returns:
            Dict with document_id, url, and metadata
        """

    async def edit_document(self, doc_id: str, operations: List[Dict]) -> Dict:
        """
        Edit document with batch update operations

        Supported operations:
        - insert_text: Insert text at position
        - replace_text: Replace text range
        - append_text: Append to document
        - format_text: Apply formatting to range
        """

    def _markdown_to_docs_format(self, markdown_content: str) -> List[Dict]:
        """Convert Markdown to Google Docs batch update format"""
```

#### Google Sheets Operations

```python
class GoogleSheetsHandler:
    """Handler for Google Sheets creation and editing operations"""

    async def create_spreadsheet(self, title: str, headers: List[str],
                               data: List[List[Any]], folder_id: str = None) -> Dict:
        """
        Create new Google Sheet with data

        Args:
            title: Sheet title
            headers: Column headers (first row)
            data: 2D array of data
            folder_id: Optional Drive folder ID

        Returns:
            Dict with spreadsheet_id, url, and metadata
        """

    async def edit_sheet(self, spreadsheet_id: str, range_name: str,
                        values: List[List[Any]], operation: str = "UPDATE") -> Dict:
        """
        Edit sheet with data operations

        Supported operations:
        - UPDATE: Replace range values
        - APPEND: Add rows to sheet
        - CLEAR: Clear range contents
        """

    async def format_sheet(self, spreadsheet_id: str, formatting_rules: List[Dict]) -> Dict:
        """
        Apply formatting to sheet ranges

        Formatting options:
        - Cell colors, fonts, borders
        - Number formats, text alignment
        - Column widths, row heights
        """
```

### 4. Drive Operations

#### File Management

```python
class GoogleDriveHandler:
    """Handler for Drive file operations and permissions"""

    async def list_files(self, query: str = None, folder_id: str = None,
                        file_types: List[str] = None, page_size: int = 50) -> List[Dict]:
        """
        List Drive files with filtering and pagination

        Args:
            query: Search query string
            folder_id: Limit to specific folder
            file_types: Filter by MIME types
            page_size: Results per page (max 100)

        Returns:
            List of file metadata
        """

    async def get_file_metadata(self, file_id: str) -> Dict:
        """Get comprehensive file metadata including permissions"""

    async def create_folder(self, name: str, parent_folder_id: str = None) -> Dict:
        """Create folder in Drive"""

    async def move_file(self, file_id: str, new_folder_id: str) -> Dict:
        """Move file to different folder"""

    async def check_permissions(self, file_id: str) -> Dict:
        """Check user permissions for file operations"""
```

### 5. Tool Integration

#### Agent Tool Interface

```python
# Tool definitions for agent integration
GOOGLE_WORKSPACE_TOOLS = {
    "create_doc": {
        "description": "Create new Google Doc with formatted content",
        "parameters": {
            "title": {"type": "string", "required": True},
            "content": {"type": "string", "required": True},
            "folder_id": {"type": "string", "required": False}
        },
        "returns": {"document_id": "string", "url": "string", "share_link": "string"}
    },

    "edit_doc": {
        "description": "Edit existing Google Doc",
        "parameters": {
            "document_id": {"type": "string", "required": True},
            "operations": {"type": "array", "required": True}
        },
        "returns": {"success": "boolean", "changes_made": "number", "version": "string"}
    },

    "create_sheet": {
        "description": "Create new Google Sheet with data",
        "parameters": {
            "title": {"type": "string", "required": True},
            "headers": {"type": "array", "required": True},
            "data": {"type": "array", "required": True},
            "folder_id": {"type": "string", "required": False}
        },
        "returns": {"spreadsheet_id": "string", "url": "string", "share_link": "string"}
    },

    "edit_sheet": {
        "description": "Edit Google Sheet data and formatting",
        "parameters": {
            "spreadsheet_id": {"type": "string", "required": True},
            "range": {"type": "string", "required": True},
            "values": {"type": "array", "required": True},
            "operation": {"type": "string", "enum": ["UPDATE", "APPEND", "CLEAR"]}
        },
        "returns": {"success": "boolean", "affected_range": "string", "cells_updated": "number"}
    },

    "list_drive_files": {
        "description": "List and search Drive files",
        "parameters": {
            "query": {"type": "string", "required": False},
            "folder_id": {"type": "string", "required": False},
            "file_types": {"type": "array", "required": False},
            "max_results": {"type": "integer", "default": 50}
        },
        "returns": {"files": "array", "total_count": "number", "next_page_token": "string"}
    },

    "summarize_drive_link": {
        "description": "Extract and summarize Google Doc content",
        "parameters": {
            "url_or_id": {"type": "string", "required": True},
            "summary_length": {"type": "integer", "default": 3}
        },
        "returns": {"summary": "string", "key_points": "array", "sections": "array"}
    }
}
```

---

## Database Schema

### Google Tokens Table

```sql
CREATE TABLE google_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    scopes TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT valid_expiry CHECK (expires_at > created_at),
    CONSTRAINT active_token_unique UNIQUE (user_id, is_active) DEFERRABLE INITIALLY DEFERRED
);

-- Indexes for performance
CREATE INDEX idx_google_tokens_user_id ON google_tokens(user_id);
CREATE INDEX idx_google_tokens_expires_at ON google_tokens(expires_at);
CREATE INDEX idx_google_tokens_active ON google_tokens(user_id) WHERE is_active = TRUE;
```

### Google Operations Audit Table

```sql
CREATE TABLE google_operations_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    tool_name VARCHAR(50) NOT NULL,
    target_resource_id VARCHAR(255),
    operation_data JSONB,
    result JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'ERROR', 'TIMEOUT')),
    error_message TEXT,
    duration_ms INTEGER,
    api_calls_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Performance constraints
    CONSTRAINT duration_positive CHECK (duration_ms > 0),
    CONSTRAINT api_calls_positive CHECK (api_calls_count >= 0)
);

-- Indexes for audit queries
CREATE INDEX idx_google_audit_user_id ON google_operations_audit(user_id);
CREATE INDEX idx_google_audit_operation_type ON google_operations_audit(operation_type);
CREATE INDEX idx_google_audit_created_at ON google_operations_audit(created_at DESC);
CREATE INDEX idx_google_audit_status ON google_operations_audit(status);
```

### Document Metadata Cache

```sql
CREATE TABLE google_document_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    folder_id VARCHAR(255),
    modified_time TIMESTAMP,
    size_bytes BIGINT,
    sharing_mode VARCHAR(20),
    metadata JSONB,
    cache_key VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_file_user UNIQUE (user_id, file_id),
    CONSTRAINT cache_validity CHECK (expires_at > created_at)
);

-- Indexes for cache lookups
CREATE INDEX idx_doc_cache_user_file ON google_document_cache(user_id, file_id);
CREATE INDEX idx_doc_cache_expires_at ON google_document_cache(expires_at);
CREATE INDEX idx_doc_cache_folder ON google_document_cache(user_id, folder_id);
```

---

## Security Implementation

### 1. Token Encryption

```python
import cryptography.fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class TokenEncryption:
    def __init__(self, master_key: str):
        """Initialize encryption with master key from environment"""
        self.salt = b'google_token_salt_fixed'  # In production, use per-user salts
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher_suite = Fernet(key)

    def encrypt_token(self, token: str) -> str:
        """Encrypt access/refresh token"""
        return self.cipher_suite.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access/refresh token"""
        return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
```

### 2. Permission Validation

```python
class PermissionValidator:
    """Validate user permissions before Google Workspace operations"""

    async def validate_document_access(self, user_id: str, document_id: str,
                                     operation: str) -> bool:
        """
        Validate user has permission for document operation

        Operations: READ, WRITE, SHARE, DELETE
        """
        try:
            # Check cache first
            cached_permissions = await self._get_cached_permissions(document_id)
            if cached_permissions:
                return self._check_permission(cached_permissions, operation)

            # Fetch from Drive API
            file_metadata = await self.drive_service.files().get(
                fileId=document_id,
                fields='permissions, owners, sharingUser'
            ).execute()

            # Validate user permissions
            user_email = await self._get_user_email(user_id)
            has_permission = self._evaluate_permissions(
                file_metadata.get('permissions', []),
                user_email,
                file_metadata.get('owners', []),
                operation
            )

            # Cache result
            await self._cache_permissions(document_id, file_metadata['permissions'])

            return has_permission

        except HttpError as e:
            if e.resp.status == 404:
                return False  # File not found
            if e.resp.status == 403:
                return False  # Access denied
            raise  # Re-raise other errors
```

### 3. Audit Logging

```python
class GoogleAuditLogger:
    """Comprehensive audit logging for all Google Workspace operations"""

    async def log_operation(self, operation: Dict):
        """Log operation with full context"""
        audit_record = {
            'user_id': operation['user_id'],
            'operation_type': operation['type'],
            'tool_name': operation['tool'],
            'target_resource_id': operation.get('resource_id'),
            'operation_data': operation.get('parameters', {}),
            'result': operation.get('result', {}),
            'status': operation['status'],
            'error_message': operation.get('error'),
            'duration_ms': operation.get('duration_ms'),
            'api_calls_count': operation.get('api_calls', 0)
        }

        # Store in database
        await self.db.insert('google_operations_audit', audit_record)

        # Send to monitoring for critical operations
        if self._is_critical_operation(operation):
            await self._send_security_alert(operation)

    def _is_critical_operation(self, operation: Dict) -> bool:
        """Identify operations that require security alerts"""
        critical_tools = ['delete_file', 'share_document', 'mass_export']
        critical_operations = ['DELETE', 'SHARE', 'EXPORT']

        return (
            operation['tool'] in critical_tools or
            operation['type'] in critical_operations or
            operation['status'] == 'ERROR'
        )
```

---

## Performance Optimization

### 1. Caching Strategy

```python
class GoogleWorkspaceCache:
    """Multi-tier caching for Google API responses"""

    def __init__(self):
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min memory cache
        self.redis_cache = RedisCache ttl=3600  # 1 hour Redis cache

    async def get_file_metadata(self, file_id: str, user_id: str) -> Optional[Dict]:
        """Get file metadata with cache lookup"""
        cache_key = f"file_meta:{user_id}:{file_id}"

        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # Check Redis cache
        cached_data = await self.redis_cache.get(cache_key)
        if cached_data:
            self.memory_cache[cache_key] = cached_data
            return cached_data

        return None

    async def cache_file_metadata(self, file_id: str, user_id: str, metadata: Dict):
        """Cache file metadata with appropriate TTL"""
        cache_key = f"file_meta:{user_id}:{file_id}"

        # Cache based on file type and usage patterns
        ttl = self._calculate_ttl(metadata)

        await self.redis_cache.set(cache_key, metadata, ttl=ttl)
        self.memory_cache[cache_key] = metadata
```

### 2. Batch Operations

```python
class BatchOperationOptimizer:
    """Optimize multiple operations through batching and parallelization"""

    async def batch_sheet_updates(self, updates: List[Dict]) -> List[Dict]:
        """
        Group sheet updates by spreadsheet and execute in batches

        Google Sheets API supports:
        - Multiple range updates in single request
        - Parallel execution across different spreadsheets
        """

        # Group by spreadsheet ID
        grouped_updates = defaultdict(list)
        for update in updates:
            grouped_updates[update['spreadsheet_id']].append(update)

        # Execute batched operations in parallel
        tasks = []
        for spreadsheet_id, sheet_updates in grouped_updates.items():
            batch_request = self._build_batch_request(sheet_updates)
            tasks.append(self._execute_batch_update(spreadsheet_id, batch_request))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._process_batch_results(results, updates)

    def _build_batch_request(self, updates: List[Dict]) -> Dict:
        """Build batch update request from individual updates"""
        requests = []
        for update in updates:
            if update['operation'] == 'UPDATE':
                requests.append({
                    'updateCells': {
                        'range': update['range'],
                        'rows': update['values'],
                        'fields': '*'
                    }
                })
            elif update['operation'] == 'FORMAT':
                requests.append({
                    'repeatCell': {
                        'range': update['range'],
                        'cell': {
                            'userEnteredFormat': update['format']
                        },
                        'fields': 'userEnteredFormat'
                    }
                })

        return {'requests': requests}
```

### 3. Connection Pooling

```python
class GoogleAPIConnectionPool:
    """Connection pool for Google API services to reduce overhead"""

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.semaphore = asyncio.Semaphore(max_connections)
        self.connections = {}

    async def get_service(self, service_name: str, user_id: str):
        """Get API service from pool or create new connection"""
        async with self.semaphore:
            connection_key = f"{service_name}:{user_id}"

            if connection_key not in self.connections:
                # Create new authenticated service
                service = await self._create_authenticated_service(service_name, user_id)
                self.connections[connection_key] = service

            return self.connections[connection_key]

    async def refresh_expired_connections(self):
        """Background task to refresh expired authentication"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired_connections()
            except Exception as e:
                logger.error(f"Connection refresh error: {e}")
```

---

## Error Handling & Resilience

### 1. Error Classification

```python
class GoogleWorkspaceErrorHandler:
    """Comprehensive error handling for Google Workspace operations"""

    ERROR_CATEGORIES = {
        'AUTHENTICATION': {
            'codes': [401, 403],
            'patterns': ['Invalid Credentials', 'Permission Denied', 'Token Expired'],
            'action': 'refresh_token',
            'retry': True
        },
        'RATE_LIMIT': {
            'codes': [429],
            'patterns': ['Rate Limit Exceeded', 'Quota Exceeded'],
            'action': 'exponential_backoff',
            'retry': True
        },
        'NOT_FOUND': {
            'codes': [404],
            'patterns': ['File Not Found', 'Document Not Found'],
            'action': 'fail_fast',
            'retry': False
        },
        'PERMISSION': {
            'codes': [403],
            'patterns': ['Insufficient Permission', 'Access Denied'],
            'action': 'check_permissions',
            'retry': False
        },
        'NETWORK': {
            'codes': [500, 502, 503, 504],
            'patterns': ['Backend Error', 'Service Unavailable'],
            'action': 'retry_with_backoff',
            'retry': True
        }
    }

    async def handle_error(self, error: Exception, operation_context: Dict) -> Dict:
        """Classify and handle errors appropriately"""
        error_category = self._classify_error(error)
        error_info = self.ERROR_CATEGORIES[error_category]

        # Log error with context
        await self._log_error(error, operation_context, error_category)

        # Determine retry strategy
        if error_info['retry'] and operation_context.get('retry_count', 0) < 3:
            retry_delay = self._calculate_retry_delay(error_category, operation_context)
            return {
                'should_retry': True,
                'retry_delay': retry_delay,
                'action': error_info['action'],
                'error_category': error_category
            }

        return {
            'should_retry': False,
            'action': error_info['action'],
            'error_category': error_category,
            'user_message': self._get_user_friendly_message(error_category, error)
        }
```

### 2. Circuit Breaker Pattern

```python
class GoogleAPICircuitBreaker:
    """Circuit breaker for Google API calls to prevent cascade failures"""

    def __init__(self):
        self.failure_threshold = 5
        self.recovery_timeout = 60  # seconds
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = None

    async def call(self, operation: Callable, *args, **kwargs):
        """Execute operation with circuit breaker protection"""

        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpenException("Google API circuit breaker is OPEN")

        try:
            result = await operation(*args, **kwargs)

            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'

            raise e
```

### 3. Graceful Degradation

```python
class GoogleWorkspaceFallback:
    """Fallback mechanisms when Google services are unavailable"""

    async def create_document_fallback(self, title: str, content: str) -> Dict:
        """Fallback: Create Markdown file in local storage"""

        # Create file in local storage with Google Docs structure
        local_filename = f"{title.replace(' ', '_')}_{datetime.now().isoformat()}.md"
        local_path = f"/tmp/google_fallback/{local_filename}"

        # Add metadata for future sync when Google is available
        fallback_content = f"""# {title}

<!-- Google Workspace Fallback Document -->
<!-- Created: {datetime.now().isoformat()} -->
<!-- Pending Google Docs sync -->

{content}

---
*Document created in local storage due to Google service unavailability. Will sync to Google Drive when service is restored.*
"""

        await self._save_local_file(local_path, fallback_content)

        # Store sync task for later
        await self._queue_sync_task({
            'type': 'create_doc',
            'title': title,
            'content': content,
            'local_path': local_path,
            'created_at': datetime.now().isoformat()
        })

        return {
            'success': True,
            'fallback_mode': True,
            'local_path': local_path,
            'message': 'Document saved locally. Will sync to Google Drive when service is available.'
        }
```

---

## Testing Strategy

### 1. Unit Tests

```python
# Test coverage targets
COVERAGE_TARGETS = {
    'google_workspace_service.py': 95,
    'oauth2_manager.py': 90,
    'document_handlers.py': 90,
    'permission_validator.py': 85,
    'audit_logger.py': 80
}

class TestGoogleWorkspaceService:
    """Comprehensive unit tests for Google Workspace integration"""

    @pytest.fixture
    async def mock_google_service(self):
        """Mock Google API service for testing"""
        # Mock all Google API responses
        with patch('googleapiclient.discovery.build') as mock_build:
            mock_service = AsyncMock()
            mock_build.return_value = mock_service
            yield GoogleWorkspaceService("test_user_id")

    async def test_create_document_success(self, mock_google_service):
        """Test successful document creation"""
        # Setup mock response
        mock_google_service.docs_service.documents().create().execute.return_value = {
            'documentId': 'test_doc_id',
            'title': 'Test Document'
        }

        # Execute operation
        result = await mock_google_service.create_document(
            title="Test Document",
            content="# Test Content\n\nThis is test content."
        )

        # Assertions
        assert result['document_id'] == 'test_doc_id'
        assert result['success'] is True
        assert 'url' in result

    async def test_permission_validation_denied(self, mock_google_service):
        """Test permission validation when access is denied"""
        # Setup mock to raise permission error
        mock_google_service.drive_service.files().get().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'{"error": {"message": "Permission denied"}}'
        )

        # Test validation
        with pytest.raises(PermissionDeniedException):
            await mock_google_service.validate_document_access(
                user_id="test_user",
                document_id="restricted_doc_id",
                operation="WRITE"
            )

    async def test_rate_limit_handling(self, mock_google_service):
        """Test rate limit error handling"""
        from googleapiclient.errors import HttpError

        # Setup rate limit error
        mock_google_service.sheets_service.spreadsheets().values().update().execute.side_effect = HttpError(
            resp=Mock(status=429), content=b'{"error": {"message": "Rate limit exceeded"}}'
        )

        # Test retry logic
        with patch('asyncio.sleep') as mock_sleep:
            result = await mock_google_service.execute_with_retry(
                operation=mock_google_service.sheets_service.spreadsheets().values().update()
            )

            # Should have slept for backoff
            assert mock_sleep.called
```

### 2. Integration Tests

```python
class TestGoogleWorkspaceIntegration:
    """Integration tests with real Google Workspace APIs"""

    @pytest.fixture
    async def test_credentials(self):
        """Test Google credentials for integration testing"""
        # Use test Google Workspace account
        return {
            'client_id': os.getenv('GOOGLE_TEST_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_TEST_CLIENT_SECRET'),
            'refresh_token': os.getenv('GOOGLE_TEST_REFRESH_TOKEN')
        }

    async def test_full_document_workflow(self, test_credentials):
        """Test complete document creation and editing workflow"""

        # Initialize service with test credentials
        service = GoogleWorkspaceService("test_user")
        await service._initialize_with_credentials(test_credentials)

        # Create document
        create_result = await service.create_document(
            title=f"Integration Test {datetime.now().isoformat()}",
            content="# Test Document\n\nThis is an integration test."
        )

        assert 'document_id' in create_result
        doc_id = create_result['document_id']

        # Edit document
        edit_result = await service.edit_document(
            doc_id=doc_id,
            operations=[{
                'type': 'insert_text',
                'text': '\n\n## Added Section\n\nContent added during integration test.',
                'location': 'END'
            }]
        )

        assert edit_result['success'] is True

        # Verify document content
        doc_content = await service.get_document_content(doc_id)
        assert 'Added Section' in doc_content

        # Cleanup
        await service.delete_document(doc_id)

    async def test_batch_sheet_operations(self, test_credentials):
        """Test batch sheet update operations"""

        service = GoogleWorkspaceService("test_user")
        await service._initialize_with_credentials(test_credentials)

        # Create sheet with test data
        sheet_result = await service.create_spreadsheet(
            title="Batch Test Sheet",
            headers=['Name', 'Value', 'Status'],
            data=[
                ['Test 1', 100, 'Active'],
                ['Test 2', 200, 'Pending'],
                ['Test 3', 300, 'Complete']
            ]
        )

        spreadsheet_id = sheet_result['spreadsheet_id']

        # Prepare batch updates
        updates = [
            {
                'range': 'Sheet1!B2:B4',
                'values': [[150], [250], [350]],
                'operation': 'UPDATE'
            },
            {
                'range': 'Sheet1!A5',
                'values': [['Test 4']],
                'operation': 'APPEND'
            }
        ]

        # Execute batch update
        batch_result = await service.batch_update_sheet(spreadsheet_id, updates)

        assert batch_result['success'] is True
        assert batch_result['updates_completed'] == 2

        # Verify updates
        final_data = await service.get_sheet_data(spreadsheet_id, 'Sheet1!A1:C5')
        assert final_data[1][1] == 150  # Test 1 value updated
        assert len(final_data) == 4       # New row added

        # Cleanup
        await service.delete_spreadsheet(spreadsheet_id)
```

### 3. Performance Tests

```python
class TestGoogleWorkspacePerformance:
    """Performance testing for Google Workspace operations"""

    async def test_document_creation_latency(self):
        """Test document creation meets <2s latency requirement"""

        latencies = []
        test_iterations = 20

        for i in range(test_iterations):
            start_time = time.time()

            await google_service.create_document(
                title=f"Perf Test {i}",
                content="Performance test document content."
            )

            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = np.percentile(latencies, 95)

        assert avg_latency < 2000, f"Average latency {avg_latency}ms exceeds 2000ms target"
        assert p95_latency < 3000, f"P95 latency {p95_latency}ms exceeds 3000ms target"

    async def test_concurrent_operations(self):
        """Test concurrent operations handle load without degradation"""

        concurrent_operations = 10
        operations_per_batch = 5

        async def simulate_user_operations(user_id: str):
            """Simulate typical user operations"""
            operations = []

            # Mix of document and sheet operations
            for i in range(operations_per_batch):
                if i % 2 == 0:
                    operations.append(google_service.create_document(
                        title=f"Concurrent Test {user_id} {i}",
                        content="Concurrent operation test content."
                    ))
                else:
                    operations.append(google_service.create_spreadsheet(
                        title=f"Concurrent Sheet {user_id} {i}",
                        headers=['Data'],
                        data=[[f"Row {i}"]]
                    ))

            results = await asyncio.gather(*operations, return_exceptions=True)
            return results

        # Execute concurrent user simulations
        user_ids = [f"user_{i}" for i in range(concurrent_operations)]
        start_time = time.time()

        tasks = [simulate_user_operations(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        total_operations = concurrent_operations * operations_per_batch
        avg_operation_time = (total_time / total_operations) * 1000

        # Performance assertions
        assert avg_operation_time < 2500, f"Concurrent operation time {avg_operation_time}ms too high"

        # Check error rate
        successful_operations = sum(
            1 for user_results in results
            for result in user_results
            if not isinstance(result, Exception)
        )
        error_rate = (total_operations - successful_operations) / total_operations
        assert error_rate < 0.05, f"Error rate {error_rate} exceeds 5% threshold"
```

---

## Monitoring & Observability

### 1. Metrics Collection

```python
class GoogleWorkspaceMetrics:
    """Comprehensive metrics collection for Google Workspace operations"""

    def __init__(self):
        self.metrics = {
            'operations': Counter(['operation_type', 'status', 'user_id']),
            'latency': Histogram(['operation_type', 'service'],
                               buckets=[100, 500, 1000, 2000, 5000, 10000]),
            'api_calls': Counter(['service', 'method', 'status_code']),
            'errors': Counter(['error_category', 'operation_type']),
            'active_tokens': Gauge(['user_id']),
            'cache_hits': Counter(['cache_type', 'operation']),
            'rate_limit_hits': Counter(['service'])
        }

    async def record_operation(self, operation: Dict):
        """Record operation metrics"""
        self.metrics['operations'].labels(
            operation_type=operation['type'],
            status=operation['status'],
            user_id=operation.get('user_id', 'unknown')
        ).inc()

        if 'duration_ms' in operation:
            self.metrics['latency'].labels(
                operation_type=operation['type'],
                service=operation.get('service', 'unknown')
            ).observe(operation['duration_ms'])

        if operation.get('api_calls'):
            for api_call in operation['api_calls']:
                self.metrics['api_calls'].labels(
                    service=api_call['service'],
                    method=api_call['method'],
                    status_code=api_call['status_code']
                ).inc()

    async def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        from prometheus_client import generate_latest
        return generate_latest()
```

### 2. Health Checks

```python
class GoogleWorkspaceHealthChecker:
    """Health check endpoints for Google Workspace integration"""

    async def check_oauth_health(self) -> Dict:
        """Check OAuth authentication system health"""
        try:
            # Test token refresh mechanism
            test_tokens = await self.db.query(
                "SELECT COUNT(*) as count FROM google_tokens WHERE is_active = TRUE"
            )

            # Test encryption/decryption
            test_value = "health_check_token_123"
            encrypted = self.token_encryptor.encrypt_token(test_value)
            decrypted = self.token_encryptor.decrypt_token(encrypted)
            encryption_works = decrypted == test_value

            return {
                'status': 'healthy' if encryption_works else 'unhealthy',
                'active_tokens': test_tokens['count'],
                'encryption_working': encryption_works,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def check_google_api_health(self) -> Dict:
        """Check Google API connectivity and quota status"""
        try:
            # Test Drive API
            drive_service = build('drive', 'v3', credentials=self.test_credentials)
            drive_response = drive_service.about().get(fields='user').execute()

            # Test Docs API
            docs_service = build('docs', 'v1', credentials=self.test_credentials)
            docs_health = True  # Just check service builds successfully

            # Check quota status (simplified)
            quota_status = 'healthy'  # Would require API calls to check actual usage

            return {
                'status': 'healthy',
                'drive_api': drive_response['user'].get('emailAddress', 'connected'),
                'docs_api': 'connected',
                'quota_status': quota_status,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
```

### 3. Alerting Rules

```yaml
# Prometheus alerting rules for Google Workspace integration
groups:
  - name: google_workspace.rules
    rules:
      - alert: GoogleWorkspaceHighErrorRate
        expr: rate(google_operations_total{status="ERROR"}[5m]) / rate(google_operations_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
          service: google_workspace
        annotations:
          summary: "Google Workspace error rate is {{ $value | humanizePercentage }}"
          description: "Error rate for Google Workspace operations has exceeded 5% for 2 minutes"

      - alert: GoogleWorkspaceHighLatency
        expr: histogram_quantile(0.95, rate(google_operation_duration_seconds_bucket[5m])) > 3
        for: 5m
        labels:
          severity: warning
          service: google_workspace
        annotations:
          summary: "Google Workspace P95 latency is {{ $value }}s"
          description: "95th percentile latency has exceeded 3 seconds for 5 minutes"

      - alert: GoogleWorkspaceRateLimit
        expr: increase(google_rate_limit_hits_total[5m]) > 10
        for: 1m
        labels:
          severity: warning
          service: google_workspace
        annotations:
          summary: "Google Workspace rate limit hits: {{ $value }}"
          description: "Rate limit hits have exceeded 10 in the last 5 minutes"

      - alert: GoogleWorkspaceTokenExpiry
        expr: google_active_tokens == 0
        for: 1m
        labels:
          severity: critical
          service: google_workspace
        annotations:
          summary: "No active Google tokens"
          description: "No active Google authentication tokens found - users may not be able to use Google Workspace features"
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Stories to Implement:**
- Story 6.1: Google OAuth2 Setup & Token Management
- Story 6.6: List Drive Files Tool (permission validation)

**Deliverables:**
- OAuth2 authentication system
- Token encryption and storage
- Basic Drive API integration
- Permission validation framework
- Audit logging infrastructure

**Success Criteria:**
- OAuth flow complete with encrypted token storage
- Users can authenticate and grant permissions
- Drive file listing works with permission awareness
- All operations logged for audit

### Phase 2: Document Operations (Week 1)

**Stories to Implement:**
- Story 6.2: Create Google Doc Tool
- Story 6.4: Create Google Sheet Tool

**Deliverables:**
- Document creation API
- Spreadsheet creation API
- Markdown to Google Docs conversion
- Data formatting and styling

**Success Criteria:**
- Agent can create Docs and Sheets
- Content properly formatted and styled
- <2s creation latency
- Files created in appropriate folders

### Phase 3: Document Editing (Week 2)

**Stories to Implement:**
- Story 6.3: Edit Google Doc Tool
- Story 6.5: Edit Google Sheet Tool

**Deliverables:**
- Document editing operations
- Spreadsheet data manipulation
- Batch update optimization
- Version control integration

**Success Criteria:**
- Agent can edit existing documents
- Batch operations efficient
- Changes tracked in Google Docs version history
- <2s edit operation latency

### Phase 4: Integration & Optimization (Week 2)

**Stories to Implement:**
- Story 6.7: Summarize Drive Link Tool

**Deliverables:**
- Document content extraction
- LLM-powered summarization
- Performance optimization
- Error handling completeness

**Success Criteria:**
- Document summarization working
- All performance targets met
- Comprehensive error handling
- 99.5% overall success rate

---

## Risk Assessment & Mitigation

### High-Risk Areas

1. **Google API Quota Management**
   - **Risk**: API quota exhaustion blocking operations
   - **Mitigation**: Smart batching, quota monitoring, fallback strategies
   - **Monitoring**: Real-time quota tracking, alerts at 80% usage

2. **Token Security**
   - **Risk**: Token compromise leading to unauthorized access
   - **Mitigation**: AES-256 encryption, minimal scope principle, regular rotation
   - **Monitoring**: Anomaly detection on token usage patterns

3. **Permission Complexity**
   - **Risk**: Complex permission rules causing access issues
   - **Mitigation**: Comprehensive permission testing, clear error messages
   - **Monitoring**: Permission validation success rates

### Medium-Risk Areas

1. **Google API Changes**
   - **Risk**: API deprecation or breaking changes
   - **Mitigation**: Version pinning, compatibility layer, upgrade monitoring
   - **Monitoring**: API version tracking, deprecation notice alerts

2. **Performance Degradation**
   - **Risk**: Increasing latency with data growth
   - **Mitigation**: Caching strategies, connection pooling, performance testing
   - **Monitoring**: Latency percentiles, cache hit rates

---

## Success Metrics

### Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Document Creation Latency | <2s average, 95th percentile <3s | Prometheus metrics |
| Document Edit Latency | <2s average, 95th percentile <3s | Prometheus metrics |
| API Success Rate | >99.5% | Error tracking |
| Rate Limit Hit Rate | <1% of operations | API monitoring |
| Token Refresh Success | >99.9% | Authentication logging |

### Security Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Token Encryption Coverage | 100% | Code audit |
| Permission Validation Coverage | 100% | Test coverage |
| Security Incident Rate | 0 incidents | Security monitoring |
| Audit Log Completeness | 100% of operations | Log analysis |

### User Experience Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| First-time Setup Success | >95% | User analytics |
| Task Completion Rate | >98% | Task tracking |
| Error Message Clarity | >90% user understanding | User surveys |
| Feature Adoption | >80% of active users | Usage analytics |

---

## Conclusion

Epic 6 delivers enterprise-grade Google Workspace integration that transforms ONYX into a powerful autonomous workspace assistant. The technical specification provides:

1. **Secure Foundation**: OAuth2 with encrypted token storage and comprehensive audit logging
2. **Complete Integration**: Full Google Docs, Sheets, and Drive API coverage with permission awareness
3. **Enterprise Performance**: Sub-2-second latency with 99.5% reliability through caching and optimization
4. **Production Ready**: Comprehensive monitoring, error handling, and security controls

The implementation is designed to scale with user needs while maintaining security and performance standards. The modular architecture allows for future expansion to additional Google Workspace services as requirements evolve.

The specification provides detailed guidance for development teams to implement each component with confidence in security, performance, and maintainability requirements.

---

**Document created:** 2025-11-14
**Status:** Ready for Implementation
**Dependencies:** Epic 1 (Foundation), Epic 2 (Chat Interface)
**Estimated effort:** 2 weeks (7 stories, medium complexity)
**Critical path:** Epic 1 → Epic 2 → Epic 6