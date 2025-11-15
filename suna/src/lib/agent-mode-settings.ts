import { db } from './database';

export interface AgentModeSettings {
  mode: 'chat' | 'agent';
  isEnabled: boolean;
  hasAcceptedWarning: boolean;
  consentTimestamp?: string;
  lastModeChange?: string | null;
  enabledAt?: string | null;
  disabledAt?: string | null;
}

export interface UpdateAgentModeSettingsParams {
  mode?: 'chat' | 'agent';
  isEnabled?: boolean;
  hasAcceptedWarning?: boolean;
  consentTimestamp?: string;
  ipAddress?: string;
  userAgent?: string;
}

/**
 * Get user's agent mode settings from database
 */
export async function getUserAgentModeSettings(userId: string): Promise<AgentModeSettings> {
  try {
    const result = await db.query(
      `SELECT
        agent_mode_preference as mode,
        agent_mode_enabled as "isEnabled",
        agent_mode_consent_accepted as "hasAcceptedWarning",
        agent_mode_consent_timestamp as "consentTimestamp",
        agent_mode_enabled_at as "enabledAt",
        agent_mode_disabled_at as "disabledAt"
       FROM users
       WHERE id = $1`,
      [userId]
    );

    if (result.rows.length === 0) {
      // Return default settings if user not found
      return {
        mode: 'chat',
        isEnabled: false,
        hasAcceptedWarning: false,
      };
    }

    const user = result.rows[0];

    // Get last mode change from audit logs
    const lastModeChangeResult = await db.query(
      `SELECT created_at
       FROM agent_mode_audit_logs
       WHERE user_id = $1 AND action = 'mode_change'
       ORDER BY created_at DESC
       LIMIT 1`,
      [userId]
    );

    return {
      mode: user.mode || 'chat',
      isEnabled: user.isEnabled || false,
      hasAcceptedWarning: user.hasAcceptedWarning || false,
      consentTimestamp: user.consentTimestamp,
      lastModeChange: lastModeChangeResult.rows[0]?.created_at || null,
      enabledAt: user.enabledAt,
      disabledAt: user.disabledAt,
    };
  } catch (error) {
    console.error('Error fetching agent mode settings:', error);
    throw error;
  }
}

/**
 * Update user's agent mode settings in database
 */
export async function updateUserAgentModeSettings(
  userId: string,
  params: UpdateAgentModeSettingsParams
): Promise<AgentModeSettings> {
  try {
    const {
      mode,
      isEnabled,
      hasAcceptedWarning,
      consentTimestamp,
      ipAddress,
      userAgent,
    } = params;

    // Build update query dynamically
    const updates: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (mode !== undefined) {
      updates.push(`agent_mode_preference = $${paramIndex}`);
      values.push(mode);
      paramIndex++;
    }

    if (isEnabled !== undefined) {
      updates.push(`agent_mode_enabled = $${paramIndex}`);
      values.push(isEnabled);
      paramIndex++;

      // Set enabled/disabled timestamps
      if (isEnabled) {
        updates.push(`agent_mode_enabled_at = NOW()`);
      } else {
        updates.push(`agent_mode_disabled_at = NOW()`);
      }
    }

    if (hasAcceptedWarning !== undefined) {
      updates.push(`agent_mode_consent_accepted = $${paramIndex}`);
      values.push(hasAcceptedWarning);
      paramIndex++;

      if (hasAcceptedWarning && consentTimestamp) {
        updates.push(`agent_mode_consent_timestamp = $${paramIndex}`);
        values.push(consentTimestamp);
        paramIndex++;
      }

      if (hasAcceptedWarning && ipAddress) {
        updates.push(`agent_mode_consent_ip_address = $${paramIndex}`);
        values.push(ipAddress);
        paramIndex++;
      }
    }

    if (updates.length === 0) {
      throw new Error('No valid fields to update');
    }

    // Add userId to values array
    values.push(userId);

    // Update user settings
    await db.query(
      `UPDATE users
       SET ${updates.join(', ')}, updated_at = NOW()
       WHERE id = $${paramIndex}`,
      values
    );

    // Return updated settings
    return await getUserAgentModeSettings(userId);
  } catch (error) {
    console.error('Error updating agent mode settings:', error);
    throw error;
  }
}

/**
 * Check if user has enabled agent mode and accepted warning
 */
export async function canUserUseAgentMode(userId: string): Promise<boolean> {
  try {
    const settings = await getUserAgentModeSettings(userId);
    return settings.isEnabled && settings.hasAcceptedWarning;
  } catch (error) {
    console.error('Error checking agent mode permission:', error);
    return false;
  }
}

/**
 * Get agent mode usage statistics for analytics
 */
export async function getAgentModeUsageStats(userId?: string): Promise<any> {
  try {
    let query = `
      SELECT
        COUNT(*) as total_users,
        COUNT(*) FILTER (WHERE agent_mode_enabled = true) as enabled_users,
        agent_mode_preference,
        COUNT(*) as count
      FROM users
      ${userId ? 'WHERE id = $1' : ''}
      GROUP BY agent_mode_preference
    `;

    const params = userId ? [userId] : [];

    const result = await db.query(query, params);

    return {
      totalUsers: result.rows.reduce((sum, row) => sum + parseInt(row.count), 0),
      enabledUsers: result.rows.reduce((sum, row) => sum + (row.agent_mode_enabled ? parseInt(row.count) : 0), 0),
      modeDistribution: result.rows.map(row => ({
        mode: row.agent_mode_preference,
        count: parseInt(row.count),
        percentage: ((parseInt(row.count) / result.rows.reduce((sum, r) => sum + parseInt(r.count), 0)) * 100).toFixed(2)
      }))
    };
  } catch (error) {
    console.error('Error getting agent mode usage stats:', error);
    throw error;
  }
}

/**
 * Get recent agent mode activity for monitoring
 */
export async function getRecentAgentModeActivity(limit: number = 50): Promise<any[]> {
  try {
    const result = await db.query(
      `SELECT
        aml.id,
        aml.user_id,
        u.email as user_email,
        aml.action,
        aml.details,
        aml.ip_address,
        aml.user_agent,
        aml.session_id,
        aml.created_at
       FROM agent_mode_audit_logs aml
       JOIN users u ON aml.user_id = u.id
       ORDER BY aml.created_at DESC
       LIMIT $1`,
      [limit]
    );

    return result.rows;
  } catch (error) {
    console.error('Error getting recent agent mode activity:', error);
    throw error;
  }
}