# Story 2.6: Response Citation & Source Attribution

## Metadata

**Story ID**: 2-6-response-citation-source-attribution
**Epic**: Epic 2 - Chat Interface & Conversation Management
**Title**: Response Citation & Source Attribution
**Priority**: P1
**Estimated Points**: 8
**Assigned To**: TBD
**Sprint**: Sprint 2
**Status**: drafted
**Created Date**: 2025-11-14
**Started Date**: null
**Completed Date**: null
**Blocked Reason**: null

## User Story

As a user using ONYX for research and analysis, I want every factual claim in AI responses to be traceable to its source document with clickable links, so that I can verify information accuracy and access original documents for deeper context.

## Description

This story implements a comprehensive citation system that ensures every factual claim made by the AI is properly attributed to its source document. The system provides inline citations within the response text, a formatted citation list at the end of each message, and clickable links that allow users to navigate directly to the original source documents.

## Acceptance Criteria

**AC2.6.1**: Each factual claim in AI responses has inline citation [1], [2], etc. immediately following the claim
**AC2.6.2**: Citation list appears at end of each AI message with source details
**AC2.6.3**: Citations show date, source type (Google Drive/Slack/Upload/Web), and document name
**AC2.6.4**: Citations are clickable links when URL is available, opening in new tabs
**AC2.6.5**: Reasoning-only claims are explicitly marked as such with no citation required
**AC2.6.6**: All citations are stored in PostgreSQL database with messages for persistence

## Technical Implementation Summary

### Citation Format and Interface

The system implements TypeScript interfaces for citations and cited responses:

- **Citation Interface**: Includes id, source_type, source_id, title, url, snippet, and timestamp
- **Source Types**: Supports google_drive, slack, upload, and web sources
- **Response Parsing**: Extracts citation references using regex pattern `[(d+)]`
- **Display Formatting**: Formats citations with index, date, source type, and title

### UI Components

- **CitationList Component**: Displays formatted citation list at end of AI messages
- **MessageBubble Integration**: Enhanced to include citation display for assistant messages
- **Clickable Links**: External link icons and proper target="_blank" attributes
- **Source Metadata**: Shows document snippets and contextual information

### Database Schema

- **Message Citations**: Added JSONB column to messages table for citation storage
- **Indexing**: GIN index on citations column for efficient querying
- **Persistence**: Citations stored with messages for historical reference

### RAG Integration (Epic 3 Interface)

- **RAG Result Interface**: Defines structure for retrieval-augmented generation results
- **Citation Creation**: Maps RAG results to citation format automatically
- **Metadata Preservation**: Maintains source document metadata through citation chain

### LLM Prompt Enhancement

- **System Prompt Modification**: Enhanced to include citation instructions
- **Context Integration**: Incorporates relevant documents with citation markers
- **Citation Instructions**: Explicit guidance for LLM on when and how to cite sources

## Dependencies

**Epic Dependencies**:
- Epic 1: Foundation & Infrastructure (PostgreSQL, API infrastructure)

**Story Dependencies**:
- Story 2.4: Message Streaming & Real-Time Response Display (for response integration)
- Story 2.5: System Prompt & Strategic Advisor Tone (for prompt enhancement)
- Epic 3: RAG Integration & Knowledge Retrieval (for source documents and metadata)

## Implementation Tasks

1. **Citation Data Structures** (1 point)
   - Define TypeScript interfaces for Citation and CitedResponse
   - Implement citation parsing and formatting functions

2. **Database Schema Updates** (1 point)
   - Add citations JSONB column to messages table
   - Create GIN index for efficient citation queries
   - Update message creation/update endpoints

3. **Citation UI Components** (2 points)
   - Create CitationList component with proper styling
   - Update MessageBubble to include citations
   - Implement clickable links and external link icons

4. **RAG Integration Interface** (2 points)
   - Define RAG result interfaces for Epic 3
   - Implement citation creation from RAG results
   - Create metadata preservation system

5. **LLM Prompt Enhancement** (1 point)
   - Update system prompt building functions
   - Add citation instructions and context formatting
   - Integrate with existing prompt management

6. **Testing and Validation** (1 point)
   - Unit tests for citation parsing and formatting
   - Integration tests for UI components
   - End-to-end tests for citation flow

## Performance Targets

- **Citation Parsing**: <10ms for typical response (1000 words, 5-10 citations)
- **Database Storage**: <50ms additional time for message saving
- **UI Rendering**: <100ms for citation list display (up to 20 citations)
- **Link Generation**: <5ms per citation for URL creation

## Definition of Done

- [ ] All 6 acceptance criteria satisfied and tested
- [ ] TypeScript interfaces implemented with proper typing
- [ ] Database schema updated with migrations
- [ ] UI components styled according to Manus theme
- [ ] Integration with message streaming completed
- [ ] Documentation updated with citation system usage
- [ ] Code review completed and approved
- [ ] Tests passing with >90% coverage for citation code

## Notes

This story establishes the foundation for trustworthy AI responses by implementing a robust citation system. It's critical for user confidence and enables verification of AI-generated content. The citation system interfaces with Epic 3's RAG functionality but can operate independently with manual citation input for testing purposes.

The implementation prioritizes user experience with clean, readable citations that don't interrupt the flow of conversation while providing essential source attribution. The JSONB storage approach ensures flexibility for future citation format enhancements while maintaining efficient query performance.