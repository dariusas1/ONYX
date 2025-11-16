# Story 6.1: OAuth2 Setup & Integration

**Story ID:** 6-1-oauth2-setup-integration
**Epic:** Epic 6 - Google Workspace Tools
**Status:** drafted
**Created:** 2025-11-16
**Story Points:** 13 (High complexity - OAuth2 foundation + security + token management)
**Priority:** P0 (Critical blocker for all Google Workspace stories)

---

## User Story

**As a** backend engineer,
**I want** secure Google OAuth2 authentication with token refresh,
**So that** Manus can safely access user's Google Workspace without storing passwords and all subsequent Google tools can operate with proper authorization.

---

## Business Context

OAuth2 Setup & Integration is the foundational security layer for the entire Google Workspace integration capability in Manus Internal. This story establishes the secure authentication framework that enables:

- Secure Google account connection without password storage
- Automated token management for persistent access
- Permission-aware operations respecting user privacy
- Foundation for Google Docs creation/editing tools (Stories 6.2-6.3)
- Foundation for Google Sheets creation/editing tools (Stories 6.4-6.5)

**Business Impact:**
- Enables autonomous document creation and editing capabilities
- Provides enterprise-grade security for Google Workspace integration
- Establishes user trust through proper OAuth2 consent and permissions
- Foundation for advanced agent workflows with Google Workspace tools

**Technical Foundation:**
This story builds on existing OAuth2 implementation patterns from Story 3-2 (Google Drive Connector) but extends the scope to support broader Google Workspace APIs required for document and spreadsheet operations.

---

## Acceptance Criteria

### AC6.1.1: OAuth2 Flow Completion
- **Given:** User initiates Google Workspace integration for the first time
- **When:** User clicks "Connect Google Account" in workspace settings
- **Then:** Redirected to Google OAuth2 consent screen with correct scopes
- **And:** User grants Manus permission to access Drive, Docs, Sheets APIs
- **And:** OAuth2 flow completes successfully with valid authorization code exchange
- **And:** User receives confirmation of successful Google account connection

### AC6.1.2: Automatic Token Refresh
- **Given:** User has successfully completed OAuth2 flow
- **When:** Access token approaches expiry (within 1-hour buffer)
- **Then:** System automatically refreshes tokens using refresh token
- **And:** Token refresh completes transparently without user interaction
- **And:** Refreshed tokens stored securely with updated expiry timestamps
- **And:** No interruption in Google Workspace API access during token refresh

### AC6.1.3: Access Revocation
- **Given:** User has active Google Workspace integration
- **When:** User clicks "Disconnect Google Account" in workspace settings
- **Then:** System revokes all stored OAuth tokens immediately
- **And:** Google access permissions are revoked via Google API
- **And:** User receives confirmation of successful disconnection
- **And:** All subsequent Google Workspace operations require re-authentication

### AC6.1.4: Permission Validation
- **Given:** User has authenticated Google Workspace integration
- **When:** Any Google Workspace API operation is attempted
- **Then:** System validates current permissions before executing operation
- **And:** Operations only proceed if user has granted required permissions
- **And:** Permission denied errors result in clear user messaging
- **And:** Users are redirected to OAuth consent if permissions are insufficient

### AC6.1.5: Secure Credential Storage
- **Given:** OAuth tokens are received from Google
- **When:** Tokens are stored in system database
- **Then:** All tokens encrypted using AES-256 encryption before storage
- **And:** No credentials appear in plaintext in database, logs, or error messages
- **And:** Token encryption keys managed securely via environment variables
- **And:** Database access requires proper authentication for token retrieval

---

## Tasks / Subtasks

### Task 1: Google OAuth2 Configuration Setup (AC: 6.1.1)
- [ ] 1.1 Set up Google Cloud Project OAuth credentials
  - [ ] Create/verify Google OAuth2 client ID and secret
  - [ ] Configure authorized redirect URIs for development/production
  - [ ] Define required OAuth scopes: drive, drive.file, spreadsheets, documents
  - [ ] Add OAuth configuration to environment variables
