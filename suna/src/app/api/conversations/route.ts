/**
 * Conversations API - List and create conversations
 */

import { NextRequest, NextResponse } from 'next/server';
import { messageService } from '@/lib/message-service';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '20');
    const offset = parseInt(searchParams.get('offset') || '0');

    const conversations = await messageService.getConversations(limit, offset);

    return NextResponse.json({
      conversations,
      limit,
      offset,
      hasMore: conversations.length === limit
    });
  } catch (error) {
    console.error('Failed to get conversations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch conversations' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { conversationId, title } = body;

    const conversation = await messageService.getOrCreateConversation(conversationId);

    if (title && conversation.id === conversationId) {
      // In a real implementation, we'd update the title here
      // For now, just return the conversation
    }

    return NextResponse.json({
      conversation: {
        id: conversation.id,
        createdAt: conversation.createdAt,
        updatedAt: conversation.updatedAt,
        title: title || `Conversation ${conversation.id.slice(-8)}`
      }
    });
  } catch (error) {
    console.error('Failed to create conversation:', error);
    return NextResponse.json(
      { error: 'Failed to create conversation' },
      { status: 500 }
    );
  }
}