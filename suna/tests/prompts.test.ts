// =============================================================================
// ONYX System Prompts and Tone Validation Test Suite
// =============================================================================
// Comprehensive tests for Manus persona, system prompt construction, and tone validation
// =============================================================================

import {
  buildSystemPrompt,
  validateSystemPrompt,
  getSystemPromptPreview,
  MANUS_PERSONA,
  buildBasePersonaPrompt,
  buildUserContextPrompt,
  buildStandingInstructionsPrompt,
  buildConversationContextPrompt
} from '@/lib/prompts';

import { validateTone, quickValidateTone } from '@/lib/tone-validator';

// Mock data for testing
const mockUserProfile = {
  id: 'user-123',
  name: 'John Doe',
  email: 'john@example.com',
  context: {
    company: 'TechStart Inc',
    industry: 'Technology',
    role: 'CEO',
    stage: 'prototype' as const
  },
  preferences: {
    communicationStyle: 'direct' as const,
    tone: 'professional' as const,
    citationStyle: 'numeric' as const
  }
};

const mockStandingInstructions = [
  {
    id: 'inst-1',
    user_id: 'user-123',
    content: 'Always provide concrete examples',
    priority: 8,
    enabled: true,
    category: 'general',
    conditions: {},
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    id: 'inst-2',
    user_id: 'user-123',
    content: 'Include implementation timeline when possible',
    priority: 6,
    enabled: true,
    category: 'recommendations',
    conditions: {},
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    id: 'inst-3',
    user_id: 'user-123',
    content: 'Cite at least 2 sources for factual claims',
    priority: 9,
    enabled: true,
    category: 'citations',
    conditions: {},
    created_at: new Date(),
    updated_at: new Date()
  }
];

// =============================================================================
// Manus Persona Tests
// =============================================================================

describe('Manus Persona', () => {
  test('MANUS_PERSONA should have required properties', () => {
    expect(MANUS_PERSONA).toHaveProperty('name', 'Manus');
    expect(MANUS_PERSONA).toHaveProperty('role', 'Strategic Advisor for Founders');
    expect(MANUS_PERSONA).toHaveProperty('description');
    expect(MANUS_PERSONA).toHaveProperty('tone');
    expect(MANUS_PERSONA).toHaveProperty('characteristics');
  });

  test('Manus persona tone should be professional and evidence-based', () => {
    expect(MANUS_PERSONA.tone.professional).toBe(true);
    expect(MANUS_PERSONA.tone.direct).toBe(true);
    expect(MANUS_PERSONA.tone.structured).toBe(true);
    expect(MANUS_PERSONA.tone.evidence_based).toBe(true);
  });

  test('Manus persona should have comprehensive characteristics', () => {
    expect(Array.isArray(MANUS_PERSONA.characteristics)).toBe(true);
    expect(MANUS_PERSONA.characteristics.length).toBeGreaterThan(0);
    expect(MANUS_PERSONA.characteristics).toContain('Provides step-by-step reasoning');
    expect(MANUS_PERSONA.characteristics).toContain('Cites sources for factual claims');
  });
});

// =============================================================================
// System Prompt Construction Tests
// =============================================================================

