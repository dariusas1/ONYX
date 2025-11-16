'use client';

import React, { useState, useEffect } from 'react';
import { Brain, Clock, TrendingUp, AlertCircle, X, ChevronDown, ChevronUp } from 'lucide-react';

interface MemoryInjection {
  memories_count: number;
  instructions_count: number;
  injection_time_ms: number;
  performance_stats: {
    cache_hit?: boolean;
    memories?: Array<{
      fact: string;
      category: string;
      confidence: number;
    }>;
    instructions?: Array<{
      instruction_text: string;
      category: string;
      priority: number;
    }>;
  };
}

interface MemoryInjectionNotificationProps {
  injection: MemoryInjection | null;
  onDismiss?: () => void;
  className?: string;
}

export function MemoryInjectionNotification({
  injection,
  onDismiss,
  className = '',
}: MemoryInjectionNotificationProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // Auto-hide after 8 seconds
  useEffect(() => {
    if (injection && injection.memories_count + injection.instructions_count > 0) {
      setIsVisible(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => onDismiss?.(), 300); // Wait for fade-out animation
      }, 8000);

      return () => clearTimeout(timer);
    }
  }, [injection, onDismiss]);

  if (!injection || !isVisible || (injection.memories_count === 0 && injection.instructions_count === 0)) {
    return null;
  }

  const totalItems = injection.memories_count + injection.instructions_count;
  const hasCacheHit = injection.performance_stats?.cache_hit;
  const performanceMs = injection.injection_time_ms;

  // Performance rating
  const getPerformanceRating = () => {
    if (performanceMs < 50) return { label: 'Excellent', color: 'text-green-500' };
    if (performanceMs < 100) return { label: 'Good', color: 'text-blue-500' };
    if (performanceMs < 200) return { label: 'Fair', color: 'text-yellow-500' };
    return { label: 'Slow', color: 'text-red-500' };
  };

  const performanceRating = getPerformanceRating();

  return (
    <div
      className={`
        fixed top-4 right-4 max-w-md bg-white border border-gray-200 rounded-lg shadow-lg
        transition-all duration-300 ease-in-out z-50
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'}
        ${className}
      `}
      role="status"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Brain className="w-5 h-5 text-indigo-500" />
            {hasCacheHit && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full"
                   title="Cache hit - loaded from memory" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Memory Recall Active</h3>
            <p className="text-xs text-gray-500">
              {totalItems} context items loaded
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${performanceRating.color}`}>
            {performanceRating.label}
          </span>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>
          <button
            onClick={() => {
              setIsVisible(false);
              setTimeout(() => onDismiss?.(), 300);
            }}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            aria-label="Dismiss notification"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-4 py-3 grid grid-cols-3 gap-4 text-center border-b border-gray-100">
        <div>
          <div className="text-lg font-semibold text-indigo-600">
            {injection.memories_count}
          </div>
          <div className="text-xs text-gray-500">Memories</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-blue-600">
            {injection.instructions_count}
          </div>
          <div className="text-xs text-gray-500">Instructions</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-600">
            {performanceMs}ms
          </div>
          <div className="text-xs text-gray-500">Load Time</div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-4 py-3 space-y-3 max-h-64 overflow-y-auto">
          {/* Memories */}
          {injection.memories_count > 0 && injection.performance_stats?.memories && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Brain className="w-4 h-4 text-indigo-500" />
                Key Memories Retrieved
              </h4>
              <div className="space-y-2">
                {injection.performance_stats.memories.slice(0, 3).map((memory, index) => (
                  <div key={index} className="text-xs p-2 bg-indigo-50 rounded border border-indigo-100">
                    <p className="text-gray-700 line-clamp-2">{memory.fact}</p>
                    <div className="flex items-center gap-2 mt-1 text-gray-500">
                      <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded text-xs">
                        {memory.category}
                      </span>
                      <span className="text-xs">
                        {Math.round(memory.confidence * 100)}% confidence
                      </span>
                    </div>
                  </div>
                ))}
                {injection.memories_count > 3 && (
                  <p className="text-xs text-gray-500 italic">
                    ... and {injection.memories_count - 3} more memories
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Standing Instructions */}
          {injection.instructions_count > 0 && injection.performance_stats?.instructions && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-500" />
                Standing Instructions Applied
              </h4>
              <div className="space-y-2">
                {injection.performance_stats.instructions.slice(0, 3).map((instruction, index) => (
                  <div key={index} className="text-xs p-2 bg-blue-50 rounded border border-blue-100">
                    <p className="text-gray-700 line-clamp-2">{instruction.instruction_text}</p>
                    <div className="flex items-center gap-2 mt-1 text-gray-500">
                      <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-xs">
                        {instruction.category}
                      </span>
                      <span className="text-xs">
                        Priority {instruction.priority}
                      </span>
                    </div>
                  </div>
                ))}
                {injection.instructions_count > 3 && (
                  <p className="text-xs text-gray-500 italic">
                    ... and {injection.instructions_count - 3} more instructions
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Performance Info */}
          <div className="flex items-center gap-2 text-xs text-gray-500 pt-2 border-t border-gray-100">
            <Clock className="w-3 h-3" />
            <span>
              {hasCacheHit ? 'Loaded from cache' : 'Fresh data retrieved'}
            </span>
            <span>•</span>
            <span className={performanceRating.color}>
              {performanceRating.label.toLowerCase()} performance
            </span>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      <div className="px-4 pb-3">
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-gradient-to-r from-indigo-500 to-blue-500 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, (totalItems / 10) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// Hook for using memory injection notifications
export function useMemoryInjectionNotification() {
  const [injection, setInjection] = useState<MemoryInjection | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  const showNotification = (injectionData: MemoryInjection) => {
    setInjection(injectionData);
    setIsVisible(true);
  };

  const hideNotification = () => {
    setIsVisible(false);
    setTimeout(() => setInjection(null), 300);
  };

  return {
    injection: isVisible ? injection : null,
    isVisible,
    showNotification,
    hideNotification,
  };
}