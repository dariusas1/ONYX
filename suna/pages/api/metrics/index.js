/**
 * Metrics API Endpoint for ONYX
 *
 * Provides Prometheus metrics endpoint for Suna frontend
 * Implements basic authentication and <10ms response time target
 */

const { metricsHandler } = require('../../../lib/metrics');

// Basic authentication for metrics endpoint
function basicAuth(req) {
  const auth = req.headers.authorization;
  if (!auth) return false;

  const [type, credentials] = auth.split(' ');
  if (type !== 'Basic') return false;

  const [username, password] = Buffer.from(credentials, 'base64')
    .toString('utf-8')
    .split(':');

  // Check against environment variables or defaults
  const validUsername = process.env.METRICS_USERNAME || 'admin';
  const validPassword = process.env.METRICS_PASSWORD || 'admin';

  return username === validUsername && password === validPassword;
}

export default async function handler(req, res) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET']);
    return res.status(405).end('Method Not Allowed');
  }

  // Basic authentication
  if (!basicAuth(req)) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Metrics"');
    return res.status(401).end('Unauthorized');
  }

  // Set cache headers to prevent caching of metrics
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');

  try {
    await metricsHandler(req, res);
  } catch (error) {
    console.error('Metrics endpoint error:', error);
    res.status(500).end('Internal Server Error');
  }
}