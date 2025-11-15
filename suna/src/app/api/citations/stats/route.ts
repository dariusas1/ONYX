/**
 * Citation Statistics API Route
 *
 * Provides citation analytics and statistics for monitoring and reporting.
 */

import { NextRequest, NextResponse } from 'next/server';
import { messageService } from '@/lib/message-service';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// =============================================================================
// GET Handler - Citation Statistics
// =============================================================================

export async function GET(request: NextRequest): Promise<Response> {
  try {
    // Authentication check
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const conversationId = searchParams.get('conversationId');

    // Get citation statistics
    const stats = await messageService.getCitationStats(
      conversationId || undefined
    );

    return NextResponse.json({
      conversationId,
      statistics: stats,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Citation Stats GET Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// OPTIONS Handler for CORS
// =============================================================================

export async function OPTIONS(): Promise<Response> {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}