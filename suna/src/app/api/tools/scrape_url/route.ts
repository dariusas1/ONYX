/**
 * Next.js API Route for URL Scraping
 *
 * This route proxies requests to the ONYX core FastAPI backend.
 * Provides a clean interface for the frontend to call scraping functionality.
 */

import { NextRequest, NextResponse } from 'next/server';

// Configuration for the ONYX core backend
const ONYX_CORE_URL = process.env.ONYX_CORE_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();

    // Validate request body
    if (!body.url) {
      return NextResponse.json(
        {
          success: false,
          error: {
            code: 'MISSING_URL',
            message: 'URL parameter is required'
          }
        },
        { status: 400 }
      );
    }

    // Basic URL validation
    try {
      new URL(body.url);
    } catch {
      return NextResponse.json(
        {
          success: false,
          error: {
            code: 'INVALID_URL',
            message: 'Invalid URL format provided'
          }
        },
        { status: 400 }
      );
    }

    // Forward request to ONYX core backend
    const response = await fetch(`${ONYX_CORE_URL}/tools/scrape_url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward any authentication headers
        ...(request.headers.get('authorization') && {
          Authorization: request.headers.get('authorization')!
        }),
      },
      body: JSON.stringify(body),
      // Set timeout to prevent hanging
      signal: AbortSignal.timeout(15000), // 15 seconds timeout
    });

    // Forward the response
    const data = await response.json();

    // Return the response with appropriate status
    return NextResponse.json(data, { status: response.status });

  } catch (error) {
    console.error('Scrape URL API route error:', error);

    // Handle different types of errors
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return NextResponse.json(
          {
            success: false,
            error: {
              code: 'TIMEOUT',
              message: 'Request timed out after 15 seconds'
            }
          },
          { status: 408 }
        );
      }

      if (error.message.includes('fetch')) {
        return NextResponse.json(
          {
            success: false,
            error: {
              code: 'SERVICE_UNAVAILABLE',
              message: 'Scraping service is currently unavailable'
            }
          },
          { status: 503 }
        );
      }
    }

    // Generic error response
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An unexpected error occurred while processing your request'
        }
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  // Health check endpoint
  try {
    const response = await fetch(`${ONYX_CORE_URL}/tools/scrape_url/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 seconds timeout
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });

  } catch (error) {
    console.error('Scrape URL health check error:', error);

    return NextResponse.json(
      {
        status: 'unhealthy',
        service: 'scrape_url',
        error: 'Health check failed',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }
}