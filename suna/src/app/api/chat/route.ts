/**
 * Chat API Route - Streaming Chat Completion
 *
 * Handles Server-Sent Events (SSE) streaming chat completions
 * with performance monitoring and message persistence.
 */

import { NextRequest, NextResponse } from 'next/server';
import { streamChatCompletion } from '@/lib/llm-client';
import { performanceMonitor } from '@/lib/performance-monitor';
import { messageService } from '@/lib/message-service';
import { buildSystemPrompt, SystemPromptComponents } from '@/lib/prompts';
import { getUserStandingInstructions } from '@/lib/standing-instructions';
import { validateTone } from '@/lib/tone-validator';

// SSE Message format
interface SSEMessage {
  event?: string;
  data: any;
}

function createSSEMessage(message: SSEMessage): string {
  const lines: string[] = [];

  if (message.event) {
    lines.push(`event: ${message.event}`);
  }

  if (typeof message.data === 'string') {
    lines.push(`data: ${message.data}`);
  } else {
    lines.push(`data: ${JSON.stringify(message.data)}`);
  }

  lines.push('', '');
  return lines.join('\n');
}

// Event types for SSE
const EventType = {
  MESSAGE: 'message',
  METRICS: 'metrics',
  ERROR: 'error',
  COMPLETE: 'complete'
} as const;