describe('System Prompt Construction', () => {
  test('buildBasePersonaPrompt should return non-empty string', () => {
    const prompt = buildBasePersonaPrompt();
    expect(typeof prompt).toBe('string');
    expect(prompt.length).toBeGreaterThan(100);
    expect(prompt).toContain('Manus');
    expect(prompt).toContain('Strategic Advisor');
  });

  test('buildUserContextPrompt should handle undefined user', () => {
    const prompt = buildUserContextPrompt(undefined);
    expect(prompt).toBe('');
  });

  test('buildUserContextPrompt should include user information', () => {
    const prompt = buildUserContextPrompt(mockUserProfile);
    expect(prompt).toContain('John Doe');
    expect(prompt).toContain('TechStart Inc');
    expect(prompt).toContain('CEO');
    expect(prompt).toContain('prototype');
  });

  test('buildStandingInstructionsPrompt should handle empty instructions', () => {
    const prompt = buildStandingInstructionsPrompt([]);
    expect(prompt).toBe('');
  });

  test('buildStandingInstructionsPrompt should include instructions', () => {
    const prompt = buildStandingInstructionsPrompt(mockStandingInstructions);
    expect(prompt).toContain('STANDING INSTRUCTIONS:');
    expect(prompt).toContain('Always provide concrete examples');
    expect(prompt).toContain('Priority: 8');
    expect(prompt).toContain('citations');
  });

  test('buildStandingInstructionsPrompt should sort by priority', () => {
    const mixedInstructions = [
      { ...mockStandingInstructions[0], priority: 3 },
      { ...mockStandingInstructions[1], priority: 9 }
    ];

    const prompt = buildStandingInstructionsPrompt(mixedInstructions);
    const lines = prompt.split('\n');

    // The higher priority (9) should come before priority 3
    const priority9Index = lines.findIndex(line => line.includes('Priority: 9'));
    const priority3Index = lines.findIndex(line => line.includes('Priority: 3'));

    expect(priority9Index).toBeLessThan(priority3Index);
  });

  test('buildConversationContextPrompt should handle undefined context', () => {
    const prompt = buildConversationContextPrompt(undefined);
    expect(prompt).toBe('');
  });

  test('buildConversationContextPrompt should include context information', () => {
    const context = {
      currentConversation: {
        topic: 'Business strategy',
        length: 5,
        userGoal: 'Get funding advice'
      },
      sessionInfo: {
        sessionId: 'session-123',
        timestamp: new Date('2024-01-15T10:00:00Z')
      }
    };

    const prompt = buildConversationContextPrompt(context);
    expect(prompt).toContain('Business strategy');
    expect(prompt).toContain('5');
    expect(prompt).toContain('Get funding advice');
    expect(prompt).toContain('session-123');
  });

  test('buildSystemPrompt should combine all components', () => {
    const components = {
      basePersona: MANUS_PERSONA,
      userProfile: mockUserProfile,
      standingInstructions: mockStandingInstructions,
      context: {
        currentConversation: {
          topic: 'Startup advice'
        },
        sessionInfo: {
          sessionId: 'test-session',
          timestamp: new Date()
        }
      }
    };

    const prompt = buildSystemPrompt(components);

    expect(prompt).toContain('Manus');
    expect(prompt).toContain('Strategic Advisor');
    expect(prompt).toContain('John Doe');
    expect(prompt).toContain('TechStart Inc');
    expect(prompt).toContain('STANDING INSTRUCTIONS:');
    expect(prompt).toContain('Always provide concrete examples');
    expect(prompt).toContain('Startup advice');
    expect(prompt).toContain('test-session');
  });

  test('buildSystemPrompt should work with minimal components', () => {
    const components = {
      basePersona: MANUS_PERSONA,
      standingInstructions: []
    };

    const prompt = buildSystemPrompt(components);
    expect(typeof prompt).toBe('string');
    expect(prompt.length).toBeGreaterThan(50);
    expect(prompt).toContain('Manus');
  });
});

// =============================================================================
// System Prompt Validation Tests
// =============================================================================

describe('System Prompt Validation', () => {
  test('validateSystemPrompt should accept valid prompt', () => {
    const validPrompt = buildBasePersonaPrompt();
    const result = validateSystemPrompt(validPrompt);

    expect(result.isValid).toBe(true);
    expect(result.score).toBeGreaterThan(70);
    expect(Array.isArray(result.issues)).toBe(true);
    expect(Array.isArray(result.suggestions)).toBe(true);
  });

  test('validateSystemPrompt should reject prompt without Manus', () => {
    const invalidPrompt = 'You are a helpful assistant.';
    const result = validateSystemPrompt(invalidPrompt);

    expect(result.isValid).toBe(false);
    expect(result.score).toBeLessThan(70);
    expect(result.issues).toContainEqual(
      expect.objectContaining({
        category: 'persona',
        message: expect.stringContaining('Missing Manus persona identification')
      })
    );
  });

  test('validateSystemPrompt should handle very short prompts', () => {
    const shortPrompt = 'You are Manus.';
    const result = validateSystemPrompt(shortPrompt);

    expect(result.isValid).toBe(false);
    expect(result.issues.some(issue =>
      issue.message.includes('too short')
    )).toBe(true);
  });

  test('validateSystemPrompt should handle very long prompts', () => {
    const longPrompt = 'Manus '.repeat(1000);
    const result = validateSystemPrompt(longPrompt);

    expect(result.isValid).toBe(false);
    expect(result.issues.some(issue =>
      issue.message.includes('too long')
    )).toBe(true);
  });

  test('getSystemPromptPreview should work without user data', () => {
    const preview = getSystemPromptPreview({
      basePersona: MANUS_PERSONA,
      standingInstructions: mockStandingInstructions,
      context: undefined
    });

    expect(typeof preview).toBe('string');
    expect(preview).toContain('Manus');
    expect(preview).toContain('Sample Founder');
  });
});

