// Health check endpoint for Suna frontend
// This will be replaced with proper Next.js API route once dependencies are installed

export default async function handler(req, res) {
  try {
    const startTime = Date.now();
    
    // Basic health checks
    const checks = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      responseTime: 0,
      version: '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      services: {
        frontend: {
          status: 'healthy',
          responseTime: '0ms'
        }
      },
      uptime: typeof process !== 'undefined' ? process.uptime() : 0
    };

    checks.responseTime = Date.now() - startTime;

    res.status(200).json(checks);
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}