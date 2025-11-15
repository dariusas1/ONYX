import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from '@/lib/auth';
import { getUserAgentModeSettings, updateUserAgentModeSettings } from '@/lib/agent-mode-settings';

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

    // Get user's agent mode settings
    const settings = await getUserAgentModeSettings(session.user.id);

    return NextResponse.json({
      success: true,
      data: settings,
    });
  } catch (error) {
    console.error('Error fetching agent mode settings:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

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
      mode,
      isEnabled,
      hasAcceptedWarning,
      consentTimestamp,
      ipAddress,
    } = body;

    // Validate input
    if (mode && !['chat', 'agent'].includes(mode)) {
      return NextResponse.json(
        { error: 'Invalid mode. Must be "chat" or "agent"' },
        { status: 400 }
      );
    }

    // Update user's agent mode settings
    const updatedSettings = await updateUserAgentModeSettings(session.user.id, {
      mode,
      isEnabled,
      hasAcceptedWarning,
      consentTimestamp,
      ipAddress,
      userAgent: request.headers.get('user-agent'),
    });

    return NextResponse.json({
      success: true,
      data: updatedSettings,
    });
  } catch (error) {
    console.error('Error updating agent mode settings:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}