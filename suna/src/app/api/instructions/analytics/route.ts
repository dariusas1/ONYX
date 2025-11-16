/**
 * Instruction Analytics API Route
 *
 * API endpoint for providing instruction usage analytics,
 * conflict detection, and effectiveness metrics.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

// GET /api/instructions/analytics - Get analytics for user's instructions
export async function GET(request: NextRequest) {
  try {
    const supabase = createClient();
    const { searchParams } = new URL(request.url);

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const instructionId = searchParams.get('instruction_id');
    const category = searchParams.get('category');

    if (instructionId) {
      // Return analytics for specific instruction
      return await getInstructionAnalytics(supabase, user.id, instructionId);
    } else {
      // Return overall analytics for user
      return await getUserAnalytics(supabase, user.id, category);
    }

  } catch (error) {
    console.error('GET /api/instructions/analytics error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

async function getInstructionAnalytics(supabase: any, userId: string, instructionId: string) {
  try {
    // Get instruction details
    const { data: instruction, error: instructionError } = await supabase
      .from('standing_instructions')
      .select('*')
      .eq('id', instructionId)
      .eq('user_id', userId)
      .single();

    if (instructionError || !instruction) {
      return NextResponse.json(
        { success: false, error: 'Instruction not found' },
        { status: 404 }
      );
    }

    // Calculate usage statistics
    const now = new Date();
    const createdAt = new Date(instruction.created_at);
    const daysSinceCreation = Math.floor((now.getTime() - createdAt.getTime()) / (1000 * 60 * 60 * 24));
    const avgDailyUsage = daysSinceCreation > 0 ? instruction.usage_count / daysSinceCreation : 0;

    // Get recent usage trends (last 30 days)
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const recentUsage = instruction.last_used_at ?
      new Date(instruction.last_used_at) >= thirtyDaysAgo : false;

    const analytics = {
      instruction_id: instructionId,
      category: instruction.category,
      priority: instruction.priority,
      enabled: instruction.enabled,
      total_usage: instruction.usage_count,
      last_used_at: instruction.last_used_at,
      created_at: instruction.created_at,
      days_since_creation,
      avg_daily_usage: Math.round(avgDailyUsage * 100) / 100,
      recent_usage_30_days: recentUsage,
      effectiveness_score: calculateEffectivenessScore(instruction, avgDailyUsage),
      recommendations: generateRecommendations(instruction, avgDailyUsage)
    };

    return NextResponse.json({
      success: true,
      data: analytics
    });

  } catch (error) {
    console.error('Error getting instruction analytics:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to get instruction analytics' },
      { status: 500 }
    );
  }
}

async function getUserAnalytics(supabase: any, userId: string, category?: string | null) {
  try {
    // Build query for user's instructions
    let query = supabase
      .from('standing_instructions')
      .select(`
        id,
        category,
        priority,
        enabled,
        usage_count,
        last_used_at,
        created_at
      `)
      .eq('user_id', userId);

    if (category) {
      query = query.eq('category', category);
    }

    const { data: instructions, error } = await query;

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch instructions' },
        { status: 500 }
      );
    }

    if (!instructions || instructions.length === 0) {
      return NextResponse.json({
        success: true,
        data: {
          total_instructions: 0,
          active_instructions: 0,
          categories: [],
          usage_overview: {
            total_usage: 0,
            avg_usage_per_instruction: 0,
            most_used_instruction: null,
            least_used_instruction: null
          },
          priority_analysis: {
            avg_priority: 0,
            high_priority_count: 0,
            low_priority_count: 0
          },
          effectiveness_metrics: {
            active_instructions_ratio: 0,
            recently_used_ratio: 0,
            overall_effectiveness_score: 0
          }
        }
      });
    }

    // Calculate analytics
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const totalInstructions = instructions.length;
    const activeInstructions = instructions.filter(inst => inst.enabled).length;
    const recentlyUsedInstructions = instructions.filter(inst =>
      inst.last_used_at && new Date(inst.last_used_at) >= thirtyDaysAgo
    ).length;

    // Category breakdown
    const categoryStats = instructions.reduce((acc: any, instruction: any) => {
      const cat = instruction.category;
      if (!acc[cat]) {
        acc[cat] = {
          category: cat,
          total_count: 0,
          active_count: 0,
          total_usage: 0,
          avg_priority: 0,
          unused_count: 0
        };
      }
      acc[cat].total_count++;
      acc[cat].total_usage += instruction.usage_count;
      acc[cat].avg_priority += instruction.priority;
      if (instruction.enabled) acc[cat].active_count++;
      if (instruction.usage_count === 0) acc[cat].unused_count++;
      return acc;
    }, {});

    // Calculate averages for each category
    Object.values(categoryStats).forEach((stats: any) => {
      stats.avg_priority = Math.round((stats.avg_priority / stats.total_count) * 100) / 100;
    });

    // Usage overview
    const totalUsage = instructions.reduce((sum, inst) => sum + inst.usage_count, 0);
    const avgUsagePerInstruction = totalUsage / totalInstructions;
    const mostUsedInstruction = instructions.reduce((max, inst) =>
      inst.usage_count > max.usage_count ? inst : max, instructions[0]
    );
    const leastUsedInstruction = instructions.reduce((min, inst) =>
      inst.usage_count < min.usage_count ? inst : min, instructions[0]
    );

    // Priority analysis
    const priorities = instructions.map(inst => inst.priority);
    const avgPriority = priorities.reduce((sum, p) => sum + p, 0) / priorities.length;
    const highPriorityCount = priorities.filter(p => p >= 8).length;
    const lowPriorityCount = priorities.filter(p <= 3).length;

    // Effectiveness metrics
    const activeInstructionsRatio = activeInstructions / totalInstructions;
    const recentlyUsedRatio = recentlyUsedInstructions / totalInstructions;
    const overallEffectivenessScore = calculateOverallEffectiveness(
      activeInstructionsRatio,
      recentlyUsedRatio,
      avgUsagePerInstruction
    );

    const analytics = {
      total_instructions: totalInstructions,
      active_instructions: activeInstructions,
      categories: Object.values(categoryStats),
      usage_overview: {
        total_usage: totalUsage,
        avg_usage_per_instruction: Math.round(avgUsagePerInstruction * 100) / 100,
        most_used_instruction: {
          id: mostUsedInstruction.id,
          instruction_text: mostUsedInstruction.instruction_text,
          usage_count: mostUsedInstruction.usage_count
        },
        least_used_instruction: {
          id: leastUsedInstruction.id,
          instruction_text: leastUsedInstruction.instruction_text,
          usage_count: leastUsedInstruction.usage_count
        }
      },
      priority_analysis: {
        avg_priority: Math.round(avgPriority * 100) / 100,
        high_priority_count,
        low_priority_count
      },
      effectiveness_metrics: {
        active_instructions_ratio: Math.round(activeInstructionsRatio * 100) / 100,
        recently_used_ratio: Math.round(recentlyUsedRatio * 100) / 100,
        overall_effectiveness_score: Math.round(overallEffectivenessScore * 100) / 100
      }
    };

    return NextResponse.json({
      success: true,
      data: analytics
    });

  } catch (error) {
    console.error('Error getting user analytics:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to get user analytics' },
      { status: 500 }
    );
  }
}

function calculateEffectivenessScore(instruction: any, avgDailyUsage: number): number {
  try {
    let score = 0;

    // Usage frequency (40% weight)
    const usageScore = Math.min(avgDailyUsage * 20, 40); // Max 40 points at 2+ uses/day
    score += usageScore;

    // Recency (30% weight)
    let recencyScore = 0;
    if (instruction.last_used_at) {
      const daysSinceLastUse = (Date.now() - new Date(instruction.last_used_at).getTime()) / (1000 * 60 * 60 * 24);
      recencyScore = Math.max(0, 30 - daysSinceLastUse * 2); // Decay over 15 days
    }
    score += recencyScore;

    // Priority alignment (20% weight)
    const priorityScore = instruction.priority; // 1-10 points
    score += priorityScore;

    // Enabled status (10% weight)
    if (instruction.enabled) {
      score += 10;
    }

    return Math.min(Math.round(score), 100);

  } catch (error) {
    console.warn('Error calculating effectiveness score:', error);
    return 50; // Default to medium effectiveness
  }
}

function generateRecommendations(instruction: any, avgDailyUsage: number): string[] {
  const recommendations = [];

  // Usage-based recommendations
  if (avgDailyUsage < 0.1) {
    recommendations.push('This instruction is rarely used. Consider if it\'s still relevant or needs better context hints.');
  }

  if (avgDailyUsage > 5) {
    recommendations.push('This instruction is heavily used. Ensure it\'s still providing value and not too restrictive.');
  }

  // Recency-based recommendations
  if (!instruction.last_used_at) {
    recommendations.push('This instruction has never been used. Consider reviewing its relevance and context hints.');
  } else {
    const daysSinceLastUse = (Date.now() - new Date(instruction.last_used_at).getTime()) / (1000 * 60 * 60 * 24);
    if (daysSinceLastUse > 30) {
      recommendations.push('This instruction hasn\'t been used in over a month. Consider if it\'s still needed.');
    }
  }

  // Priority-based recommendations
  if (instruction.priority < 3) {
    recommendations.push('This instruction has low priority. Consider if it should be more important or if it can be removed.');
  }

  if (instruction.priority > 8) {
    recommendations.push('This instruction has high priority. Ensure it\'s truly critical and doesn\'t conflict with other important instructions.');
  }

  // Category-specific recommendations
  if (instruction.category === 'communication' && !instruction.enabled) {
    recommendations.push('Communication instructions are generally helpful when enabled. Consider re-enabling this instruction.');
  }

  if (instruction.category === 'security' && !instruction.enabled) {
    recommendations.push('Security instructions are important for protecting your data. Consider reviewing and re-enabling this instruction.');
  }

  return recommendations;
}

function calculateOverallEffectiveness(
  activeRatio: number,
  recentlyUsedRatio: number,
  avgUsage: number
): number {
  try {
    let score = 0;

    // Active instructions ratio (40% weight)
    score += activeRatio * 40;

    // Recently used ratio (30% weight)
    score += recentlyUsedRatio * 30;

    // Average usage (30% weight)
    const usageScore = Math.min(avgUsage * 15, 30); // Max 30 points at 2+ uses/day avg
    score += usageScore;

    return Math.min(Math.round(score), 100);

  } catch (error) {
    console.warn('Error calculating overall effectiveness:', error);
    return 50;
  }
}