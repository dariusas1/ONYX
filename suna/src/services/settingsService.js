'use client';

/**
 * Settings Service for ONYX application
 * Handles user settings with local storage and future Supabase integration
 */

import { storage } from '../utils/storage';

// Settings keys
const USER_SETTINGS_KEYS = {
  AGENT_MODE: 'agent_mode',
  THEME: 'theme',
  NOTIFICATIONS: 'notifications',
  AUTO_EXECUTE: 'auto_execute',
} as const;

/**
 * Settings service class
 */
export class SettingsService {
  /**
   * Get user setting from storage
   * @param key - Setting key
   * @param defaultValue - Default value if not found
   * @returns Setting value
   */
  static async getSetting(key, defaultValue = null) {
    try {
      // For now, use localStorage
      // In future, integrate with Supabase user_settings table
      return storage.get(`user_${key}`) || defaultValue;
    } catch (error) {
      console.warn(`Error getting setting "${key}":`, error);
      return defaultValue;
    }
  }

  /**
   * Set user setting
   * @param key - Setting key
   * @param value - Setting value
   * @returns Success status
   */
  static async setSetting(key, value) {
    try {
      // For now, use localStorage
      // In future, sync with Supabase user_settings table
      const storageKey = `user_${key}`;
      const success = storage.set(storageKey, value);

      if (success) {
        // Trigger sync event for future Supabase integration
        this.triggerSyncEvent(key, value);
      }

      return success;
    } catch (error) {
      console.warn(`Error setting "${key}":`, error);
      return false;
    }
  }

  /**
   * Get all user settings
   * @returns Object with all settings
   */
  static async getAllSettings() {
    try {
      const settings = {};

      // Get all known settings
      Object.values(USER_SETTINGS_KEYS).forEach(key => {
        settings[key] = storage.get(`user_${key}`);
      });

      return settings;
    } catch (error) {
      console.warn('Error getting all settings:', error);
      return {};
    }
  }

  /**
   * Update multiple settings
   * @param settings - Object with settings to update
   * @returns Success status
   */
  static async updateSettings(settings) {
    try {
      const results = {};

      for (const [key, value] of Object.entries(settings)) {
        results[key] = await this.setSetting(key, value);
      }

      return results;
    } catch (error) {
      console.warn('Error updating settings:', error);
      return {};
    }
  }

  /**
   * Delete user setting
   * @param key - Setting key
   * @returns Success status
   */
  static async deleteSetting(key) {
    try {
      // For now, use localStorage
      // In future, delete from Supabase user_settings table
      const storageKey = `user_${key}`;

      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(storageKey);
        return true;
      }

      return false;
    } catch (error) {
      console.warn(`Error deleting setting "${key}":`, error);
      return false;
    }
  }

  /**
   * Sync settings with cloud storage (future Supabase integration)
   * @param settings - Settings to sync
   * @returns Promise resolving to sync result
   */
  static async syncWithCloud(settings) {
    try {
      // Placeholder for future Supabase integration
      console.log('Syncing settings with cloud:', settings);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 100));

      // In future:
      // 1. Authenticate with Supabase
      // 2. Upsert to user_settings table
      // 3. Handle conflicts
      // 4. Return sync status

      return {
        success: true,
        synced: Object.keys(settings),
        conflicts: [],
      };
    } catch (error) {
      console.warn('Error syncing with cloud:', error);
      return {
        success: false,
        error: error.message,
        synced: [],
        conflicts: [],
      };
    }
  }

  /**
   * Load settings from cloud storage (future Supabase integration)
   * @returns Promise resolving to cloud settings
   */
  static async loadFromCloud() {
    try {
      // Placeholder for future Supabase integration
      console.log('Loading settings from cloud...');

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 100));

      // In future:
      // 1. Authenticate with Supabase
      // 2. Query user_settings table
      // 3. Handle conflicts with local settings
      // 4. Return merged settings

      return {
        success: true,
        settings: {},
        conflicts: [],
      };
    } catch (error) {
      console.warn('Error loading from cloud:', error);
      return {
        success: false,
        error: error.message,
        settings: {},
        conflicts: [],
      };
    }
  }

  /**
   * Trigger custom sync event for external listeners
   * @param key - Setting key
   * @param value - Setting value
   */
  static triggerSyncEvent(key, value) {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('settingSync', {
        detail: { key, value, timestamp: new Date().toISOString() },
      });
      window.dispatchEvent(event);
    }
  }

  /**
   * Listen for setting sync events
   * @param callback - Event handler callback
   * @returns Cleanup function
   */
  static onSyncEvent(callback) {
    if (typeof window !== 'undefined') {
      const handler = (event) => callback(event.detail);
      window.addEventListener('settingSync', handler);

      // Return cleanup function
      return () => {
        window.removeEventListener('settingSync', handler);
      };
    }

    return () => {}; // No-op for SSR
  }
}

// Export convenience functions for common settings
export const AgentModeSettings = {
  get: () => SettingsService.getSetting(USER_SETTINGS_KEYS.AGENT_MODE, 'chat'),
  set: (mode) => SettingsService.setSetting(USER_SETTINGS_KEYS.AGENT_MODE, mode),
  sync: () => SettingsService.syncWithCloud({ [USER_SETTINGS_KEYS.AGENT_MODE]: 'chat' }),
};

export { USER_SETTINGS_KEYS };