- [ ] 1.2 Implement OAuth2 authorization endpoint
  - [ ] Create `/api/auth/google/authorize` route for initiating OAuth flow
  - [ ] Generate Google OAuth consent URL with proper parameters
  - [ ] Implement state parameter for CSRF protection
  - [ ] Add user session tracking during OAuth flow
- [ ] 1.3 Implement OAuth2 callback handler
  - [ ] Create `/api/auth/google/callback` route for handling Google redirects
  - [ ] Validate state parameter to prevent CSRF attacks
  - [ ] Exchange authorization code for access and refresh tokens
  - [ ] Handle OAuth errors and user denial scenarios

### Task 2: Token Management System (AC: 6.1.2, 6.1.5)
- [ ] 2.1 Implement secure token storage
  - [ ] Create OAuth tokens database schema with encrypted storage
  - [ ] Implement AES-256 encryption/decryption utilities
  - [ ] Store access tokens, refresh tokens, and expiry timestamps
  - [ ] Add token metadata (scopes, user_id, created_at, updated_at)
- [ ] 2.2 Implement automatic token refresh
  - [ ] Create token refresh service with expiry checking
  - [ ] Implement background refresh for tokens approaching expiry
  - [ ] Handle refresh token failures and re-authentication flows
  - [ ] Add token refresh logging and monitoring
- [ ] 2.3 Implement token retrieval service
  - [ ] Create service for retrieving valid tokens for API calls
  - [ ] Add automatic refresh trigger during token retrieval
  - [ ] Implement token validation before returning to callers
  - [ ] Add token caching for performance optimization

### Task 3: Access Control & Permission Management (AC: 6.1.3, 6.1.4)
- [ ] 3.1 Implement access revocation
  - [ ] Create `/api/auth/google/revoke` endpoint for disconnecting accounts
  - [ ] Revoke Google tokens via Google OAuth2 revocation endpoint
  - [ ] Remove encrypted tokens from local database
  - [ ] Clear any cached tokens or sessions
- [ ] 3.2 Implement permission validation
  - [ ] Create permission checking service for Google API operations
  - [ ] Validate required scopes before executing API calls
  - [ ] Implement permission error handling and user messaging
  - [ ] Add permission audit logging for security compliance
- [ ] 3.3 Create account management UI
  - [ ] Add Google account connection status to user settings
  - [ ] Implement "Connect Google Account" button and flow
  - [ ] Add "Disconnect Google Account" functionality
  - [ ] Display connected account email and permissions status

### Task 4: Security Implementation (AC: 6.1.5)
- [ ] 4.1 Implement credential security measures
  - [ ] Ensure no OAuth tokens in application logs or error messages
  - [ ] Add input sanitization for OAuth-related parameters
  - [ ] Implement rate limiting for OAuth endpoints
  - [ ] Add security headers for OAuth responses
- [ ] 4.2 Create security monitoring
  - [ ] Add OAuth event logging (connections, disconnections, refreshes)
  - [ ] Implement anomaly detection for suspicious OAuth activity
  - [ ] Create security alerts for token failures or revocations
  - [ ] Add OAuth token usage metrics and monitoring

### Task 5: Testing & Documentation (All ACs)
- [ ] 5.1 Create comprehensive test suite
  - [ ] Unit tests for token encryption/decryption
  - [ ] Integration tests for OAuth flow end-to-end
  - [ ] Token refresh automation tests
  - [ ] Permission validation test cases
  - [ ] Security penetration testing for OAuth endpoints
- [ ] 5.2 Documentation and setup guides
  - [ ] Create Google Cloud Console setup instructions
  - [ ] Document OAuth configuration and environment variables
  - [ ] Add troubleshooting guide for common OAuth issues
  - [ ] Create security best practices documentation

---

## Dev Notes

### Technical Implementation Patterns

**Reuse from Story 3-2 (Google Drive Connector):**
- Token encryption patterns using AES-256 Fernet symmetric encryption
- OAuth2 flow implementation with Google Auth libraries
- Database schema patterns for secure token storage
- Token refresh automation and error handling
- Permission validation and security logging patterns

