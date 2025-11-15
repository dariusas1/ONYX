/**
 * Conversation Messages API - Get messages for a specific conversation
 */

import { NextRequest, NextResponse } from 'next/server';
import { messageService } from '@/lib/message-service';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');

    const conversationId = params.id;
    const messages = await messageService.getMessages(conversationId, limit, offset);

    return NextResponse.json({
      conversationId,
      messages,
      limit,
      offset,
      hasMore: messages.length === limit
    });
  } catch (error) {
    console.error('Failed to get messages:', error);
    return NextResponse.json(
      { error: 'Failed to fetch messages' },
      { status: 500 }
    );
  }
}