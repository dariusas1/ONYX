/**
 * Instruction Evaluation API Route
 *
 * API endpoint for evaluating instructions in conversation context,
 * detecting conflicts, and providing usage analytics.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

// POST /api/instructions/evaluate - Evaluate instructions for conversation context
export async function POST(request: NextRequest) {
  try {
    const supabase = createClient();

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const body = await request.json();

    if (!body.conversation_context) {
      return NextResponse.json(
        { success: false, error: 'Conversation context is required' },
        { status: 400 }
      );
    }

    const startTime = Date.now();

    // Get active instructions for user
    const { data: instructions, error } = await supabase
      .from('standing_instructions')
      .select(`
        id,
        instruction_text,
        priority,
        category,
        enabled,
        context_hints,
        usage_count,
        last_used_at,
        created_at,
        updated_at
      `)
      .eq('user_id', user.id)
      .eq('enabled', true)
      .order('priority', { ascending: false })
      .order('usage_count', { ascending: false });

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch instructions' },
        { status: 500 }
      );
    }

    const context = body.conversation_context;
    const activeInstructions = [];
    const appliedInstructionIds = [];

    // Filter instructions based on context relevance
    for (const instruction of instructions || []) {
      if (isInstructionRelevant(instruction, context)) {
        const relevanceScore = calculateRelevanceScore(instruction, context);
        activeInstructions.push({
          ...instruction,
          relevance_score,
          application_reason: getApplicationReason(instruction, context)
        });
        appliedInstructionIds.push(instruction.id);
      }
    }

    // Sort by relevance score
    activeInstructions.sort((a, b) => b.relevance_score - a.relevance_score);

    // Update usage statistics
    if (appliedInstructionIds.length > 0) {
      const { error: updateError } = await supabase
        .from('standing_instructions')
        .update({
          usage_count: supabase.sql('usage_count + 1'),
          last_used_at: new Date().toISOString()
        })
        .in('id', appliedInstructionIds)
        .eq('user_id', user.id);

      if (updateError) {
        console.warn('Failed to update usage stats:', updateError);
        // Don't fail the request - this is non-critical
      }
    }

    // Detect conflicts
    const conflicts = detectConflicts(activeInstructions);

    const evaluationTime = Date.now() - startTime;

    const result = {
      success: true,
      data: {
        active_instructions: activeInstructions,
        evaluation_time_ms: evaluationTime,
        total_evaluated: instructions?.length || 0,
        conflicts_detected: conflicts,
        applied_count: activeInstructions.length
      }
    };

    return NextResponse.json(result);

  } catch (error) {
    console.error('POST /api/instructions/evaluate error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

function isInstructionRelevant(instruction: any, context: any): boolean {
  try {
    const contextHints = instruction.context_hints || {};

    // Check topic relevance
    if (contextHints.topics && contextHints.topics.length > 0) {
      const messageContent = (context.messageContent || '').toLowerCase();
      const hasMatchingTopic = contextHints.topics.some((topic: string) =>
        messageContent.includes(topic.toLowerCase())
      );
      if (!hasMatchingTopic) return false;
    }

    // Check agent mode relevance
    if (contextHints.agentModes && contextHints.agentModes.length > 0) {
      if (!contextHints.agentModes.includes(context.agentMode)) {
        return false;
      }
    }

    // Check confidence threshold
    if (contextHints.minConfidence !== undefined) {
      if (context.confidence < contextHints.minConfidence) {
        return false;
      }
    }

    // Check keywords
    if (contextHints.keywords && contextHints.keywords.length > 0) {
      const messageContent = (context.messageContent || '').toLowerCase();
      const hasMatchingKeyword = contextHints.keywords.some((keyword: string) =>
        messageContent.includes(keyword.toLowerCase())
      );
      if (!hasMatchingKeyword) return false;
    }

    // Check exclude topics
    if (contextHints.excludeTopics && contextHints.excludeTopics.length > 0) {
      const messageContent = (context.messageContent || '').toLowerCase();
      const hasExcludedTopic = contextHints.excludeTopics.some((topic: string) =>
        messageContent.includes(topic.toLowerCase())
      );
      if (hasExcludedTopic) return false;
    }

    // Check category-specific conditions
    switch (instruction.category) {
      case 'security':
        return (context.involvesSensitiveData || context.requiresSecureHandling);
      case 'workflow':
        return (context.isAgentMode || context.isTaskExecution);
      case 'communication':
        return true; // Communication instructions always relevant
      default:
        return true;
    }

  } catch (error) {
    console.warn('Error checking instruction relevance:', error);
    return true; // Default to relevant if there's an error
  }
}

function calculateRelevanceScore(instruction: any, context: any): number {
  try {
    let score = 0;

    // Base score from priority (0-10 points, 60% weight)
    score += (instruction.priority / 10) * 0.6;

    // Usage frequency (0-10 points, 30% weight)
    const usageScore = Math.min(instruction.usage_count / 10, 1) * 0.3;
    score += usageScore;

    // Recency bonus (0-10 points, 10% weight)
    let recencyScore = 0;
    if (instruction.last_used_at) {
      const daysSinceLastUse = (Date.now() - new Date(instruction.last_used_at).getTime()) / (1000 * 60 * 60 * 24);
      recencyScore = Math.max(0, 1 - daysSinceLastUse / 7) * 0.1; // Decay over 7 days
    }
    score += recencyScore;

    return Math.round(score * 100) / 100; // Round to 2 decimal places

  } catch (error) {
    console.warn('Error calculating relevance score:', error);
    return 0.5; // Default to medium relevance
  }
}

function getApplicationReason(instruction: any, context: any): string {
  try {
    const reasons = [];

    const contextHints = instruction.context_hints || {};

    // Check topic match
    if (contextHints.topics && contextHints.topics.length > 0) {
      const messageContent = (context.messageContent || '').toLowerCase();
      const matchingTopics = contextHints.topics.filter((topic: string) =>
        messageContent.includes(topic.toLowerCase())
      );
      if (matchingTopics.length > 0) {
        reasons.push(`Topic match: ${matchingTopics.join(', ')}`);
      }
    }

    // Check agent mode match
    if (contextHints.agentModes && contextHints.agentModes.includes(context.agentMode)) {
      reasons.push(`Agent mode: ${context.agentMode}`);
    }

    // Check keyword match
    if (contextHints.keywords && contextHints.keywords.length > 0) {
      const messageContent = (context.messageContent || '').toLowerCase();
      const matchingKeywords = contextHints.keywords.filter((keyword: string) =>
        messageContent.includes(keyword.toLowerCase())
      );
      if (matchingKeywords.length > 0) {
        reasons.push(`Keyword match: ${matchingKeywords.join(', ')}`);
      }
    }

    // Category-specific reasons
    if (instruction.category === 'security' && (context.involvesSensitiveData || context.requiresSecureHandling)) {
      reasons.push('Security context detected');
    }

    if (instruction.category === 'workflow' && (context.isAgentMode || context.isTaskExecution)) {
      reasons.push('Workflow context detected');
    }

    return reasons.length > 0 ? reasons.join('; ') : 'General applicability';

  } catch (error) {
    console.warn('Error getting application reason:', error);
    return 'General applicability';
  }
}

function detectConflicts(instructions: any[]): any[] {
  try {
    const conflicts = [];

    for (let i = 0; i < instructions.length; i++) {
      for (let j = i + 1; j < instructions.length; j++) {
        const instruction1 = instructions[i];
        const instruction2 = instructions[j];

        const conflict = detectConflictBetweenInstructions(instruction1, instruction2);
        if (conflict) {
          conflicts.push(conflict);
        }
      }
    }

    return conflicts;

  } catch (error) {
    console.warn('Error detecting conflicts:', error);
    return [];
  }
}

function detectConflictBetweenInstructions(instruction1: any, instruction2: any): any | null {
  try {
    const text1 = (instruction1.instruction_text || '').toLowerCase();
    const text2 = (instruction2.instruction_text || '').toLowerCase();

    // Direct contradictions
    const contradictoryPairs = [
      ['always', 'never'],
      ['do', "don't"],
      ['should', "shouldn't"],
      ['must', 'must not'],
      ['formal', 'casual'],
      ['brief', 'detailed'],
      ['fast', 'thorough']
    ];

    for (const [word1, word2] of contradictoryPairs) {
      if (text1.includes(word1) && text2.includes(word2)) {
        return {
          instruction_1_id: instruction1.id,
          instruction_1_text: instruction1.instruction_text,
          instruction_2_id: instruction2.id,
          instruction_2_text: instruction2.instruction_text,
          conflict_type: 'direct_contradiction',
          severity: 'high',
          resolution_suggestion: `Consider which instruction should take priority based on the specific context`
        };
      }
    }

    // Priority conflicts (different priorities for similar instructions)
    if (instruction1.category === instruction2.category &&
        Math.abs(instruction1.priority - instruction2.priority) > 3) {
      return {
        instruction_1_id: instruction1.id,
        instruction_1_text: instruction1.instruction_text,
        instruction_2_id: instruction2.id,
        instruction_2_text: instruction2.instruction_text,
        conflict_type: 'priority_conflict',
        severity: 'medium',
        resolution_suggestion: `Instructions have significantly different priorities (${instruction1.priority} vs ${instruction2.priority}) in the same category`
      };
    }

    // Security vs workflow conflicts
    if ((instruction1.category === 'security' && instruction2.category === 'workflow') ||
        (instruction2.category === 'security' && instruction1.category === 'workflow')) {
      return {
        instruction_1_id: instruction1.id,
        instruction_1_text: instruction1.instruction_text,
        instruction_2_id: instruction2.id,
        instruction_2_text: instruction2.instruction_text,
        conflict_type: 'security_workflow_conflict',
        severity: 'medium',
        resolution_suggestion: 'Security requirements should take precedence over workflow preferences'
      };
    }

    return null;

  } catch (error) {
    console.warn('Error detecting conflict between instructions:', error);
    return null;
  }
}