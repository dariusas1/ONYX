import { db } from './database';

export interface AuditLogEntry {
  id: string;
  userId: string;
  action: 'mode_change' | 'warning_shown' | 'warning_accepted' | 'warning_rejected' | 'agent_enabled' | 'agent_disabled' | 'consent_revoked';
  details: {
    fromMode?: string;
    toMode?: string;
    fromEnabled?: boolean;
    toEnabled?: boolean;
    timestamp?: string;
    ipAddress?: string;
    userAgent?: string;
    sessionId?: string;
    consentTimestamp?: string;
    enabledAt?: string;
    disabledAt?: string;
    [key: string]: any;
  };
  ipAddress?: string;
  userAgent?: string;
  sessionId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAuditLogParams {
  action: string;
  details: any;
  userId: string;
  ipAddress?: string;
  userAgent?: string;
  sessionId?: string;
}

/**
 * Create an audit log entry for agent mode actions
 */
export async function logAgentModeAudit(
  userId: string,
  params: CreateAuditLogParams
): Promise<AuditLogEntry> {
  try {
    const {
      action,
      details,
      ipAddress,
      userAgent,
      sessionId,
    } = params;

    const result = await db.query(
      `INSERT INTO agent_mode_audit_logs
       (user_id, action, details, ip_address, user_agent, session_id, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
       RETURNING *`,
      [
        userId,
        action,
        JSON.stringify(details),
        ipAddress || null,
        userAgent || null,
        sessionId || null,
      ]
    );

    const log = result.rows[0];

    return {
      id: log.id,
      userId: log.user_id,
      action: log.action,
      details: log.details,
      ipAddress: log.ip_address,
      userAgent: log.user_agent,
      sessionId: log.session_id,
      createdAt: log.created_at,
      updatedAt: log.updated_at,
    };
  } catch (error) {
    console.error('Error creating audit log:', error);
    throw error;
  }
}

/**
 * Get audit logs for a specific user
 */
export async function getUserAuditLogs(
  userId: string,
  options: {
    limit?: number;
    offset?: number;
    action?: string;
    startDate?: string;
    endDate?: string;
  } = {}
): Promise<AuditLogEntry[]> {
  try {
    const {
      limit = 100,
      offset = 0,
      action,
      startDate,
      endDate,
    } = options;

    let query = `
      SELECT
        id,
        user_id as "userId",
        action,
        details,
        ip_address as "ipAddress",
        user_agent as "userAgent",
        session_id as "sessionId",
        created_at as "createdAt",
        updated_at as "updatedAt"
      FROM agent_mode_audit_logs
      WHERE user_id = $1
    `;

    const params: any[] = [userId];
    let paramIndex = 2;

    if (action) {
      query += ` AND action = $${paramIndex}`;
      params.push(action);
      paramIndex++;
    }

    if (startDate) {
      query += ` AND created_at >= $${paramIndex}`;
      params.push(startDate);
      paramIndex++;
    }

    if (endDate) {
      query += ` AND created_at <= $${paramIndex}`;
      params.push(endDate);
      paramIndex++;
    }

    query += ` ORDER BY created_at DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
    params.push(limit, offset);

    const result = await db.query(query, params);

    return result.rows.map(row => ({
      id: row.id,
      userId: row.userId,
      action: row.action,
      details: row.details,
      ipAddress: row.ipAddress,
      userAgent: row.userAgent,
      sessionId: row.sessionId,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    }));
  } catch (error) {
    console.error('Error fetching user audit logs:', error);
    throw error;
  }
}

/**
 * Get recent audit logs for monitoring
 */
export async function getRecentAuditLogs(
  limit: number = 50,
  action?: string
): Promise<AuditLogEntry[]> {
  try {
    let query = `
      SELECT
        id,
        user_id as "userId",
        action,
        details,
        ip_address as "ipAddress",
        user_agent as "userAgent",
        session_id as "sessionId",
        created_at as "createdAt",
        updated_at as "updatedAt"
      FROM agent_mode_audit_logs
    `;

    const params: any[] = [];
    let paramIndex = 1;

    if (action) {
      query += ` WHERE action = $${paramIndex}`;
      params.push(action);
      paramIndex++;
    }

    query += ` ORDER BY created_at DESC LIMIT $${paramIndex}`;
    params.push(limit);

    const result = await db.query(query, params);

    return result.rows.map(row => ({
      id: row.id,
      userId: row.userId,
      action: row.action,
      details: row.details,
      ipAddress: row.ipAddress,
      userAgent: row.userAgent,
      sessionId: row.sessionId,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    }));
  } catch (error) {
    console.error('Error fetching recent audit logs:', error);
    throw error;
  }
}

/**
 * Get audit log statistics for reporting
 */
export async function getAuditLogStats(
  userId?: string,
  options: {
    startDate?: string;
    endDate?: string;
  } = {}
): Promise<any> {
  try {
    const { startDate, endDate } = options;

    let whereClause = '';
    const params: any[] = [];

    if (userId) {
      whereClause = 'WHERE user_id = $1';
      params.push(userId);
    }

    if (startDate) {
      whereClause += whereClause ? ' AND ' : 'WHERE ';
      whereClause += 'created_at >= $' + (params.length + 1);
      params.push(startDate);
    }

    if (endDate) {
      whereClause += whereClause ? ' AND ' : ' WHERE ';
      whereClause += 'created_at <= $' + (params.length + 1);
      params.push(endDate);
    }

    const query = `
      SELECT
        COUNT(*) as total_entries,
        COUNT(*) FILTER (WHERE action = 'mode_change') as mode_changes,
        COUNT(*) FILTER (WHERE action = 'warning_shown') as warnings_shown,
        COUNT(*) FILTER (WHERE action = 'warning_accepted') as warnings_accepted,
        COUNT(*) FILTER (WHERE action = 'warning_rejected') as warnings_rejected,
        COUNT(*) FILTER (WHERE action = 'agent_enabled') as agent_enabled,
        COUNT(*) FILTER (WHERE action = 'agent_disabled') as agent_disabled,
        COUNT(*) FILTER (WHERE action = 'consent_revoked') as consent_revoked
      FROM agent_mode_audit_logs
      ${whereClause}
    `;

    const result = await db.query(query, params);

    return {
      totalEntries: parseInt(result.rows[0].total_entries),
      modeChanges: parseInt(result.rows[0].mode_changes),
      warningsShown: parseInt(result.rows[0].warnings_shown),
      warningsAccepted: parseInt(result.rows[0].warnings_accepted),
      warningsRejected: parseInt(result.rows[0].warnings_rejected),
      agentEnabled: parseInt(result.rows[0].agent_enabled),
      agentDisabled: parseInt(result.rows[0].agent_disabled),
      consentRevoked: parseInt(result.rows[0].consent_revoked),
    };
  } catch (error) {
    console.error('Error getting audit log stats:', error);
    throw error;
  }
}

/**
 * Clean up old audit logs (for maintenance)
 */
export async function cleanupOldAuditLogs(daysToKeep: number = 365): Promise<number> {
  try {
    const result = await db.query(
      `DELETE FROM agent_mode_audit_logs
       WHERE created_at < NOW() - INTERVAL '${daysToKeep} days'
       RETURNING COUNT(*) as deleted_count`,
      []
    );

    return parseInt(result.rows[0].deleted_count);
  } catch (error) {
    console.error('Error cleaning up old audit logs:', error);
    throw error;
  }
}