// =============================================================================
// ONYX User Settings - Individual Standing Instruction API
// =============================================================================
// CRUD operations for individual standing instructions with authentication
// =============================================================================

import { NextRequest, NextResponse } from 'next/server';
import {
  getStandingInstructionById,
  updateStandingInstruction,
  deleteStandingInstruction
} from '@/lib/standing-instructions';

// Authentication middleware (simplified for now)
async function authenticateRequest(request: NextRequest): Promise<{ userId: string } | null> {
  // In a real implementation, this would verify JWT tokens or session cookies
  // For now, we'll accept a user_id header for development
  const userId = request.headers.get('x-user-id');

  if (!userId) {
    return null;
  }

  return { userId };
}

// Parse request body safely
function parseRequestBody(request: NextRequest): Promise<any> {
  return request.json().catch(() => null);
}

// =============================================================================
// GET - Get specific standing instruction
// =============================================================================
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Authenticate request
    const auth = await authenticateRequest(request);
    if (!auth) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { id } = params;
    if (!id) {
      return NextResponse.json(
        { error: 'Instruction ID is required' },
        { status: 400 }
      );
    }

    // Get standing instruction
    const result = await getStandingInstructionById(id, auth.userId);

    if (!result.success) {
      if (result.error?.includes('not found')) {
        return NextResponse.json(
          { error: 'Standing instruction not found' },
          { status: 404 }
        );
      }

      return NextResponse.json(
        { error: result.error || 'Failed to fetch standing instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: result.data
    });

  } catch (error) {
    console.error('Standing instruction GET error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// PUT - Update standing instruction
// =============================================================================
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Authenticate request
    const auth = await authenticateRequest(request);
    if (!auth) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { id } = params;
    if (!id) {
      return NextResponse.json(
        { error: 'Instruction ID is required' },
        { status: 400 }
      );
    }

    const body = await parseRequestBody(request);
    if (!body) {
      return NextResponse.json(
        { error: 'Invalid request body' },
        { status: 400 }
      );
    }

    const { content, priority, enabled, category, conditions } = body;

    // Validate that at least one field is being updated
    if (content !== undefined || priority !== undefined || enabled !== undefined ||
        category !== undefined || conditions !== undefined) {

      const result = await updateStandingInstruction(id, auth.userId, {
        content: content !== undefined ? (typeof content === 'string' ? content.trim() : content) : undefined,
        priority,
        enabled,
        category,
        conditions
      });

      if (!result.success) {
        if (result.error?.includes('not found')) {
          return NextResponse.json(
            { error: 'Standing instruction not found' },
            { status: 404 }
          );
        }

        return NextResponse.json(
          { error: result.error || 'Failed to update standing instruction' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data: result.data,
        message: 'Standing instruction updated successfully'
      });
    } else {
      return NextResponse.json(
        { error: 'No valid fields to update' },
        { status: 400 }
      );
    }

  } catch (error) {
    console.error('Standing instruction PUT error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// DELETE - Delete standing instruction
// =============================================================================
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Authenticate request
    const auth = await authenticateRequest(request);
    if (!auth) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { id } = params;
    if (!id) {
      return NextResponse.json(
        { error: 'Instruction ID is required' },
        { status: 400 }
      );
    }

    const result = await deleteStandingInstruction(id, auth.userId);

    if (!result.success) {
      if (result.error?.includes('not found')) {
        return NextResponse.json(
          { error: 'Standing instruction not found' },
          { status: 404 }
        );
      }

      return NextResponse.json(
        { error: result.error || 'Failed to delete standing instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: 'Standing instruction deleted successfully'
    });

  } catch (error) {
    console.error('Standing instruction DELETE error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}