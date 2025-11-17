import { NextRequest, NextResponse } from 'next/server';

// Import the same control state from take-control
const controlState = new Map<string, {
  owner: 'agent' | 'founder' | null;
  requestedBy: string | null;
  requestTime: number;
  reason?: string;
}>();

// Release control endpoint
export async function POST(request: NextRequest) {
  try {
    // Validate authorization
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const userToken = authHeader.substring(7);

    // Get session ID from request
    const body = await request.json();
    const { sessionId } = body;

    if (!sessionId) {
      return NextResponse.json(
        { error: 'Missing sessionId parameter' },
        { status: 400 }
      );
    }

    // Get current control state
    const currentControl = controlState.get(sessionId);

    if (!currentControl) {
      return NextResponse.json({
        success: false,
        message: 'No active control session found'
      });
    }

    // Validate user permissions
    const hasReleasePermission = await validateReleasePermission(userToken);
    if (!hasReleasePermission) {
      return NextResponse.json(
        { error: 'Insufficient permissions to release control' },
        { status: 403 }
      );
    }

    // Check if user can release control
    if (currentControl.owner === 'agent') {
      return NextResponse.json({
        success: false,
        message: 'Agent currently has control'
      });
    }

    // Update control state - return control to agent
    const newControlState = {
      owner: 'agent' as const,
      requestedBy: null,
      requestTime: Date.now()
    };

    controlState.set(sessionId, newControlState);

    // Log control release for audit
    console.log(`Control released by founder: ${new Date().toISOString()}`, {
      sessionId,
      previousOwner: currentControl.owner,
      newOwner: 'agent'
    });

    return NextResponse.json({
      success: true,
      controlOwner: 'agent',
      hasControl: false,
      timestamp: new Date().toISOString(),
      message: 'Control released and returned to agent'
    });

  } catch (error) {
    console.error('Release control error:', error);
    return NextResponse.json(
      { error: 'Failed to release control' },
      { status: 500 }
    );
  }
}

async function validateReleasePermission(token: string): Promise<boolean> {
  // In a real implementation, you would:
  // 1. Decode and validate the JWT token
  // 2. Check user roles and permissions
  // 3. Verify user is authorized to release control
  // For now, we'll do basic validation
  return token.length > 10;
}