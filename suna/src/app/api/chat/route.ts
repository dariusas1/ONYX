/**
 * Chat API Route with Citation Support
 *
 * Handles streaming chat completions with real-time citation extraction
 * and message storage including citation metadata.
 */

import { NextRequest, NextResponse } from 'next/server';
import { streamChatCompletion, StreamMetadata } from '@/lib/llm-client';
import { messageService, CreateMessageRequest } from '@/lib/message-service';
import { buildSystemPromptWithRAG, SystemPromptComponents } from '@/lib/prompts';
import { CitationExtractor, CitationExtractionResult, Citation } from '@/lib/citation-extractor';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// =============================================================================
// TypeScript Interfaces
// =============================================================================

export interface ChatRequest {
  message: string;
  conversationId?: string;
  systemPromptComponents?: SystemPromptComponents;
  ragContext?: Array<{
    documentId: string;
    documentName: string;
    snippet: string;
    metadata?: Record<string, any>;
  }>;
  stream?: boolean;
}

export interface ChatResponse {
  messageId: string;
  conversationId: string;
  content: string;
  citations: Citation[];
  metadata: {
    modelUsed?: string;
    totalTokens?: number;
    totalTime?: number;
    finishReason?: string;
    firstTokenLatency?: number;
    citationExtractionResult?: CitationExtractionResult;
  };
  timestamp: Date;
}

export interface StreamChunk {
  type: 'content' | 'citation' | 'metadata' | 'error' | 'complete';
  content?: string;
  citation?: Citation;
  metadata?: StreamMetadata;
  error?: string;
}

// =============================================================================
// Citation Extraction Setup
// =============================================================================

const citationExtractor = new CitationExtractor({
  confidenceThreshold: 0.7,
  maxCitationsPerMessage: 50,
  snippetLength: 300,
  enableRealTimeExtraction: true,
  validatePermissions: true
});

