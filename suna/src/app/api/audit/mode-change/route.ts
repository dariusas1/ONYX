import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from '@/lib/auth';
import { logAgentModeAudit } from '@/lib/agent-mode-audit';

export async function POST(request: NextRequest) {
  try {
    // Get user session
    const session = await getServerSession();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await request.json();
    const {
      action,
      details,
      sessionId,
    } = body;

    // Validate required fields
    if (!action) {
      return NextResponse.json(
        { error: 'Action is required' },
        { status: 400 }
      );
    }

    // Validate action type
    const validActions = [
      'mode_change',
      'warning_shown',
      'warning_accepted',
      'warning_rejected',
      'agent_enabled',
      'agent_disabled',
      'consent_revoked'
    ];

    if (!validActions.includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action type' },
        { status: 400 }
      );
    }

    // Extract client information
    const clientInfo = {
      ipAddress: request.ip ||
                 request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
                 request.headers.get('x-real-ip') ||
                 'unknown',
      userAgent: request.headers.get('user-agent') || 'unknown',
    };

    // Log the audit entry
    const auditLog = await logAgentModeAudit(session.user.id, {
      action,
      details: {
        ...details,
        ...clientInfo,
        sessionId: sessionId || 'unknown',
        timestamp: new Date().toISOString(),
      },
      userId: session.user.id,
    });

    return NextResponse.json({
      success: true,
      data: {
        id: auditLog.id,
        timestamp: auditLog.createdAt,
      },
    });
  } catch (error) {
    console.error('Error logging agent mode audit:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// GET endpoint for retrieving audit logs (admin/staff only)
export async function GET(request: NextRequest) {
  try {
    // Get user session
    const session = await getServerSession();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Check if user has permission to view audit logs
    // This would typically be admin/staff role check
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');
    const userId = searchParams.get('userId');

    // For now, only allow users to view their own audit logs
    const targetUserId = userId || session.user.id;

    if (userId && userId !== session.user.id && !session.user.isAdmin) {
      return NextResponse.json(
        { error: 'Insufficient permissions' },
        { status: 403 }
      );
    }

    // Get audit logs from database
    const auditLogs = await getAgentModeAuditLogs(targetUserId, {
      limit: Math.min(limit, 100), // Max 100 per request
      offset: Math.max(offset, 0),
    });

    return NextResponse.json({
      success: true,
      data: auditLogs,
      pagination: {
        limit,
        offset,
        hasMore: auditLogs.length === limit,
      },
    });
  } catch (error) {
    console.error('Error fetching audit logs:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Helper function to get audit logs (would be in a separate lib file)
async function getAgentModeAuditLogs(
  userId: string,
  options: { limit: number; offset: number }
) {
  // This would typically query your database
  // For now, return mock data structure
  return [];
}