export async function POST(request: NextRequest) {
  // Start performance monitoring
  const startTime = Date.now();
  const requestId = `req_${startTime}_${Math.random().toString(36).substr(2, 9)}`;
  let conversationId: string;

  try {
    const body = await request.json();
    const {
      message,
      conversation_id,
      model = 'manus-primary',
      user_id,
      user_context
    } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    conversationId = conversation_id || `conv_${Date.now()}`;

    // Start performance monitoring
    performanceMonitor.startStream(requestId, conversationId);

    // Get conversation history for context
    const history = await messageService.getMessages(conversationId, 10);

    // Build system prompt components
    const systemPromptStartTime = Date.now();

    // Get user standing instructions
    let standingInstructions: any[] = [];
    if (user_id) {
      try {
        const instructionResult = await getUserStandingInstructions(user_id, {
          enabled_only: true,
          limit: 10
        });
        if (instructionResult.success && instructionResult.data) {
          standingInstructions = instructionResult.data;
        }
      } catch (error) {
        console.warn('Failed to load standing instructions:', error);
        // Continue without standing instructions
      }
    }

    // Build system prompt
    const systemPromptComponents: SystemPromptComponents = {
      basePersona: undefined, // Will use default
      userProfile: user_context ? {
        id: user_id || 'anonymous',
        ...user_context
      } : undefined,
      standingInstructions: standingInstructions,
      context: {
        currentConversation: {
          topic: undefined, // Could be derived from message
          length: history.length + 1,
          userGoal: undefined // Could be derived from message
        },
        sessionInfo: {
          sessionId: requestId,
          timestamp: new Date()
        }
      }
    };

    const systemPrompt = buildSystemPrompt(systemPromptComponents);
    const systemPromptTime = Date.now() - systemPromptStartTime;

    // Format messages for LLM client with system prompt prepended
    const messages = [
      { role: 'system', content: systemPrompt },
      ...history.map(msg => ({
        role: msg.role as 'user' | 'assistant',
        content: msg.content
      })),
      { role: 'user', content: message }
    ];

    // Create streaming response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        let firstTokenSent = false;
        let totalTokens = 0;
        let currentContent = '';
        let messageId: string | undefined;

        try {
          // Send initial metrics event
          controller.enqueue(
            encoder.encode(createSSEMessage({
              event: EventType.METRICS,
              data: {
                request_id: requestId,
                conversation_id: conversationId,
                first_token_latency: null,
                model_used: model
              }
            }))
          );

          // Start streaming with LLM client
          await streamChatCompletion(
            messages,
            // onChunk - called for each piece of content
            async (chunk: string) => {
              if (!firstTokenSent) {
                const firstTokenLatency = Date.now() - startTime;
                performanceMonitor.recordFirstToken(requestId, firstTokenLatency);

                // Send first token metrics
                controller.enqueue(
                  encoder.encode(createSSEMessage({
                    event: EventType.METRICS,
                    data: {
                      first_token_latency: firstTokenLatency,
                      timestamp: Date.now()
                    }
                  }))
                );

                firstTokenSent = true;
              }

              currentContent += chunk;
              totalTokens++;

              // Send message chunk
              controller.enqueue(
                encoder.encode(createSSEMessage({
                  event: EventType.MESSAGE,
                  data: {
                    content: chunk,
                    timestamp: Date.now()
                  }
                }))
              );

              // Record chunk performance
              performanceMonitor.recordChunk(requestId, chunk.length, Date.now() - startTime);
            },
            // onError - called on streaming errors
            async (error: Error) => {
              performanceMonitor.recordError(requestId, error.message);

              controller.enqueue(
                encoder.encode(createSSEMessage({
                  event: EventType.ERROR,
                  data: {
                    error: error.message,
                    timestamp: Date.now()
                  }
                }))
              );

              controller.close();
            },
            // onComplete - called when streaming finishes
            async (metadata) => {
              const totalTime = Date.now() - startTime;
              messageId = metadata.messageId;

              // Perform tone validation
              let toneValidation: any = null;
              if (currentContent && currentContent.length > 50) {
                try {
                  toneValidation = validateTone(currentContent);
                } catch (error) {
                  console.warn('Tone validation failed:', error);
                }
              }

              // Complete performance monitoring
              const metrics = performanceMonitor.completeStream(requestId, {
                totalTokens,
                modelUsed: metadata.modelUsed || model,
                finishReason: metadata.finishReason
              });

              // Send completion metrics with tone validation
              controller.enqueue(
                encoder.encode(createSSEMessage({
                  event: EventType.METRICS,
                  data: {
                    total_tokens: totalTokens,
                    total_time: totalTime,
                    tokens_per_second: metrics?.tokensPerSecond,
                    finish_reason: metadata.finishReason,
                    model_used: metadata.modelUsed || model,
                    system_prompt_time_ms: systemPromptTime,
                    tone_validation: toneValidation ? {
                      score: toneValidation.overallScore,
                      is_valid: toneValidation.isValid,
                      categories: Object.keys(toneValidation.categories).map(key => ({
                        name: key,
                        score: toneValidation.categories[key].score,
                        passed: toneValidation.categories[key].passed
                      }))
                    } : null
                  }
                }))
              );

              // Send completion event with tone validation
              controller.enqueue(
                encoder.encode(createSSEMessage({
                  event: EventType.COMPLETE,
                  data: {
                    message_id: messageId,
                    total_tokens: totalTokens,
                    total_time: totalTime,
                    model_used: metadata.modelUsed || model,
                    finish_reason: metadata.finishReason,
                    tone_validation: toneValidation ? {
                      overall_score: toneValidation.overallScore,
                      is_valid: toneValidation.isValid,
                      critical_issues: toneValidation.issues
                        .filter(issue => issue.severity === 'high')
                        .map(issue => issue.message)
                    } : null
                  }
                }))
              );

              // Persist messages to database
              try {
                // Save user message
                await messageService.createMessage({
                  conversationId,
                  role: 'user',
                  content: message,
                  timestamp: new Date()
                });

                // Save assistant response
                if (messageId && currentContent) {
                  await messageService.createMessage({
                    conversationId,
                    role: 'assistant',
                    content: currentContent,
                    timestamp: new Date(),
                    metadata: {
                      messageId,
                      modelUsed: metadata.modelUsed || model,
                      totalTokens,
                      totalTime,
                      finishReason: metadata.finishReason,
                      systemPrompt: {
                        length: systemPrompt.length,
                        constructionTimeMs: systemPromptTime,
                        standingInstructionsCount: standingInstructions.length,
                        hasUserProfile: !!user_context
                      },
                      toneValidation: toneValidation ? {
                        overallScore: toneValidation.overallScore,
                        isValid: toneValidation.isValid,
                        categoryScores: Object.entries(toneValidation.categories).map(([key, category]) => ({
                          category: key,
                          score: category.score,
                          passed: category.passed
                        }))
                      } : null
                    }
                  });
                }
              } catch (dbError) {
                console.error('Failed to persist messages:', dbError);
                // Don't fail the response, just log the error
              }

              controller.close();
            }
          );

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown streaming error';
          performanceMonitor.recordError(requestId, errorMessage);

          controller.enqueue(
            encoder.encode(createSSEMessage({
              event: EventType.ERROR,
              data: {
                error: errorMessage,
                timestamp: Date.now()
              }
            }))
          );

          controller.close();
        }
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown server error';

    return NextResponse.json(
      {
        error: 'Internal server error',
        message: errorMessage,
        request_id: requestId
      },
      { status: 500 }
    );
  }
}

// GET endpoint for connection health check
export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'chat-streaming-api'
  });
}