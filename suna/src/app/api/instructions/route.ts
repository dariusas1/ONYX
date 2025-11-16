/**
 * Standing Instructions API Routes
 *
 * REST API endpoints for managing standing instructions with full CRUD operations,
 * bulk operations, conflict detection, and analytics.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import {
  CreateInstructionRequest,
  InstructionFilters,
  BulkOperationRequest,
  ApiResponse
} from '@/lib/types/instructions';

// GET /api/instructions - List instructions with filtering
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

    // Parse query parameters
    const filters: InstructionFilters = {};

    if (searchParams.get('category')) {
      filters.category = searchParams.get('category') as any;
    }

    if (searchParams.get('enabled') !== null) {
      filters.enabled = searchParams.get('enabled') === 'true';
    }

    if (searchParams.get('priority_min')) {
      filters.priority_min = parseInt(searchParams.get('priority_min')!);
    }

    if (searchParams.get('priority_max')) {
      filters.priority_max = parseInt(searchParams.get('priority_max')!);
    }

    if (searchParams.get('search')) {
      filters.search = searchParams.get('search')!;
    }

    if (searchParams.get('sort_by')) {
      filters.sort_by = searchParams.get('sort_by') as any;
    }

    if (searchParams.get('sort_order')) {
      filters.sort_order = searchParams.get('sort_order') as any;
    }

    if (searchParams.get('limit')) {
      filters.limit = parseInt(searchParams.get('limit')!);
    }

    if (searchParams.get('offset')) {
      filters.offset = parseInt(searchParams.get('offset')!);
    }

    // Build database query
    let query = supabase
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
      .eq('user_id', user.id);

    // Apply filters
    if (filters.enabled !== undefined) {
      query = query.eq('enabled', filters.enabled);
    }

    if (filters.category) {
      query = query.eq('category', filters.category);
    }

    if (filters.priority_min !== undefined) {
      query = query.gte('priority', filters.priority_min);
    }

    if (filters.priority_max !== undefined) {
      query = query.lte('priority', filters.priority_max);
    }

    if (filters.search) {
      query = query.ilike('instruction_text', `%${filters.search}%`);
    }

    // Apply ordering
    const sortField = filters.sort_by || 'priority';
    const sortOrder = filters.sort_order || 'DESC';
    query = query.order(sortField, { ascending: sortOrder === 'ASC' });

    // Get total count for pagination
    const { count, error: countError } = await supabase
      .from('standing_instructions')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id);

    if (countError) {
      console.error('Count error:', countError);
      return NextResponse.json(
        { success: false, error: 'Failed to count instructions' },
        { status: 500 }
      );
    }

    // Apply pagination
    if (filters.limit) {
      query = query.limit(filters.limit);
    }

    if (filters.offset) {
      query = query.range(filters.offset, filters.offset + (filters.limit || 10) - 1);
    }

    const { data: instructions, error } = await query;

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch instructions' },
        { status: 500 }
      );
    }

    const response = {
      success: true,
      data: {
        instructions: instructions || [],
        pagination: {
          limit: filters.limit || 10,
          offset: filters.offset || 0,
          count: instructions?.length || 0,
          total: count || 0
        }
      }
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('GET /api/instructions error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// POST /api/instructions - Create new instruction
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

    const body: CreateInstructionRequest = await request.json();

    // Validate request data
    if (!body.instruction_text || !body.instruction_text.trim()) {
      return NextResponse.json(
        { success: false, error: 'Instruction text is required' },
        { status: 400 }
      );
    }

    if (body.instruction_text.length > 500) {
      return NextResponse.json(
        { success: false, error: 'Instruction text cannot exceed 500 characters' },
        { status: 400 }
      );
    }

    if (body.priority !== undefined && (body.priority < 1 || body.priority > 10)) {
      return NextResponse.json(
        { success: false, error: 'Priority must be between 1 and 10' },
        { status: 400 }
      );
    }

    const validCategories = ['behavior', 'communication', 'decision', 'security', 'workflow'];
    if (!validCategories.includes(body.category)) {
      return NextResponse.json(
        { success: false, error: `Category must be one of: ${validCategories.join(', ')}` },
        { status: 400 }
      );
    }

    // Check instruction limit
    const { count, error: countError } = await supabase
      .from('standing_instructions')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('enabled', true);

    if (countError) {
      console.error('Count error:', countError);
      return NextResponse.json(
        { success: false, error: 'Failed to check instruction limit' },
        { status: 500 }
      );
    }

    if ((count || 0) >= 100) {
      return NextResponse.json(
        { success: false, error: 'Maximum number of active instructions (100) reached' },
        { status: 400 }
      );
    }

    // Create instruction
    const { data: instruction, error } = await supabase
      .from('standing_instructions')
      .insert({
        user_id: user.id,
        instruction_text: body.instruction_text.trim(),
        priority: body.priority || 5,
        category: body.category,
        enabled: body.enabled !== undefined ? body.enabled : true,
        context_hints: body.context_hints || {}
      })
      .select()
      .single();

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to create instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: instruction
    });

  } catch (error) {
    console.error('POST /api/instructions error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// PUT /api/instructions - Bulk operations
export async function PUT(request: NextRequest) {
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

    const body: BulkOperationRequest = await request.json();

    if (!body.instruction_ids || !Array.isArray(body.instruction_ids) || body.instruction_ids.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Instruction IDs array is required' },
        { status: 400 }
      );
    }

    if (!body.operation || !['enable', 'disable', 'delete', 'update_priority'].includes(body.operation)) {
      return NextResponse.json(
        { success: false, error: 'Operation must be one of: enable, disable, delete, update_priority' },
        { status: 400 }
      );
    }

    const results = {
      success_count: 0,
      failed_count: 0,
      errors: [] as Array<{ instruction_id: string; error: string }>
    };

    // Process each instruction
    for (const instructionId of body.instruction_ids) {
      try {
        let query;

        switch (body.operation) {
          case 'enable':
            query = supabase
              .from('standing_instructions')
              .update({ enabled: true })
              .eq('id', instructionId)
              .eq('user_id', user.id);
            break;

          case 'disable':
            query = supabase
              .from('standing_instructions')
              .update({ enabled: false })
              .eq('id', instructionId)
              .eq('user_id', user.id);
            break;

          case 'delete':
            query = supabase
              .from('standing_instructions')
              .delete()
              .eq('id', instructionId)
              .eq('user_id', user.id);
            break;

          case 'update_priority':
            if (body.value === undefined || body.value < 1 || body.value > 10) {
              throw new Error('Priority must be between 1 and 10');
            }
            query = supabase
              .from('standing_instructions')
              .update({ priority: body.value })
              .eq('id', instructionId)
              .eq('user_id', user.id);
            break;
        }

        const { error } = await query;

        if (error) {
          results.failed_count++;
          results.errors.push({
            instruction_id: instructionId,
            error: error.message
          });
        } else {
          results.success_count++;
        }

      } catch (error) {
        results.failed_count++;
        results.errors.push({
          instruction_id: instructionId,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    return NextResponse.json({
      success: true,
      data: results
    });

  } catch (error) {
    console.error('PUT /api/instructions error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}