/**
 * Frontend Instruction Service
 *
 * Service layer for making API calls to the standing instructions backend.
 * Provides a clean interface for React components to interact with instruction management.
 */

import {
  StandingInstruction,
  CreateInstructionRequest,
  UpdateInstructionRequest,
  InstructionFilters,
  BulkOperationRequest,
  BulkOperationResponse,
  InstructionAnalytics,
  ConversationContext,
  InstructionEvaluationResult
} from '@/lib/types/instructions';

class InstructionService {
  private baseUrl = '/api/instructions';

  // Instruction CRUD Operations
  async getInstructions(filters?: InstructionFilters): Promise<StandingInstruction[]> {
    try {
      const params = new URLSearchParams();

      if (filters?.category) params.append('category', filters.category);
      if (filters?.enabled !== undefined) params.append('enabled', filters.enabled.toString());
      if (filters?.priority_min !== undefined) params.append('priority_min', filters.priority_min.toString());
      if (filters?.priority_max !== undefined) params.append('priority_max', filters.priority_max.toString());
      if (filters?.search) params.append('search', filters.search);
      if (filters?.sort_by) params.append('sort_by', filters.sort_by);
      if (filters?.sort_order) params.append('sort_order', filters.sort_order);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.offset) params.append('offset', filters.offset.toString());

      const response = await fetch(`${this.baseUrl}?${params.toString()}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch instructions');
      }

      return result.data.instructions;
    } catch (error) {
      console.error('Error fetching instructions:', error);
      throw error;
    }
  }

  async getInstructionById(id: string): Promise<StandingInstruction> {
    try {
      const response = await fetch(`${this.baseUrl}/${id}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch instruction');
      }

      return result.data;
    } catch (error) {
      console.error('Error fetching instruction:', error);
      throw error;
    }
  }

  async createInstruction(data: CreateInstructionRequest): Promise<StandingInstruction> {
    try {
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to create instruction');
      }

      return result.data;
    } catch (error) {
      console.error('Error creating instruction:', error);
      throw error;
    }
  }

  async updateInstruction(id: string, data: UpdateInstructionRequest): Promise<StandingInstruction> {
    try {
      const response = await fetch(`${this.baseUrl}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to update instruction');
      }

      return result.data;
    } catch (error) {
      console.error('Error updating instruction:', error);
      throw error;
    }
  }

  async deleteInstruction(id: string, softDelete: boolean = true): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/${id}?soft=${softDelete}`, {
        method: 'DELETE'
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to delete instruction');
      }
    } catch (error) {
      console.error('Error deleting instruction:', error);
      throw error;
    }
  }

  // Bulk Operations
  async bulkOperation(data: BulkOperationRequest): Promise<BulkOperationResponse> {
    try {
      const response = await fetch(this.baseUrl, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to perform bulk operation');
      }

      return result.data;
    } catch (error) {
      console.error('Error performing bulk operation:', error);
      throw error;
    }
  }

  // Instruction Evaluation
  async evaluateInstructions(context: ConversationContext): Promise<InstructionEvaluationResult> {
    try {
      const response = await fetch(`${this.baseUrl}/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_context: context })
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to evaluate instructions');
      }

      return result.data;
    } catch (error) {
      console.error('Error evaluating instructions:', error);
      throw error;
    }
  }

  // Analytics
  async getAnalytics(instructionId?: string): Promise<InstructionAnalytics | any> {
    try {
      const params = instructionId ? `?instruction_id=${instructionId}` : '';
      const response = await fetch(`${this.baseUrl}/analytics${params}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch analytics');
      }

      return result.data;
    } catch (error) {
      console.error('Error fetching analytics:', error);
      throw error;
    }
  }

  // Utility Methods
  validateInstruction(data: Partial<CreateInstructionRequest | UpdateInstructionRequest>): {
    isValid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate instruction text
    if ('instruction_text' in data) {
      const text = data.instruction_text;
      if (!text || !text.trim()) {
        errors.push('Instruction text is required');
      } else if (text.length > 500) {
        errors.push('Instruction text cannot exceed 500 characters');
      } else if (text.length < 10) {
        warnings.push('Instruction text is quite short - consider adding more detail');
      }

      // Check for problematic patterns
      const lowerText = text.toLowerCase();
      const problematicPatterns = [
        ['always', 'Consider using "typically" or "generally" instead of "always"'],
        ['never', 'Consider using "avoid" or "rarely" instead of "never"'],
        ['must', 'Consider using "should" or "preferably" instead of "must"']
      ];

      for (const [pattern, suggestion] of problematicPatterns) {
        if (lowerText.includes(pattern)) {
          warnings.push(suggestion);
        }
      }
    }

    // Validate priority
    if ('priority' in data) {
      const priority = data.priority;
      if (priority !== undefined && (priority < 1 || priority > 10)) {
        errors.push('Priority must be between 1 and 10');
      } else if (priority < 3) {
        warnings.push('Low priority instructions may not be applied frequently');
      } else if (priority > 8) {
        warnings.push('High priority instructions will override many others');
      }
    }

    // Validate category
    if ('category' in data) {
      const validCategories = ['behavior', 'communication', 'decision', 'security', 'workflow'];
      if (!validCategories.includes(data.category!)) {
        errors.push(`Category must be one of: ${validCategories.join(', ')}`);
      }
    }

    // Validate context hints
    if ('context_hints' in data && data.context_hints) {
      const hints = data.context_hints;

      if (hints.topics && Array.isArray(hints.topics)) {
        if (hints.topics.length > 10) {
          warnings.push('Too many topics may make the instruction too restrictive');
        }
        if (hints.topics.some((topic: string) => !topic.trim())) {
          errors.push('Topics cannot be empty strings');
        }
      }

      if (hints.minConfidence !== undefined) {
        if (hints.minConfidence < 0 || hints.minConfidence > 1) {
          errors.push('Minimum confidence must be between 0 and 1');
        } else if (hints.minConfidence > 0.9) {
          warnings.push('High confidence threshold may prevent instruction from being applied');
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  formatInstructionForDisplay(instruction: StandingInstruction): {
    text: string;
    category: string;
    priority: string;
    usage: string;
    lastUsed: string;
    status: string;
  } {
    return {
      text: instruction.instruction_text,
      category: instruction.category,
      priority: `Priority ${instruction.priority}`,
      usage: `Used ${instruction.usage_count} time${instruction.usage_count !== 1 ? 's' : ''}`,
      lastUsed: instruction.last_used_at
        ? new Date(instruction.last_used_at).toLocaleDateString()
        : 'Never used',
      status: instruction.enabled ? 'Active' : 'Inactive'
    };
  }

  searchInstructions(instructions: StandingInstruction[], query: string): StandingInstruction[] {
    if (!query.trim()) return instructions;

    const lowercaseQuery = query.toLowerCase();
    return instructions.filter(instruction =>
      instruction.instruction_text.toLowerCase().includes(lowercaseQuery) ||
      instruction.category.toLowerCase().includes(lowercaseQuery)
    );
  }

  sortInstructions(
    instructions: StandingInstruction[],
    sortBy: 'priority' | 'usage_count' | 'last_used_at' | 'created_at' | 'updated_at',
    order: 'ASC' | 'DESC' = 'DESC'
  ): StandingInstruction[] {
    return [...instructions].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortBy) {
        case 'priority':
          aValue = a.priority;
          bValue = b.priority;
          break;
        case 'usage_count':
          aValue = a.usage_count;
          bValue = b.usage_count;
          break;
        case 'last_used_at':
          aValue = a.last_used_at ? new Date(a.last_used_at).getTime() : 0;
          bValue = b.last_used_at ? new Date(b.last_used_at).getTime() : 0;
          break;
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'updated_at':
          aValue = new Date(a.updated_at).getTime();
          bValue = new Date(b.updated_at).getTime();
          break;
        default:
          return 0;
      }

      if (order === 'ASC') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });
  }

  // Performance monitoring
  async measurePerformance<T>(operation: () => Promise<T>, operationName: string): Promise<{
    result: T;
    duration: number;
  }> {
    const startTime = performance.now();
    try {
      const result = await operation();
      const duration = performance.now() - startTime;

      // Log performance metrics (in production, this would go to a monitoring service)
      if (duration > 1000) {
        console.warn(`Slow operation detected: ${operationName} took ${duration.toFixed(2)}ms`);
      }

      return { result, duration };
    } catch (error) {
      const duration = performance.now() - startTime;
      console.error(`Operation failed: ${operationName} after ${duration.toFixed(2)}ms`, error);
      throw error;
    }
  }
}

// Export singleton instance
export const instructionService = new InstructionService();

// Export types for use in components
export type {
  StandingInstruction,
  CreateInstructionRequest,
  UpdateInstructionRequest,
  InstructionFilters,
  BulkOperationRequest,
  InstructionAnalytics,
  ConversationContext,
  InstructionEvaluationResult
};