// =============================================================================
// Main Chat Handler
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

    // Parse request body
    const body: ChatRequest = await request.json();
    const { message, conversationId, systemPromptComponents, ragContext, stream = true } = body;

    if (!message?.trim()) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Get or create conversation
    const conversation = await messageService.getOrCreateConversation(conversationId);

    // Store user message
    await messageService.createMessage({
      conversationId: conversation.id,
      role: 'user',
      content: message,
      timestamp: new Date(),
      metadata: {}
    });

    // Build system prompt with RAG context for citations
    const systemPrompt = systemPromptComponents
      ? buildSystemPromptWithRAG(systemPromptComponents, ragContext)
      : undefined;

    // Prepare messages for LLM
    const messages = [
      ...(systemPrompt ? [{ role: 'system' as const, content: systemPrompt }] : []),
      { role: 'user' as const, content: message }
    ];

    if (stream) {
      return handleStreamingResponse(messages, conversation.id, ragContext);
    } else {
      return handleNonStreamingResponse(messages, conversation.id, ragContext);
    }
  } catch (error) {
    console.error('Chat API Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// =============================================================================
// Streaming Response Handler
// =============================================================================

async function handleStreamingResponse(
  messages: Array<{ role: string; content: string }>,
  conversationId: string,
  ragContext?: ChatRequest['ragContext']
): Promise<Response> {
  let currentContent = '';
  let extractedCitations: Citation[] = [];
  let messageId = '';
  let firstTokenTime: number | null = null;
  const startTime = Date.now();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Send initial chunk
        controller.enqueue(encoder.encode(JSON.stringify({
          type: 'metadata',
          metadata: {
            conversationId,
            timestamp: new Date().toISOString()
          }
        }) + '\n'));

        // Start streaming completion
        await streamChatCompletion(
          messages,
          async (chunk: string) => {
            // Track first token latency
            if (!firstTokenTime) {
              firstTokenTime = Date.now() - startTime;
            }

            currentContent += chunk;

            // Send content chunk
            controller.enqueue(encoder.encode(JSON.stringify({
              type: 'content',
              content: chunk
            }) + '\n'));

            // Real-time citation extraction (every 100 characters)
            if (currentContent.length % 100 < chunk.length) {
              try {
                const extractionResult = await citationExtractor.extractFromStream(
                  currentContent,
                  ragContext,
                  (citation: Citation) => {
                    // Send citation in real-time
                    controller.enqueue(encoder.encode(JSON.stringify({
                      type: 'citation',
                      citation
                    }) + '\n'));
                  }
                );

                if (extractionResult.hasCitations) {
                  extractedCitations = extractionResult.citations;
                }
              } catch (error) {
                console.warn('Citation extraction error:', error);
              }
            }
          },
          async (error: Error) => {
            controller.enqueue(encoder.encode(JSON.stringify({
              type: 'error',
              error: error.message
            }) + '\n'));
            controller.close();
          },
          async (metadata: StreamMetadata) => {
            try {
              // Final citation extraction
              const finalExtractionResult = await citationExtractor.extractFromStream(
                currentContent,
                ragContext
              );

              if (finalExtractionResult.hasCitations) {
                extractedCitations = finalExtractionResult.citations;
              }

              messageId = metadata.messageId;

              // Store message with citations
              await messageService.createMessage({
                conversationId,
                role: 'assistant',
                content: currentContent,
                timestamp: new Date(),
                citations: extractedCitations,
                metadata: {
                  messageId: metadata.messageId,
                  modelUsed: metadata.modelUsed,
                  totalTokens: metadata.totalTokens,
                  totalTime: metadata.totalTime,
                  finishReason: metadata.finishReason,
                  firstTokenLatency: firstTokenTime || undefined,
                  citationExtractionResult: finalExtractionResult,
                  ragContext
                }
              });

              // Send completion metadata
              controller.enqueue(encoder.encode(JSON.stringify({
                type: 'complete',
                metadata: {
                  ...metadata,
                  firstTokenLatency: firstTokenTime || undefined,
                  citations: extractedCitations,
                  citationExtractionResult: finalExtractionResult
                }
              }) + '\n'));

              controller.close();
            } catch (error) {
              controller.enqueue(encoder.encode(JSON.stringify({
                type: 'error',
                error: `Failed to complete message: ${error instanceof Error ? error.message : 'Unknown error'}`
              }) + '\n'));
              controller.close();
            }
          }
        );
      } catch (error) {
        controller.enqueue(encoder.encode(JSON.stringify({
          type: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        }) + '\n'));
        controller.close();
      }
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

// =============================================================================
// Non-Streaming Response Handler
// =============================================================================

async function handleNonStreamingResponse(
  messages: Array<{ role: string; content: string }>,
  conversationId: string,
  ragContext?: ChatRequest['ragContext']
): Promise<Response> {
  let currentContent = '';
  const startTime = Date.now();

  return new Promise((resolve) => {
    streamChatCompletion(
      messages,
      async (chunk: string) => {
        currentContent += chunk;
      },
      async (error: Error) => {
        resolve(NextResponse.json(
          { error: error.message },
          { status: 500 }
        ));
      },
      async (metadata: StreamMetadata) => {
        try {
          // Extract citations from completed response
          const extractionResult = await citationExtractor.extractFromStream(
            currentContent,
            ragContext
          );

          // Store message with citations
          await messageService.createMessage({
            conversationId,
            role: 'assistant',
            content: currentContent,
            timestamp: new Date(),
            citations: extractionResult.citations,
            metadata: {
              messageId: metadata.messageId,
              modelUsed: metadata.modelUsed,
              totalTokens: metadata.totalTokens,
              totalTime: metadata.totalTime,
              finishReason: metadata.finishReason,
              firstTokenLatency: Date.now() - startTime,
              citationExtractionResult: extractionResult,
              ragContext
            }
          });

          const response: ChatResponse = {
            messageId: metadata.messageId,
            conversationId,
            content: currentContent,
            citations: extractionResult.citations,
            metadata: {
              modelUsed: metadata.modelUsed,
              totalTokens: metadata.totalTokens,
              totalTime: metadata.totalTime,
              finishReason: metadata.finishReason,
              firstTokenLatency: Date.now() - startTime,
              citationExtractionResult: extractionResult
            },
            timestamp: new Date()
          };

          resolve(NextResponse.json(response));
        } catch (error) {
          resolve(NextResponse.json(
            { error: `Failed to complete message: ${error instanceof Error ? error.message : 'Unknown error'}` },
            { status: 500 }
          ));
        }
      }
    );
  });
}

// =============================================================================
// GET Handler for Chat History
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
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');

    if (!conversationId) {
      return NextResponse.json(
        { error: 'Conversation ID is required' },
        { status: 400 }
      );
    }

    // Get messages with their citations
    const messages = await messageService.getMessages(conversationId, limit, offset);
    const messagesWithCitations = await Promise.all(
      messages.map(async (message) => ({
        ...message,
        citations: await messageService.getMessageCitations(message.id)
      }))
    );

    return NextResponse.json({
      conversationId,
      messages: messagesWithCitations,
      hasMore: messages.length === limit
    });
  } catch (error) {
    console.error('Chat GET Error:', error);
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