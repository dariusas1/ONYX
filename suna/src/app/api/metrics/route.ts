/**
 * Prometheus Metrics Endpoint for Suna Frontend
 *
 * Exposes Prometheus metrics for monitoring and observability.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getMetricsCollector } from '../../../lib/metrics';

/**
 * Metrics endpoint for Prometheus scraping
 */
export async function GET(request: NextRequest) {
  try {
    const collector = getMetricsCollector();
    const metrics = collector.getMetrics();

    return new NextResponse(metrics, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; version=0.0.4',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });

  } catch (error) {
    console.error('Metrics endpoint error:', error);

    return new NextResponse('Metrics collection failed', {
      status: 500,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}