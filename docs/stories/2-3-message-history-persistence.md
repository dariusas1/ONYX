# Story 2.3: Message History & Persistence

Status: drafted

## Story

As a strategic founder engaging in extended conversations,
I want my chat messages to be automatically saved and efficiently retrievable with full-text search capabilities,
so that I can reference previous conversations, maintain context across sessions, and quickly find specific information discussed in the past.

## Acceptance Criteria

1. Messages saved to Postgres on send
2. Load last 100 messages per conversation
3. Infinite scroll loads older messages (paginated)
4. Full-text search across all messages works
5. Query performance <100ms for message retrieval
6. Conversation list sorted by recent activity

## Tasks / Subtasks

- [ ] Task 1: Database Schema Implementation (AC: 1, 5, 6)
  - [ ] Subtask 1.1: Create conversations table with proper indexes
  - [ ] Subtask 1.2: Create messages table with full-text search index
  - [ ] Subtask 1.3: Implement conversation timestamp update trigger
  - [ ] Subtask 1.4: Add database migrations and schema validation

- [ ] Task 2: Conversation API Implementation (AC: 6)
  - [ ] Subtask 2.1: Implement GET /api/conversations (list user conversations)
  - [ ] Subtask 2.2: Implement POST /api/conversations (create new conversation)
  - [ ] Subtask 2.3: Add pagination support (limit/offset)
  - [ ] Subtask 2.4: Sort by updated_at DESC for recent activity

- [ ] Task 3: Messages API Implementation (AC: 2, 3, 5)
  - [ ] Subtask 3.1: Implement GET /api/conversations/[id]/messages
  - [ ] Subtask 3.2: Add pagination with cursor-based loading
  - [ ] Subtask 3.3: Implement infinite scroll support
  - [ ] Subtask 3.4: Optimize query performance with proper indexes

- [ ] Task 4: Message Persistence Integration (AC: 1)
  - [ ] Subtask 4.1: Modify chat interface to save messages on send
  - [ ] Subtask 4.2: Implement async message saving to avoid UI blocking
  - [ ] Subtask 4.3: Add error handling for failed message saves
  - [ ] Subtask 4.4: Ensure message order preservation

- [ ] Task 5: Frontend Conversation Management (AC: 2, 3)
  - [ ] Subtask 5.1: Create useConversation hook for message management
  - [ ] Subtask 5.2: Implement message loading with pagination
  - [ ] Subtask 5.3: Add infinite scroll UI component
  - [ ] Subtask 5.4: Handle loading states and error conditions

- [ ] Task 6: Full-Text Search Implementation (AC: 4)
  - [ ] Subtask 6.1: Implement GET /api/search endpoint
  - [ ] Subtask 6.2: Add PostgreSQL full-text search with GIN index
  - [ ] Subtask 6.3: Implement search ranking and relevance scoring
  - [ ] Subtask 6.4: Add search UI component with results display

- [ ] Task 7: Performance Optimization (AC: 5)
  - [ ] Subtask 7.1: Database query optimization and indexing strategy
  - [ ] Subtask 7.2: Implement query result caching where appropriate
  - [ ] Subtask 7.3: Add performance monitoring and logging
  - [ ] Subtask 7.4: Validate <100ms query performance targets

## Dev Notes

### Technical Implementation Summary

**Database Schema:**
- PostgreSQL with UUID primary keys for scalability
- Conversations table tracks chat sessions with user relationships
- Messages table stores individual messages with role-based access
- Full-text search index using PostgreSQL's built-in GIN indexes
- Automated timestamp management with triggers
- Proper foreign key constraints with cascade deletion

**API Architecture:**
- RESTful API design with Next.js App Router
- Authentication middleware using NextAuth session management
- Cursor-based pagination for efficient message loading
- Role-based access control ensuring users only access their conversations
- Optimized SQL queries with proper indexing strategy

**Frontend Implementation:**
- React hooks for conversation and message state management
- Infinite scroll implementation with cursor pagination
- Optimistic UI updates for better user experience
- Search functionality with real-time result display
- Loading states and error handling for robust UX

**Performance Features:**
- Database indexes optimized for common query patterns
- Full-text search with ranking and relevance scoring
- Cursor-based pagination for efficient memory usage
- Async message persistence to prevent UI blocking
- Query performance monitoring to ensure <100ms targets

**Search Implementation:**
- PostgreSQL native full-text search capabilities
- tsvector and tsquery functions for relevance ranking
- Search across message content with conversation context
- Result limiting and ranking for optimal user experience
- Support for complex search queries and phrase matching

## Dependencies

- **Epic 1**: Foundation & Infrastructure (Database setup, authentication)
- **Story 2.1**: Suna UI Deployment with Manus Theme (Chat interface foundation)
- **Story 2.2**: LiteLLM Proxy Setup & Model Routing (Message processing integration)

## Story Metadata

- **Story ID**: 2-3
- **Title**: Message History & Persistence
- **Priority**: P1 (High)
- **Estimated Points**: 13
- **Epic**: Epic 2 - Chat Interface & Conversation Management
- **Sprint**: Sprint 2
- **Assigned To**: TBD
- **Created Date**: 2025-11-14
- **Started Date**: TBD
- **Completed Date**: TBD
- **Blocked Reason**: None
- **Dependencies**: Epic 1, Story 2-1, Story 2-2

## Risk Assessment

**Technical Risks:**
- Database performance at scale with large message volumes
- Full-text search query complexity and performance optimization
- Pagination implementation complexity with cursor-based loading

**Mitigation Strategies:**
- Comprehensive database indexing strategy from the start
- Performance monitoring and query optimization
- Incremental implementation with early performance validation
- Database connection pooling and query optimization

## Definition of Done

- [ ] All acceptance criteria met and validated
- [ ] Database schema implemented with proper migrations
- [ ] API endpoints tested with comprehensive test coverage
- [ ] Frontend components implemented with responsive design
- [ ] Search functionality working with accurate results
- [ ] Performance targets achieved (<100ms query time)
- [ ] Error handling implemented for all failure scenarios
- [ ] Documentation updated for new APIs and database schema
- [ ] Code review completed and approved
- [ ] Integration testing across all components passed