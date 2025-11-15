// =============================================================================
// ONYX User Settings - Standing Instructions API
// =============================================================================
// CRUD API for user standing instructions with authentication and validation
// =============================================================================

import { NextRequest, NextResponse } from 'next/server';
import {
  createStandingInstruction,
  getUserStandingInstructions,
  updateStandingInstruction,
  deleteStandingInstruction,
  getStandingInstructionById,
  bulkCreateStandingInstructions
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
// GET - List standing instructions
// =============================================================================
export async function GET(request: NextRequest) {
  try {
    // Authenticate request
    const auth = await authenticateRequest(request);
    if (!auth) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Parse query parameters
    const { searchParams } = new URL(request.url);
    const enabled_only = searchParams.get('enabled_only') === 'true';
    const category = searchParams.get('category') || undefined;
    const min_priority = searchParams.get('min_priority') ?
      parseInt(searchParams.get('min_priority')!, 10) : undefined;
    const max_priority = searchParams.get('max_priority') ?
      parseInt(searchParams.get('max_priority')!, 10) : undefined;
    const limit = searchParams.get('limit') ?
      parseInt(searchParams.get('limit')!, 10) : 50;

    // Get standing instructions
    const result = await getUserStandingInstructions(auth.userId, {
      enabled_only,
      category,
      min_priority,
      max_priority,
      limit
    });

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || 'Failed to fetch standing instructions' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: result.data,
      metadata: result.metadata
    });

  } catch (error) {
    console.error('Standing instructions GET error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// POST - Create standing instruction
// =============================================================================
export async function POST(request: NextRequest) {
  try {
    // Authenticate request
    const auth = await authenticateRequest(request);
    if (!auth) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const body = await parseRequestBody(request);
    if (!body) {
      return NextResponse.json(
        { error: 'Invalid request body' },
        { status: 400 }
      );
    }

    // Handle bulk creation
    if (body.instructions && Array.isArray(body.instructions)) {
      const result = await bulkCreateStandingInstructions(auth.userId, body.instructions);

      if (!result.success) {
        return NextResponse.json(
          { error: result.error || 'Failed to create standing instructions' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data: result.data,
        metadata: result.metadata,
        message: `Created ${result.data?.length || 0} standing instructions`
      });
    }

    // Handle single instruction creation
    const { content, priority, enabled, category, conditions } = body;

    if (!content || typeof content !== 'string') {
      return NextResponse.json(
        { error: 'Content is required and must be a string' },
        { status: 400 }
      );
    }

    const result = await createStandingInstruction({
      user_id: auth.userId,
      content: content.trim(),
      priority,
      enabled,
      category,
      conditions
    });

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || 'Failed to create standing instruction' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: result.data,
      message: 'Standing instruction created successfully'
    }, { status: 201 });

  } catch (error) {
    console.error('Standing instructions POST error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}