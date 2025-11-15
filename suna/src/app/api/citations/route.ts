/**
 * Citations API Route
 *
 * Handles citation CRUD operations, search, and statistics.
 * Provides endpoints for UI components to retrieve and manage citations.
 */

import { NextRequest, NextResponse } from 'next/server';
import { messageService, CitationSearchParams } from '@/lib/message-service';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// =============================================================================
// GET Handler - Retrieve Citations
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
    const messageId = searchParams.get('messageId');
    const conversationId = searchParams.get('conversationId');
    const documentId = searchParams.get('documentId');
    const confidenceThreshold = searchParams.get('confidenceThreshold');
    const sourceType = searchParams.get('sourceType');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');

    // Handle different query types
    if (messageId) {
      // Get citations for a specific message
      const citations = await messageService.getMessageCitations(messageId);
      return NextResponse.json({
        messageId,
        citations,
        count: citations.length
      });
    }

    if (conversationId) {
      // Get citations for a conversation
      const conversationCitations = await messageService.getConversationCitations(conversationId);
      return NextResponse.json({
        conversationId,
        citations: conversationCitations,
        count: conversationCitations.reduce((sum, cc) => sum + cc.citations.length, 0)
      });
    }

    // Search citations with filters
    const searchParamsObj: CitationSearchParams = {};

    if (documentId) searchParamsObj.documentId = documentId;
    if (confidenceThreshold) {
      searchParamsObj.confidenceThreshold = parseFloat(confidenceThreshold);
    }
    if (sourceType) searchParamsObj.sourceType = sourceType;
    if (startDate && endDate) {
      searchParamsObj.dateRange = {
        start: new Date(startDate),
        end: new Date(endDate)
      };
    }

    const citations = await messageService.searchCitations(searchParamsObj);

    return NextResponse.json({
      citations,
      count: citations.length,
      filters: searchParamsObj
    });
  } catch (error) {
    console.error('Citations GET Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// POST Handler - Create/Update Citations
// =============================================================================

export async function POST(request: NextRequest): Promise<Response> {
  try {
    // Authentication check
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { messageId, citations, action } = body;

    if (!messageId) {
      return NextResponse.json(
        { error: 'Message ID is required' },
        { status: 400 }
      );
    }

    switch (action) {
      case 'update':
        // Update existing citations
        const { citationId, updates } = body;
        if (!citationId || !updates) {
          return NextResponse.json(
            { error: 'Citation ID and updates are required for update action' },
            { status: 400 }
          );
        }

        const success = await messageService.updateCitation(citationId, updates);
        return NextResponse.json({
          success,
          citationId,
          updates
        });

      case 'delete':
        // Delete citations for a message
        await messageService.deleteMessageCitations(messageId);
        return NextResponse.json({
          success: true,
          messageId,
          action: 'deleted'
        });

      default:
        return NextResponse.json(
          { error: 'Invalid action. Use "update" or "delete".' },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error('Citations POST Error:', error);
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
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}