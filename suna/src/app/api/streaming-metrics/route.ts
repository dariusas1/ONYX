/**
 * Streaming Metrics API - Real-time chat performance monitoring
 *
 * Provides comprehensive metrics for chat streaming performance
 * including latency, throughput, and quality indicators.
 */

import { NextRequest, NextResponse } from 'next/server';
import { performanceMonitor } from '@/lib/performance-monitor';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const conversationId = searchParams.get('conversationId');

    // Get overall performance metrics
    const metrics = performanceMonitor.exportMetrics();

    // Get conversation-specific summary if requested
    let conversationSummary = null;
    if (conversationId) {
      conversationSummary = performanceMonitor.getConversationSummary(conversationId);
    }

    // Get performance recommendations
    const recommendations = conversationId
      ? performanceMonitor.getRecommendations(conversationId)
      : performanceMonitor.getRecommendations('all');

    // Cleanup old metrics
    performanceMonitor.cleanup();

    return NextResponse.json({
      timestamp: new Date().toISOString(),
      metrics,
      conversationSummary,
      recommendations,
      status: 'healthy'
    });
  } catch (error) {
    console.error('Failed to get streaming performance metrics:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch streaming performance metrics',
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, data } = body;

    switch (action) {
      case 'cleanup':
        performanceMonitor.cleanup();
        return NextResponse.json({ message: 'Streaming metrics cleaned up' });

      case 'reset':
        // Reset all metrics (for testing)
        performanceMonitor.cleanup();
        return NextResponse.json({ message: 'Streaming metrics reset' });

      case 'recommendations':
        const { conversationId } = data || {};
        const recommendations = performanceMonitor.getRecommendations(conversationId);
        return NextResponse.json({ recommendations });

      default:
        return NextResponse.json(
          { error: `Unknown action: ${action}` },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error('Failed to process streaming metrics request:', error);
    return NextResponse.json(
      { error: 'Failed to process streaming metrics request' },
      { status: 500 }
    );
  }
}