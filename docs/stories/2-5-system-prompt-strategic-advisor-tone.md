# Story 2.5: System Prompt & Strategic Advisor Tone

**Story ID:** 2-5-system-prompt-strategic-advisor-tone
**Epic:** Epic 2 - Chat Interface & Conversation Management
**Status:** drafted
**Priority:** P1
**Estimated Points:** 8
**Assigned to:** TBD
**Sprint:** Sprint 2
**Created Date:** 2025-11-14
**Started Date:** null
**Completed Date:** null
**Blocked Reason:** null

## User Story

**As a** founder using ONYX
**I want** Manus to maintain a consistent strategic advisor persona across all responses
**So that** I receive reliable, well-structured advice with clear reasoning and actionable recommendations

## Description

This story implements the system prompt infrastructure and strategic advisor tone for Manus, ONYX's AI assistant. The system ensures consistent persona, response format, and tone across all interactions while supporting dynamic personalization through standing instructions and user context.

## Technical Implementation Summary

### Core Components

1. **System Prompt Template** (`src/lib/prompts.ts`)
   - Base prompt defining Manus persona and core principles
   - Dynamic context injection for user profile and standing instructions
   - Structured response format requirements

2. **Dynamic System Prompt Loading** (`src/lib/system-prompt.ts`)
   - Database integration for user profile retrieval
   - Standing instructions loading from PostgreSQL
   - Runtime prompt construction per user

3. **Tone Validation System** (`src/lib/tone-validator.ts`)
   - Automated validation of response characteristics
   - Citation, reasoning, and recommendation checking
   - Conciseness and speculation controls

4. **Database Schema**
   - `standing_instructions` table for persistent user preferences
   - Proper indexing and constraint management
   - User association with cascade deletion

## Implementation Details

### System Prompt Template
```typescript
// src/lib/prompts.ts
export function buildSystemPrompt(userContext?: {
  name?: string;
  role?: string;
  standingInstructions?: string[];
}): string {
  const basePrompt = `You are Manus, M3rcury's strategic intelligence advisor. You assist the founding team with high-stakes strategic decisions.

CORE PRINCIPLES:
1. Think step-by-step - show your reasoning process
2. Cite sources for all factual claims - reference specific documents
3. Focus on strategic implications, not just facts
4. Provide actionable recommendations
5. Be concise and direct - no fluff or unnecessary pleasantries
6. Disclose uncertainty when data is incomplete
7. Challenge assumptions constructively

RESPONSE FORMAT:
- Start with a direct answer to the question
- Follow with supporting reasoning (2-3 key points)
- Include relevant citations [1], [2] at end
- End with strategic recommendation or next steps

TONE:
- Professional but conversational
- Confident yet humble about limitations
- Focus on "why" and "what next" not just "what"
- Avoid speculation without clearly marking it as such`;

  let contextSection = '';

  if (userContext) {
    contextSection = '\n\nUSER CONTEXT:';
    if (userContext.name) {
      contextSection += `\n- Name: ${userContext.name}`;
    }
    if (userContext.role) {
      contextSection += `\n- Role: ${userContext.role}`;
    }
    if (userContext.standingInstructions?.length) {
      contextSection += '\n- Standing Instructions:';
      userContext.standingInstructions.forEach(instruction => {
        contextSection += `\n  * ${instruction}`;
      });
    }
  }

  return basePrompt + contextSection;
}
```

### Database Integration
```typescript
// src/lib/system-prompt.ts
import { db } from './db';

export async function getSystemPrompt(userId: string): Promise<string> {
  // Load user profile
  const userResult = await db.query(
    `SELECT display_name, email FROM users WHERE id = $1`,
    [userId]
  );
  const user = userResult.rows[0];

  // Load standing instructions
  const instructionsResult = await db.query(
    `SELECT instruction
     FROM standing_instructions
     WHERE user_id = $1 AND enabled = true
     ORDER BY created_at ASC`,
    [userId]
  );

  const standingInstructions = instructionsResult.rows.map(
    row => row.instruction
  );

  return buildSystemPrompt({
    name: user.display_name,
    role: 'Founder',
    standingInstructions,
  });
}
```

### Tone Validation
```typescript
// src/lib/tone-validator.ts
interface ToneCheck {
  hasCitations: boolean;
  hasReasoning: boolean;
  hasRecommendation: boolean;
  isConcise: boolean;
  avoidsSpeculation: boolean;
}

export function validateTone(response: string): ToneCheck {
  return {
    hasCitations: /\[\d+\]/.test(response),
    hasReasoning: response.toLowerCase().includes('because') ||
                   response.toLowerCase().includes('since'),
    hasRecommendation: response.toLowerCase().includes('recommend') ||
                        response.toLowerCase().includes('should'),
    isConcise: response.split(' ').length < 500,
    avoidsSpeculation: !response.toLowerCase().includes('maybe') ||
                        response.includes('uncertain') ||
                        response.includes('unclear')
  };
}
```

### Database Schema
```sql
-- Standing instructions table
CREATE TABLE standing_instructions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  instruction TEXT NOT NULL,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standing_instructions_user ON standing_instructions(user_id, enabled);
```

## Dependencies

- **Story 2.3**: Message History & Persistence (for user context and conversation history)
- **Epic 1**: Foundation & Infrastructure (database setup, user management)

## Acceptance Criteria

- **AC2.5.1**: System prompt prepended to all LLM requests
- **AC2.5.2**: Responses include step-by-step reasoning
- **AC2.5.3**: Sources cited for factual claims
- **AC2.5.4**: Strategic implications highlighted
- **AC2.5.5**: Actionable recommendations provided
- **AC2.5.6**: Tone is professional and direct
- **AC2.5.7**: Standing instructions loaded from database
- **AC2.5.8**: Tone validation passes automated checks

## Test Cases

### Example Prompts for Testing
```typescript
// tests/fixtures/test-prompts.ts
export const TEST_PROMPTS = [
  {
    query: "What's our competitive advantage vs Anthropic?",
    expectedTone: [
      'step-by-step reasoning',
      'cited sources',
      'strategic implications',
      'actionable recommendation'
    ]
  },
  {
    query: "Should we pivot to defense contracts?",
    expectedTone: [
      'direct answer first',
      'pros and cons analysis',
      'risk assessment',
      'clear recommendation with rationale'
    ]
  },
  {
    query: "What was Q3 revenue?",
    expectedTone: [
      'specific number with source',
      'context (vs target, vs Q2)',
      'implications for strategy',
      'data quality disclosure if uncertain'
    ]
  }
];
```

## Performance Requirements

- System prompt construction: <50ms
- Database query for standing instructions: <100ms
- Tone validation: <10ms per response
- Total overhead per request: <200ms

## Notes

- This story establishes the foundation for consistent AI personality across all ONYX interactions
- Standing instructions enable user personalization while maintaining core persona
- Tone validation ensures quality control without restricting helpful responses
- Database-driven approach allows for dynamic updates and A/B testing of prompts
- Integration with message history (Story 2.3) provides conversation context for better responses

## Files to be Created/Modified

- `src/lib/prompts.ts` - System prompt template and construction logic
- `src/lib/system-prompt.ts` - Database integration and dynamic loading
- `src/lib/tone-validator.ts` - Response validation framework
- `src/db/migrations/002_standing_instructions.sql` - Database schema
- `tests/prompts.test.ts` - Comprehensive test suite
- `src/app/api/chat/route.ts` - Integration with chat endpoint