import { NextRequest, NextResponse } from 'next/server';

// Control management state (in production, use Redis or database)
const controlState = new Map<string, {
  owner: 'agent' | 'founder' | null;
  requestedBy: string | null;
  requestTime: number;
  reason?: string;
}>();

// Take control endpoint
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { reason } = body;

    // Validate authorization
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const userToken = authHeader.substring(7);

    // Get session ID from request or generate one
    const sessionId = body.sessionId || `session-${Date.now()}`;

    // Get current control state
    const currentControl = controlState.get(sessionId) || {
      owner: 'agent',
      requestedBy: null,
      requestTime: Date.now()
    };

    // Validate user permissions
    const hasControlPermission = await validateControlPermission(userToken, 'founder');
    if (!hasControlPermission) {
      return NextResponse.json(
        { error: 'Insufficient permissions to take control' },
        { status: 403 }
      );
    }

    // Check if control can be taken
    if (currentControl.owner === 'founder') {
      return NextResponse.json({
        success: false,
        message: 'You already have control',
        currentOwner: 'founder'
      });
    }

    // Update control state
    const newControlState = {
      owner: 'founder' as const,
      requestedBy: userToken,
      requestTime: Date.now(),
      reason
    };

    controlState.set(sessionId, newControlState);

    // Log control change for audit
    console.log(`Control taken by founder: ${new Date().toISOString()}`, {
      sessionId,
      previousOwner: currentControl.owner,
      newOwner: 'founder',
      reason
    });

    return NextResponse.json({
      success: true,
      controlOwner: 'founder',
      hasControl: true,
      timestamp: new Date().toISOString(),
      reason
    });

  } catch (error) {
    console.error('Take control error:', error);
    return NextResponse.json(
      { error: 'Failed to take control' },
      { status: 500 }
    );
  }
}

// Get control status
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get('sessionId');

    if (!sessionId) {
      return NextResponse.json(
        { error: 'Missing sessionId parameter' },
        { status: 400 }
      );
    }

    const control = controlState.get(sessionId);

    return NextResponse.json({
      sessionId,
      controlOwner: control?.owner || 'agent',
      hasControl: control?.owner === 'founder',
      lastUpdated: control ? new Date(control.requestTime).toISOString() : null,
      reason: control?.reason
    });

  } catch (error) {
    console.error('Get control status error:', error);
    return NextResponse.json(
      { error: 'Failed to get control status' },
      { status: 500 }
    );
  }
}

async function validateControlPermission(token: string, requestedRole: 'agent' | 'founder'): Promise<boolean> {
  // In a real implementation, you would:
  // 1. Decode and validate the JWT token
  // 2. Check user roles and permissions
  // 3. Verify user is authorized to request the specified role
  // For now, we'll do basic validation
  return token.length > 10 && requestedRole === 'founder';
}