**Key Extensions for Story 6-1:**
- Extended OAuth scopes beyond Drive to include Docs and Sheets APIs
- Multi-service token management supporting different Google Workspace APIs
- Enhanced permission validation for document/spreadsheet operations
- Account management UI for user-controlled connection/disconnection

### Security Architecture

**Token Storage:**
```
OAuth Tokens (Google) → AES-256 Encryption → PostgreSQL (encrypted_tokens table)
```

**OAuth Flow:**
```
User → Authorize Endpoint → Google Consent → Callback → Token Exchange → Encrypted Storage
```

**Permission Validation:**
```
API Operation → Required Scopes Check → Token Validation → Permission Confirmation → Execution
```

### Project Structure Alignment

**Database Schema:**
- Extend existing OAuth tokens table from Story 3-2 if present
- Follow established naming conventions (snake_case)
- Include audit fields (created_at, updated_at, user_id)
- Add indexes for performance optimization

**Service Architecture:**
- Follow established service patterns from onyx-core/services/
- Use consistent error handling and logging patterns
- Implement health check endpoints for OAuth services
- Maintain separation of concerns (auth, token management, permissions)

**API Design:**
- Follow RESTful conventions established in other API endpoints
- Use consistent response formats and error codes
- Implement proper HTTP status codes and error handling
- Add API documentation following existing patterns

### Integration Points

**Dependencies:**
- Story 1.3: Environment Configuration & Secrets Management (for OAuth credentials)
- Story 3.2: Google Drive Connector patterns (reuse OAuth implementation)
- Supabase: User authentication and session management
- PostgreSQL: Secure token storage and user metadata

**External Services:**
- Google OAuth2 API: Authentication and token management
- Google Workspace APIs: Docs, Sheets, Drive for permission validation
- Google Cloud Console: OAuth client configuration and management

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

---

## Senior Developer Review (AI)

### Review Outcome

[ ] Approved - Ready for Development
[ ] Changes Requested - See Action Items Below
[ ] Blocked - Critical Issues Must Be Addressed

### Security Review

**OAuth2 Implementation:**
- [ ] OAuth flow follows security best practices
- [ ] State parameter implemented for CSRF protection
- [ ] Token encryption meets enterprise security standards
- [ ] Refresh token management handles edge cases properly
- [ ] Permission validation prevents unauthorized access

**Data Protection:**
- [ ] No credentials in logs or error messages verified
- [ ] Encryption key management follows security guidelines
- [ ] Token revocation completely removes access
- [ ] Database access properly secured for token storage

### Technical Review

**Architecture:**
- [ ] OAuth service design follows established patterns
- [ ] Token refresh automation is robust and reliable
- [ ] Permission validation is comprehensive
- [ ] Error handling covers all failure scenarios
- [ ] Performance considerations addressed (caching, optimization)

**Integration:**
- [ ] Reuses existing OAuth implementation from Story 3-2 effectively
- [ ] Properly extends for broader Google Workspace scope requirements
- [ ] User interface integration is seamless and intuitive
- [ ] API design follows project conventions

### Action Items

- [ ] Security review completed
- [ ] Performance testing conducted
- [ ] Documentation verified
- [ ] Integration testing with Stories 6.2-6.5 planned

---

## Change Log

**2025-11-16:** Initial story creation with comprehensive OAuth2 requirements based on sprint status and previous implementation patterns from Story 3-2.

---

## References

- **Source:** docs/sprint-status.yaml (Story 6-1 acceptance criteria and dependencies)
- **Source:** docs/epics.md (Epic 6 scope and Story 6.1 requirements)
- **Source:** docs/architecture.md (System architecture and security patterns)
- **Source:** docs/stories/3-2-google-drive-connector-auto-sync.md (OAuth2 implementation patterns)
- **Technical Reference:** Google OAuth2 Documentation (https://developers.google.com/identity/protocols/oauth2)
- **Technical Reference:** Google Workspace APIs Documentation (https://developers.google.com/workspace)

---

**Last Updated:** 2025-11-16
**Author:** BMAD Create-Story Workflow
**Status:** Drafted - Ready for Development Assignment