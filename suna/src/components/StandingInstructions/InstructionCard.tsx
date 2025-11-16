/**
 * InstructionCard Component
 *
 * Individual instruction card with display and actions
 */

import React, { useState } from 'react';
import { StandingInstruction, CategoryInfo } from './types';
import { INSTRUCTION_CATEGORIES, PRIORITY_LABELS } from './constants';
import { formatDistanceToNow } from 'date-fns';

interface InstructionCardProps {
  instruction: StandingInstruction;
  category: CategoryInfo;
  onEdit: (id: string) => void;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  isSelected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
  showSelection?: boolean;
}

const InstructionCard: React.FC<InstructionCardProps> = ({
  instruction,
  category,
  onEdit,
  onToggle,
  onDelete,
  isSelected = false,
  onSelect,
  showSelection = false
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleToggle = async () => {
    setIsLoading(true);
    try {
      await onToggle(instruction.id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this instruction?')) {
      setIsLoading(true);
      try {
        await onDelete(instruction.id);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return 'bg-red-100 text-red-800 border-red-200';
    if (priority >= 6) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (priority >= 4) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <div className={`bg-white rounded-lg border-2 p-4 transition-all duration-200 hover:shadow-md ${
      instruction.enabled ? 'border-gray-200' : 'border-gray-100 opacity-75'
    } ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : ''}`}>

      {/* Header with Category and Priority */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {showSelection && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onSelect?.(instruction.id, e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
          )}

          <div
            className="flex items-center space-x-2 px-2 py-1 rounded-full"
            style={{ backgroundColor: `${category.color}20`, border: `1px solid ${category.color}40` }}
          >
            <span className="text-lg">{category.icon}</span>
            <span className="text-sm font-medium" style={{ color: category.color }}>
              {category.label}
            </span>
          </div>
        </div>

        <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(instruction.priority)}`}>
          Priority {instruction.priority} ({PRIORITY_LABELS[instruction.priority as keyof typeof PRIORITY_LABELS]})
        </div>
      </div>

      {/* Instruction Text */}
      <div className="mb-3">
        <p className={`text-gray-800 ${!instruction.enabled ? 'line-through text-gray-500' : ''}`}>
          {instruction.instruction_text}
        </p>
      </div>

      {/* Context Hints */}
      {instruction.context_hints && instruction.context_hints.length > 0 && (
        <div className="mb-3">
          <div className="flex flex-wrap gap-1">
            {instruction.context_hints.map((hint, index) => (
              <span
                key={index}
                className="inline-block px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded-full"
              >
                {hint}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Usage Stats and Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <span>Used {instruction.usage_count} times</span>
          {instruction.last_used_at && (
            <span>
              Last used {formatDistanceToNow(new Date(instruction.last_used_at), { addSuffix: true })}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleToggle}
            disabled={isLoading}
            className={`px-3 py-1 text-sm font-medium rounded-full transition-colors ${
              instruction.enabled
                ? 'bg-green-100 text-green-800 hover:bg-green-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isLoading ? '...' : (instruction.enabled ? 'Enabled' : 'Disabled')}
          </button>

          <button
            onClick={() => onEdit(instruction.id)}
            disabled={isLoading}
            className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 rounded-full hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Edit
          </button>

          <button
            onClick={handleDelete}
            disabled={isLoading}
            className="px-3 py-1 text-sm font-medium text-red-600 bg-red-50 rounded-full hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default InstructionCard;