/**
 * Enhanced Health Check Endpoint for Suna Frontend
 *
 * Provides comprehensive health status including dependency checks,
 * system metrics, and service information.
 */

import { logInfo, logError, logTimer } from '../../../lib/logger';

// Health check configuration
const HEALTH_CONFIG = {
  timeoutMs: 5000, // Maximum time for health checks
  dependencies: {
    onyxCore: {
      url: process.env.NEXT_PUBLIC_API_BASE ?
        `${process.env.NEXT_PUBLIC_API_BASE.replace(/\/$/, '')}/health` :
        'http://localhost:8080/health',
      timeout: 3000,
      required: true
    }
  }
};

/**
 * Check dependency health
 */
async function checkDependency(name, config) {
  const startTime = Date.now();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    const response = await fetch(config.url, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'User-Agent': 'suna-health-check/1.0.0'
      }
    });

    clearTimeout(timeoutId);

    const responseTime = Date.now() - startTime;

    if (!response.ok) {
      return {
        status: 'unhealthy',
        error: `HTTP ${response.status}: ${response.statusText}`,
        responseTime: `${responseTime}ms`,
        url: config.url
      };
    }

    const data = await response.json();

    return {
      status: 'healthy',
      responseTime: `${responseTime}ms`,
      url: config.url,
      data: {
        overall: data.status,
        services: data.services || {},
        version: data.version || 'unknown'
      }
    };

  } catch (error) {
    const responseTime = Date.now() - startTime;

    return {
      status: 'unhealthy',
      error: error.name === 'AbortError' ? 'Timeout' : error.message,
      responseTime: `${responseTime}ms`,
      url: config.url
    };
  }
}

/**
 * Get system metrics
 */
function getSystemMetrics() {
  const memUsage = process.memoryUsage();
  const uptime = process.uptime();

  return {
    uptime: Math.floor(uptime),
    uptime_formatted: formatUptime(uptime),
    memory: {
      rss: formatBytes(memUsage.rss),
      heap_used: formatBytes(memUsage.heapUsed),
      heap_total: formatBytes(memUsage.heapTotal),
      external: formatBytes(memUsage.external),
      heap_usage_percent: Math.round((memUsage.heapUsed / memUsage.heapTotal) * 100)
    },
    cpu: process.cpuUsage(),
    node_version: process.version,
    platform: process.platform
  };
}

/**
 * Format uptime to human readable string
 */
function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}

/**
 * Format bytes to human readable string
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Main health check handler
 */
export default async function handler(req, res) {
  const requestId = req.headers['x-request-id'] || `health_${Date.now()}`;
  const endTimer = logTimer('health_check', { request_id: requestId }, requestId);

  try {
    const startTime = Date.now();

    // Check all dependencies
    const dependencyChecks = {};
    const dependencyPromises = [];

    for (const [name, config] of Object.entries(HEALTH_CONFIG.dependencies)) {
      dependencyPromises.push(
        checkDependency(name, config)
          .then(result => ({ name, result }))
          .catch(error => ({
            name,
            result: {
              status: 'unhealthy',
              error: error.message
            }
          }))
      );
    }

    const dependencyResults = await Promise.all(dependencyPromises);

    // Organize dependency results
    for (const { name, result } of dependencyResults) {
      dependencyChecks[name] = result;

      // Log dependency status
      if (result.status === 'healthy') {
        logInfo('dependency_healthy', {
          dependency: name,
          response_time: result.responseTime,
          url: result.url
        }, requestId);
      } else {
        logError('dependency_unhealthy', {
          dependency: name,
          error: result.error,
          url: result.url
        }, result.error, requestId);
      }
    }

    // Determine overall health
    const allHealthy = Object.values(dependencyChecks).every(
      dep => dep.status === 'healthy'
    );
    const requiredHealthy = Object.entries(dependencyChecks)
      .filter(([name]) => HEALTH_CONFIG.dependencies[name]?.required !== false)
      .every(([, dep]) => dep.status === 'healthy');

    const overallStatus = requiredHealthy ? 'healthy' : 'unhealthy';

    // Get system metrics
    const metrics = getSystemMetrics();

    // Build response
    const healthResponse = {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      response_time: `${Date.now() - startTime}ms`,
      version: process.env.npm_package_version || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      service: 'suna-frontend',
      uptime: metrics.uptime,
      metrics: metrics,
      dependencies: dependencyChecks,
      checks: {
        total: Object.keys(dependencyChecks).length,
        healthy: Object.values(dependencyChecks).filter(d => d.status === 'healthy').length,
        unhealthy: Object.values(dependencyChecks).filter(d => d.status === 'unhealthy').length
      },
      endpoints: {
        health: '/api/health',
        metrics: '/api/metrics'
      }
    };

    // Add additional metadata
    if (process.env.GIT_COMMIT) {
      healthResponse.git_commit = process.env.GIT_COMMIT;
    }

    if (process.env.BUILD_DATE) {
      healthResponse.build_date = process.env.BUILD_DATE;
    }

    endTimer();

    // Log health check completion
    logInfo('health_check_completed', {
      status: overallStatus,
      total_dependencies: Object.keys(dependencyChecks).length,
      healthy_dependencies: healthResponse.checks.healthy,
      response_time: healthResponse.response_time
    }, requestId);

    // Set appropriate status code
    const statusCode = overallStatus === 'healthy' ? 200 : 503;

    return res.status(statusCode).json(healthResponse);

  } catch (error) {
    endTimer();

    const errorResponse = {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error',
      service: 'suna-frontend'
    };

    logError('health_check_failed', {
      error: error.message,
      stack: error.stack
    }, error instanceof Error ? error.message : 'Unknown error', requestId);

    return res.status(503).json(errorResponse);
  }
}