// =============================================================================
// Tone Validation Tests
// =============================================================================

describe('Tone Validation', () => {
  test('validateTone should accept well-structured response', () => {
    const goodResponse = `
      Analysis: This situation requires careful consideration of multiple factors.

      Based on research from [Smith, 2023], the market opportunity appears significant.
      The data from TechCrunch [1] supports this conclusion.

      Strategic Implications:
      - This move could strengthen our market position
      - There's a risk of overextending resources

      Recommendations:
      1. Conduct additional market research (Timeline: 2 weeks)
      2. Develop implementation plan (Timeline: 4 weeks)
      3. Monitor competitor responses

      Success Metrics: Revenue growth of 15% within 6 months
    `;

    const result = validateTone(goodResponse);

    expect(result.isValid).toBe(true);
    expect(result.overallScore).toBeGreaterThan(70);
    expect(result.categories.citations.passed).toBe(true);
    expect(result.categories.reasoning.passed).toBe(true);
    expect(result.categories.recommendations.passed).toBe(true);
  });

  test('validateTone should reject response without citations', () => {
    const responseWithoutCitations = `
      Analysis: This situation requires careful consideration.

      Strategic Implications:
      - Market opportunity exists
      - Resource constraints apply

      Recommendations:
      1. Research the market
      2. Create a plan
    `;

    const result = validateTone(responseWithoutCitations);

    expect(result.categories.citations.passed).toBe(false);
    expect(result.categories.citations.score).toBeLessThan(50);
  });

  test('validateTone should reject response without recommendations', () => {
    const responseWithoutRecommendations = `
      Analysis: This situation requires careful consideration [1].

      Evidence shows the market opportunity is significant [2].

      Strategic Implications:
      - Strong position in market
      - Growth potential exists

      The overall outlook is positive.
    `;

    const result = validateTone(responseWithoutRecommendations);

    expect(result.categories.recommendations.passed).toBe(false);
    expect(result.categories.recommendations.score).toBeLessThan(50);
  });

  test('validateTone should detect unprofessional language', () => {
    const unprofessionalResponse = `
      Analysis: This situation requires amazing consideration.

      This revolutionary opportunity will guarantee success!

      Recommendations:
      1. Use this secret formula
      2. Get rich quick
    `;

    const result = validateTone(unprofessionalResponse);

    expect(result.categories.professionalTone.passed).toBe(false);
    expect(result.categories.professionalTone.score).toBeLessThan(70);
  });

  test('validateTone should handle empty or short responses', () => {
    const shortResponse = 'Okay, let me think about this.';

    const result = validateTone(shortResponse);

    expect(result.isValid).toBe(false);
    expect(result.overallScore).toBeLessThan(70);
  });

  test('quickValidateTone should provide simplified validation', () => {
    const response = `
      Based on research [1], this is a good opportunity.

      Strategic implications include market positioning advantages.

      Recommendation: Implement this approach within 2 weeks.
    `;

    const result = quickValidateTone(response);

    expect(typeof result.isValid).toBe('boolean');
    expect(typeof result.score).toBe('number');
    expect(Array.isArray(result.criticalIssues)).toBe(true);
  });

  test('validateTone should provide detailed metrics', () => {
    const response = `
      Analysis: First, we need to consider the market conditions. Next, we should evaluate our competitive position. Therefore, this approach seems viable.

      Research indicates [1] that the market size is substantial. Additionally, expert opinions [2] suggest strong growth potential.

      Strategic Implications:
      This move could strengthen our market position. However, resource constraints must be considered.

      Recommendations:
      Action: Conduct market research (Timeline: 3 weeks)
      Implementation: Develop go-to-market strategy (Timeline: 6 weeks)
      Success Metrics: Customer acquisition cost under $50
    `;

    const result = validateTone(response);

    expect(result.metrics.totalWords).toBeGreaterThan(50);
    expect(result.metrics.readingTime).toBeGreaterThan(0);
    expect(result.metrics.structureScore).toBeGreaterThan(0);
    expect(result.metrics.complianceScore).toBeGreaterThan(0);
  });

  test('validateTone should handle strict mode configuration', () => {
    const response = `
      Analysis: This is decent advice [1].

      Strategic implications exist.

      Recommendation: Do this.
    `;

    const result = validateTone(response, { strictMode: true });

    expect(result.isValid).toBe(false);
    expect(result.overallScore).toBeLessThan(85);
  });

  test('validateTone should handle custom configuration', () => {
    const response = `
      Analysis: This is good advice [1][2].

      Strategic implications are clear.

      Recommendations:
      1. First step
      2. Second step
      3. Third step
    `;

    const result = validateTone(response, {
      minCitations: 2,
      minRecommendations: 3,
      requireStrategicImplications: true
    });

    expect(result.categories.citations.passed).toBe(true);
    expect(result.categories.recommendations.passed).toBe(true);
    expect(result.categories.strategicImplications.passed).toBe(true);
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Integration Tests', () => {
  test('should build and validate complete system prompt', () => {
    const components = {
      basePersona: MANUS_PERSONA,
      userProfile: mockUserProfile,
      standingInstructions: mockStandingInstructions,
      context: {
        currentConversation: {
          topic: 'Product launch strategy',
          length: 10,
          userGoal: 'Successful market entry'
        },
        sessionInfo: {
          sessionId: 'integration-test',
          timestamp: new Date()
        }
      }
    };

    const systemPrompt = buildSystemPrompt(components);
    const validation = validateSystemPrompt(systemPrompt);
    const toneValidation = validateTone(systemPrompt);

    expect(validation.isValid).toBe(true);
    expect(validation.score).toBeGreaterThan(70);
    expect(typeof toneValidation).toBe('object');
    expect(systemPrompt).toContain('Manus');
    expect(systemPrompt).toContain('TechStart Inc');
    expect(systemPrompt).toContain('Always provide concrete examples');
    expect(systemPrompt).toContain('Product launch strategy');
  });

  test('should handle edge cases gracefully', () => {
    // Test with empty components
    const emptyComponents = {
      basePersona: MANUS_PERSONA,
      standingInstructions: [],
      context: undefined
    };

    const systemPrompt = buildSystemPrompt(emptyComponents);
    const validation = validateSystemPrompt(systemPrompt);

    expect(typeof systemPrompt).toBe('string');
    expect(systemPrompt.length).toBeGreaterThan(50);
    expect(validation.isValid).toBe(true);
  });

  test('should maintain performance targets', () => {
    const components = {
      basePersona: MANUS_PERSONA,
      userProfile: mockUserProfile,
      standingInstructions: mockStandingInstructions.slice(0, 10), // Test with many instructions
      context: {
        currentConversation: {
          topic: 'Complex strategic planning scenario with multiple stakeholders and long-term implications',
          length: 50,
          userGoal: 'Achieve sustainable growth while maintaining competitive advantage'
        },
        sessionInfo: {
          sessionId: 'performance-test',
          timestamp: new Date()
        }
      }
    };

    const startTime = Date.now();
    const systemPrompt = buildSystemPrompt(components);
    const buildTime = Date.now() - startTime;

    expect(buildTime).toBeLessThan(100); // Should build in under 100ms
    expect(systemPrompt.length).toBeGreaterThan(0);
  });
});