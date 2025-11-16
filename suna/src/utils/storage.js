/**
 * LocalStorage utilities with error handling and fallbacks
 * Provides consistent interface for browser storage operations
 */

class StorageManager {
  constructor() {
    this.isAvailable = this.checkAvailability();
    this.prefix = 'onyx_';
  }

  /**
   * Check if localStorage is available
   */
  checkAvailability() {
    try {
      const testKey = '__onyx_storage_test__';
      localStorage.setItem(testKey, 'test');
      localStorage.removeItem(testKey);
      return true;
    } catch (error) {
      console.warn('localStorage is not available:', error);
      return false;
    }
  }

  /**
   * Get item from localStorage with error handling
   */
  get(key) {
    if (!this.isAvailable) {
      return null;
    }

    try {
      const prefixedKey = this.prefix + key;
      const item = localStorage.getItem(prefixedKey);

      if (item === null) {
        return null;
      }

      // Parse JSON if it looks like JSON
      if (item.startsWith('{') || item.startsWith('[') || item.startsWith('"')) {
        return JSON.parse(item);
      }

      return item;
    } catch (error) {
      console.error('Failed to get item from localStorage:', error);
      return null;
    }
  }

  /**
   * Set item in localStorage with error handling
   */
  set(key, value) {
    if (!this.isAvailable) {
      return false;
    }

    try {
      const prefixedKey = this.prefix + key;
      const serializedValue = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(prefixedKey, serializedValue);
      return true;
    } catch (error) {
      console.error('Failed to set item in localStorage:', error);
      return false;
    }
  }

  /**
   * Remove item from localStorage with error handling
   */
  remove(key) {
    if (!this.isAvailable) {
      return false;
    }

    try {
      const prefixedKey = this.prefix + key;
      localStorage.removeItem(prefixedKey);
      return true;
    } catch (error) {
      console.error('Failed to remove item from localStorage:', error);
      return false;
    }
  }

  /**
   * Check if item exists in localStorage
   */
  has(key) {
    if (!this.isAvailable) {
      return false;
    }

    try {
      const prefixedKey = this.prefix + key;
      return localStorage.getItem(prefixedKey) !== null;
    } catch (error) {
      console.error('Failed to check item in localStorage:', error);
      return false;
    }
  }

  /**
   * Clear all ONYX items from localStorage
   */
  clear() {
    if (!this.isAvailable) {
      return false;
    }

    try {
      const keys = Object.keys(localStorage);
      let cleared = 0;

      for (const key of keys) {
        if (key.startsWith(this.prefix)) {
          localStorage.removeItem(key);
          cleared++;
        }
      }

      return cleared > 0;
    } catch (error) {
      console.error('Failed to clear localStorage:', error);
      return false;
    }
  }

  /**
   * Get all ONYX items from localStorage
   */
  getAll() {
    if (!this.isAvailable) {
      return {};
    }

    try {
      const keys = Object.keys(localStorage);
      const items = {};

      for (const key of keys) {
        if (key.startsWith(this.prefix)) {
          const cleanKey = key.replace(this.prefix, '');
          items[cleanKey] = this.get(cleanKey);
        }
      }

      return items;
    } catch (error) {
      console.error('Failed to get all items from localStorage:', error);
      return {};
    }
  }

  /**
   * Get storage usage information
   */
  getStorageInfo() {
    if (!this.isAvailable) {
      return {
        used: 0,
        available: 0,
        total: 0,
        percentage: 0
      };
    }

    try {
      let used = 0;
      const keys = Object.keys(localStorage);

      for (const key of keys) {
        if (key.startsWith(this.prefix)) {
          used += localStorage.getItem(key).length;
        }
      }

      // Estimate available space (most browsers have ~5-10MB limit)
      const total = 5 * 1024 * 1024; // 5MB
      const available = total - used;
      const percentage = (used / total) * 100;

      return {
        used,
        available,
        total,
        percentage: Math.round(percentage * 100) / 100
      };
    } catch (error) {
      console.error('Failed to get storage info:', error);
      return {
        used: 0,
        available: 0,
        total: 0,
        percentage: 0
      };
    }
  }
}

// Create singleton instance
const storage = new StorageManager();

// Export utility functions for direct access
export const get = (key) => storage.get(key);
export const set = (key, value) => storage.set(key, value);
export const remove = (key) => storage.remove(key);
export const has = (key) => storage.has(key);
export const clear = () => storage.clear();
export const getAll = () => storage.getAll();
export const getStorageInfo = () => storage.getStorageInfo();

// Export the storage manager instance
export { storage };

// Export as default
export default storage;