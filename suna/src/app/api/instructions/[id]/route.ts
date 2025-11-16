/**
 * Individual Instruction API Routes
 *
 * REST API endpoints for managing individual standing instructions including
 * get, update, delete operations and analytics.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { UpdateInstructionRequest } from '@/lib/types/instructions';

// GET /api/instructions/[id] - Get specific instruction
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const supabase = createClient();
    const { id } = params;

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Fetch instruction
    const { data: instruction, error } = await supabase
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
      .eq('id', id)
      .eq('user_id', user.id)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json(
          { success: false, error: 'Instruction not found' },
          { status: 404 }
        );
      }
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: instruction
    });

  } catch (error) {
    console.error('GET /api/instructions/[id] error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// PUT /api/instructions/[id] - Update instruction
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const supabase = createClient();
    const { id } = params;

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const body: UpdateInstructionRequest = await request.json();

    // Validate update data
    const updateData: any = {};
    let hasValidUpdates = false;

    if (body.instruction_text !== undefined) {
      if (!body.instruction_text || !body.instruction_text.trim()) {
        return NextResponse.json(
          { success: false, error: 'Instruction text cannot be empty' },
          { status: 400 }
        );
      }
      if (body.instruction_text.length > 500) {
        return NextResponse.json(
          { success: false, error: 'Instruction text cannot exceed 500 characters' },
          { status: 400 }
        );
      }
      updateData.instruction_text = body.instruction_text.trim();
      hasValidUpdates = true;
    }

    if (body.priority !== undefined) {
      if (body.priority < 1 || body.priority > 10) {
        return NextResponse.json(
          { success: false, error: 'Priority must be between 1 and 10' },
          { status: 400 }
        );
      }
      updateData.priority = body.priority;
      hasValidUpdates = true;
    }

    if (body.category !== undefined) {
      const validCategories = ['behavior', 'communication', 'decision', 'security', 'workflow'];
      if (!validCategories.includes(body.category)) {
        return NextResponse.json(
          { success: false, error: `Category must be one of: ${validCategories.join(', ')}` },
          { status: 400 }
        );
      }
      updateData.category = body.category;
      hasValidUpdates = true;
    }

    if (body.enabled !== undefined) {
      updateData.enabled = body.enabled;
      hasValidUpdates = true;
    }

    if (body.context_hints !== undefined) {
      updateData.context_hints = body.context_hints;
      hasValidUpdates = true;
    }

    if (!hasValidUpdates) {
      return NextResponse.json(
        { success: false, error: 'No valid fields to update' },
        { status: 400 }
      );
    }

    // Update instruction
    const { data: instruction, error } = await supabase
      .from('standing_instructions')
      .update(updateData)
      .eq('id', id)
      .eq('user_id', user.id)
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
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json(
          { success: false, error: 'Instruction not found' },
          { status: 404 }
        );
      }
      console.error('Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to update instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: instruction
    });

  } catch (error) {
    console.error('PUT /api/instructions/[id] error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// DELETE /api/instructions/[id] - Delete instruction
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const supabase = createClient();
    const { id } = params;

    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Check for soft delete preference
    const { searchParams } = new URL(request.url);
    const softDelete = searchParams.get('soft') !== 'false'; // Default to soft delete

    let result;

    if (softDelete) {
      // Soft delete (disable)
      const { data, error } = await supabase
        .from('standing_instructions')
        .update({ enabled: false })
        .eq('id', id)
        .eq('user_id', user.id)
        .select('id')
        .single();

      result = { data, error };
    } else {
      // Hard delete
      const { data, error } = await supabase
        .from('standing_instructions')
        .delete()
        .eq('id', id)
        .eq('user_id', user.id)
        .select('id')
        .single();

      result = { data, error };
    }

    if (result.error) {
      if (result.error.code === 'PGRST116') {
        return NextResponse.json(
          { success: false, error: 'Instruction not found' },
          { status: 404 }
        );
      }
      console.error('Database error:', result.error);
      return NextResponse.json(
        { success: false, error: 'Failed to delete instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: softDelete ? 'Instruction disabled' : 'Instruction deleted'
    });

  } catch (error) {
    console.error('DELETE /api/instructions/[id] error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}