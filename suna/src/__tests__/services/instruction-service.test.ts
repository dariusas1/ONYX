/**
 * Instruction Service Tests
 *
 * Unit tests for the frontend instruction service covering all CRUD operations,
 * validation, and utility functions.
 */

import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { instructionService } from '@/services/instruction-service';
import {
  StandingInstruction,
  CreateInstructionRequest,
  UpdateInstructionRequest,
  InstructionCategory
} from '@/lib/types/instructions';

// Mock fetch
global.fetch = vi.fn();

describe('InstructionService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getInstructions', () => {
    it('should fetch instructions successfully', async () => {
      const mockInstructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Test instruction',
          priority: 5,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {},
          usage_count: 10,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { instructions: mockInstructions }
        })
      });

      const result = await instructionService.getInstructions();

      expect(fetch).toHaveBeenCalledWith('/api/instructions?');
      expect(result).toEqual(mockInstructions);
    });

    it('should apply filters correctly', async () => {
      const filters = {
        category: InstructionCategory.COMMUNICATION,
        enabled: true,
        priority_min: 3,
        search: 'test'
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { instructions: [] }
        })
      });

      await instructionService.getInstructions(filters);

      expect(fetch).toHaveBeenCalledWith(
        '/api/instructions?category=communication&enabled=true&priority_min=3&search=test'
      );
    });

    it('should handle API errors', async () => {
      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Database error'
        })
      });

      await expect(instructionService.getInstructions()).rejects.toThrow('Database error');
    });
  });

  describe('createInstruction', () => {
    it('should create instruction successfully', async () => {
      const mockInstruction: StandingInstruction = {
        id: '1',
        user_id: 'user1',
        instruction_text: 'New instruction',
        priority: 7,
        category: InstructionCategory.DECISION,
        enabled: true,
        context_hints: {},
        usage_count: 0,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      };

      const createData: CreateInstructionRequest = {
        instruction_text: 'New instruction',
        priority: 7,
        category: InstructionCategory.DECISION
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockInstruction
        })
      });

      const result = await instructionService.createInstruction(createData);

      expect(fetch).toHaveBeenCalledWith('/api/instructions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData)
      });
      expect(result).toEqual(mockInstruction);
    });

    it('should handle creation errors', async () => {
      const createData: CreateInstructionRequest = {
        instruction_text: 'Invalid instruction text that is way too long and exceeds the maximum character limit of 500 characters',
        category: InstructionCategory.BEHAVIOR
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Instruction text cannot exceed 500 characters'
        })
      });

      await expect(instructionService.createInstruction(createData)).rejects.toThrow(
        'Instruction text cannot exceed 500 characters'
      );
    });
  });

  describe('updateInstruction', () => {
    it('should update instruction successfully', async () => {
      const mockInstruction: StandingInstruction = {
        id: '1',
        user_id: 'user1',
        instruction_text: 'Updated instruction',
        priority: 8,
        category: InstructionCategory.SECURITY,
        enabled: true,
        context_hints: {},
        usage_count: 5,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z'
      };

      const updateData: UpdateInstructionRequest = {
        instruction_text: 'Updated instruction',
        priority: 8
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockInstruction
        })
      });

      const result = await instructionService.updateInstruction('1', updateData);

      expect(fetch).toHaveBeenCalledWith('/api/instructions/1', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });
      expect(result).toEqual(mockInstruction);
    });
  });

  describe('deleteInstruction', () => {
    it('should delete instruction successfully', async () => {
      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Instruction disabled'
        })
      });

      await instructionService.deleteInstruction('1');

      expect(fetch).toHaveBeenCalledWith('/api/instructions/1?soft=true', {
        method: 'DELETE'
      });
    });

    it('should support hard delete', async () => {
      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Instruction deleted'
        })
      });

      await instructionService.deleteInstruction('1', false);

      expect(fetch).toHaveBeenCalledWith('/api/instructions/1?soft=false', {
        method: 'DELETE'
      });
    });
  });

  describe('bulkOperation', () => {
    it('should perform bulk enable operation', async () => {
      const bulkData = {
        operation: 'enable' as const,
        instruction_ids: ['1', '2', '3']
      };

      const mockResponse = {
        success_count: 3,
        failed_count: 0,
        errors: []
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockResponse
        })
      });

      const result = await instructionService.bulkOperation(bulkData);

      expect(fetch).toHaveBeenCalledWith('/api/instructions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bulkData)
      });
      expect(result).toEqual(mockResponse);
    });

    it('should handle partial failures in bulk operations', async () => {
      const bulkData = {
        operation: 'delete' as const,
        instruction_ids: ['1', '2', '3']
      };

      const mockResponse = {
        success_count: 2,
        failed_count: 1,
        errors: [
          { instruction_id: '3', error: 'Instruction not found' }
        ]
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockResponse
        })
      });

      const result = await instructionService.bulkOperation(bulkData);

      expect(result.success_count).toBe(2);
      expect(result.failed_count).toBe(1);
      expect(result.errors).toHaveLength(1);
    });
  });

  describe('evaluateInstructions', () => {
    it('should evaluate instructions with context', async () => {
      const context = {
        messageContent: 'Help me make a decision',
        agentMode: 'chat',
        confidence: 0.8,
        involvesSensitiveData: false,
        requiresSecureHandling: false,
        isAgentMode: false,
        isTaskExecution: false
      };

      const mockResult = {
        active_instructions: [],
        evaluation_time_ms: 25,
        total_evaluated: 5,
        conflicts_detected: [],
        applied_count: 2
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockResult
        })
      });

      const result = await instructionService.evaluateInstructions(context);

      expect(fetch).toHaveBeenCalledWith('/api/instructions/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_context: context })
      });
      expect(result).toEqual(mockResult);
    });
  });

  describe('getAnalytics', () => {
    it('should get analytics for all instructions', async () => {
      const mockAnalytics = {
        total_instructions: 10,
        active_instructions: 8,
        categories: [],
        usage_overview: {
          total_usage: 45,
          avg_usage_per_instruction: 4.5,
          most_used_instruction: { id: '1', instruction_text: 'Test', usage_count: 15 },
          least_used_instruction: { id: '2', instruction_text: 'Test 2', usage_count: 0 }
        },
        priority_analysis: {
          avg_priority: 5.5,
          high_priority_count: 3,
          low_priority_count: 2
        },
        effectiveness_metrics: {
          active_instructions_ratio: 0.8,
          recently_used_ratio: 0.6,
          overall_effectiveness_score: 75
        }
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockAnalytics
        })
      });

      const result = await instructionService.getAnalytics();

      expect(fetch).toHaveBeenCalledWith('/api/instructions/analytics');
      expect(result).toEqual(mockAnalytics);
    });

    it('should get analytics for specific instruction', async () => {
      const mockInstructionAnalytics = {
        instruction_id: '1',
        category: InstructionCategory.BEHAVIOR,
        priority: 7,
        enabled: true,
        total_usage: 15,
        avg_daily_usage: 0.5,
        effectiveness_score: 80,
        recommendations: ['Test recommendation']
      };

      (fetch as Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockInstructionAnalytics
        })
      });

      const result = await instructionService.getAnalytics('1');

      expect(fetch).toHaveBeenCalledWith('/api/instructions/analytics?instruction_id=1');
      expect(result).toEqual(mockInstructionAnalytics);
    });
  });

  describe('validateInstruction', () => {
    it('should validate valid instruction data', () => {
      const data = {
        instruction_text: 'Valid instruction text',
        priority: 5,
        category: InstructionCategory.BEHAVIOR
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect empty instruction text', () => {
      const data = {
        instruction_text: '',
        priority: 5,
        category: InstructionCategory.BEHAVIOR
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Instruction text is required');
    });

    it('should detect instruction text too long', () => {
      const data = {
        instruction_text: 'a'.repeat(501),
        priority: 5,
        category: InstructionCategory.BEHAVIOR
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Instruction text cannot exceed 500 characters');
    });

    it('should detect invalid priority', () => {
      const data = {
        instruction_text: 'Valid instruction',
        priority: 15,
        category: InstructionCategory.BEHAVIOR
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Priority must be between 1 and 10');
    });

    it('should detect invalid category', () => {
      const data = {
        instruction_text: 'Valid instruction',
        priority: 5,
        category: 'invalid_category' as any
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Category must be one of: behavior, communication, decision, security, workflow');
    });

    it('should generate warnings for problematic patterns', () => {
      const data = {
        instruction_text: 'You must always follow this rule',
        priority: 5,
        category: InstructionCategory.BEHAVIOR
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
      expect(result.warnings.some(w => w.includes('must'))).toBe(true);
    });

    it('should validate context hints', () => {
      const data = {
        instruction_text: 'Valid instruction',
        priority: 5,
        category: InstructionCategory.BEHAVIOR,
        context_hints: {
          topics: ['topic1', '', 'topic3'],
          minConfidence: 1.5
        }
      };

      const result = instructionService.validateInstruction(data);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Minimum confidence must be between 0 and 1');
      expect(result.errors).toContain('Topics cannot be empty strings');
    });
  });

  describe('formatInstructionForDisplay', () => {
    it('should format instruction for display', () => {
      const instruction: StandingInstruction = {
        id: '1',
        user_id: 'user1',
        instruction_text: 'Test instruction',
        priority: 5,
        category: InstructionCategory.BEHAVIOR,
        enabled: true,
        context_hints: {},
        usage_count: 1,
        last_used_at: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      };

      const result = instructionService.formatInstructionForDisplay(instruction);

      expect(result.text).toBe('Test instruction');
      expect(result.category).toBe('behavior');
      expect(result.priority).toBe('Priority 5');
      expect(result.usage).toBe('Used 1 time');
      expect(result.lastUsed).toBe('1/1/2024');
      expect(result.status).toBe('Active');
    });

    it('should handle never used instruction', () => {
      const instruction: StandingInstruction = {
        id: '1',
        user_id: 'user1',
        instruction_text: 'Test instruction',
        priority: 5,
        category: InstructionCategory.BEHAVIOR,
        enabled: false,
        context_hints: {},
        usage_count: 0,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      };

      const result = instructionService.formatInstructionForDisplay(instruction);

      expect(result.usage).toBe('Used 0 times');
      expect(result.lastUsed).toBe('Never used');
      expect(result.status).toBe('Inactive');
    });
  });

  describe('searchInstructions', () => {
    it('should search instructions by text', () => {
      const instructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Communication style instruction',
          priority: 5,
          category: InstructionCategory.COMMUNICATION,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          user_id: 'user1',
          instruction_text: 'Security protocol',
          priority: 10,
          category: InstructionCategory.SECURITY,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      const result = instructionService.searchInstructions(instructions, 'communication');

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('1');
    });

    it('should search instructions by category', () => {
      const instructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Test instruction',
          priority: 5,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          user_id: 'user1',
          instruction_text: 'Another test',
          priority: 8,
          category: InstructionCategory.SECURITY,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      const result = instructionService.searchInstructions(instructions, 'security');

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('2');
    });

    it('should return all instructions for empty query', () => {
      const instructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Test instruction',
          priority: 5,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      const result = instructionService.searchInstructions(instructions, '');

      expect(result).toEqual(instructions);
    });
  });

  describe('sortInstructions', () => {
    it('should sort by priority descending', () => {
      const instructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Low priority',
          priority: 2,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          user_id: 'user1',
          instruction_text: 'High priority',
          priority: 9,
          category: InstructionCategory.SECURITY,
          enabled: true,
          context_hints: {},
          usage_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      const result = instructionService.sortInstructions(instructions, 'priority', 'DESC');

      expect(result[0].priority).toBe(9);
      expect(result[1].priority).toBe(2);
    });

    it('should sort by usage count ascending', () => {
      const instructions: StandingInstruction[] = [
        {
          id: '1',
          user_id: 'user1',
          instruction_text: 'Heavily used',
          priority: 5,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {},
          usage_count: 100,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          user_id: 'user1',
          instruction_text: 'Lightly used',
          priority: 5,
          category: InstructionCategory.COMMUNICATION,
          enabled: true,
          context_hints: {},
          usage_count: 5,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ];

      const result = instructionService.sortInstructions(instructions, 'usage_count', 'ASC');

      expect(result[0].usage_count).toBe(5);
      expect(result[1].usage_count).toBe(100);
    });
  });

  describe('measurePerformance', () => {
    it('should measure operation performance', async () => {
      const mockOperation = vi.fn().mockResolvedValue('test result');

      const { result, duration } = await instructionService.measurePerformance(
        mockOperation,
        'test operation'
      );

      expect(mockOperation).toHaveBeenCalled();
      expect(result).toBe('test result');
      expect(typeof duration).toBe('number');
      expect(duration).toBeGreaterThanOrEqual(0);
    });

    it('should log warnings for slow operations', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const mockOperation = vi.fn().mockImplementation(() => {
        return new Promise(resolve => setTimeout(() => resolve('test result'), 1100));
      });

      await instructionService.measurePerformance(mockOperation, 'slow operation');

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Slow operation detected'),
        expect.stringContaining('slow operation'),
        expect.stringContaining('1100.00ms')
      );
    });
  });
});