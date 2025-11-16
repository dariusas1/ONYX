/**
 * Constants for Standing Instructions Management
 */

import { CategoryInfo } from './types';

export const INSTRUCTION_CATEGORIES: CategoryInfo[] = [
  {
    value: 'workflow',
    label: 'Workflow Preferences',
    icon: '⚙️',
    color: '#8b5cf6',
    description: 'Process guidelines and workflow optimization'
  },
  {
    value: 'decision',
    label: 'Decision Making',
    icon: '⚖️',
    color: '#f59e0b',
    description: 'Decision frameworks and criteria'
  },
  {
    value: 'communication',
    label: 'Communication Style',
    icon: '💬',
    color: '#10b981',
    description: 'Tone, format, and communication preferences'
  },
  {
    value: 'security',
    label: 'Security & Privacy',
    icon: '🔒',
    color: '#ef4444',
    description: 'Security protocols and privacy requirements'
  },
  {
    value: 'general',
    label: 'General Behavior',
    icon: '🗣️',
    color: '#3b82f6',
    description: 'General behavioral guidelines and personality'
  }
];

export const PRIORITY_LABELS = {
  1: 'Very Low',
  2: 'Low',
  3: 'Low-Medium',
  4: 'Medium-Low',
  5: 'Medium',
  6: 'Medium-High',
  7: 'High-Medium',
  8: 'High',
  9: 'Very High',
  10: 'Critical'
};

export const SORT_OPTIONS = [
  { value: 'priority', label: 'Priority' },
  { value: 'usage', label: 'Usage Count' },
  { value: 'category', label: 'Category' },
  { value: 'created', label: 'Created Date' }
];

export const INSTRUCTION_TEXT_LIMIT = 500;
export const CONTEXT_HINTS_LIMIT = 10;
export const BULK_OPERATION_LIMIT = 50;

export const API_ENDPOINTS = {
  INSTRUCTIONS: '/api/instructions',
  ANALYTICS: '/api/instructions/analytics/usage',
  BULK_STATUS: '/api/instructions/bulk-status',
  TEST_INJECTION: '/api/instructions/test-injection',
  HEALTH: '/api/instructions/health'
} as const;