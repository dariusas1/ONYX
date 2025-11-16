/**
 * Types for Standing Instructions Management
 */

export interface StandingInstruction {
  id: string;
  user_id: string;
  instruction_text: string;
  category: InstructionCategory;
  priority: number;
  context_hints: string[];
  enabled: boolean;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export type InstructionCategory = 'workflow' | 'decision' | 'communication' | 'security' | 'general';

export interface InstructionCreateRequest {
  instruction_text: string;
  category: InstructionCategory;
  priority?: number;
  context_hints?: string[];
  enabled?: boolean;
}

export interface InstructionUpdateRequest {
  instruction_text?: string;
  category?: InstructionCategory;
  priority?: number;
  context_hints?: string[];
  enabled?: boolean;
}

export interface InstructionAnalytics {
  overall_stats: {
    total_instructions: number;
    enabled_instructions: number;
    disabled_instructions: number;
    total_usage: number;
    avg_usage: number;
    max_usage: number;
    last_used: string | null;
  };
  category_breakdown: Array<{
    category: string;
    count: number;
    total_usage: number;
    avg_priority: number;
  }>;
  top_instructions: Array<{
    id: string;
    instruction_text: string;
    category: string;
    priority: number;
    usage_count: number;
    last_used_at: string | null;
  }>;
  generated_at: string;
}

export interface CategoryInfo {
  value: InstructionCategory;
  label: string;
  icon: string;
  color: string;
  description: string;
}

export interface BulkStatusUpdate {
  instruction_ids: string[];
  enabled: boolean;
}

export interface InstructionTestResult {
  message: string;
  injection: {
    user_id: string;
    conversation_id: string;
    instructions_count: number;
    memories_count: number;
    injection_time_ms: number;
    performance_stats: Record<string, any>;
    instructions: StandingInstruction[];
  };
}