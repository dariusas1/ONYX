/**
 * InstructionForm Component
 *
 * Form for creating and editing standing instructions
 */

import React, { useState, useEffect } from 'react';
import { InstructionCreateRequest, InstructionUpdateRequest, InstructionCategory } from './types';
import { INSTRUCTION_CATEGORIES, PRIORITY_LABELS, INSTRUCTION_TEXT_LIMIT, CONTEXT_HINTS_LIMIT } from './constants';

interface InstructionFormProps {
  instruction?: any; // For editing existing instruction
  onSubmit: (data: InstructionCreateRequest | InstructionUpdateRequest) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

const InstructionForm: React.FC<InstructionFormProps> = ({
  instruction,
  onSubmit,
  onCancel,
  isLoading = false
}) => {
  const [formData, setFormData] = useState({
    instruction_text: '',
    category: 'general' as InstructionCategory,
    priority: 5,
    context_hints: [''],
    enabled: true
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [contextHintInput, setContextHintInput] = useState('');

  useEffect(() => {
    if (instruction) {
      setFormData({
        instruction_text: instruction.instruction_text || '',
        category: instruction.category || 'general',
        priority: instruction.priority || 5,
        context_hints: instruction.context_hints?.length ? [...instruction.context_hints, ''] : [''],
        enabled: instruction.enabled ?? true
      });
    }
  }, [instruction]);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleContextHintChange = (index: number, value: string) => {
    const newHints = [...formData.context_hints];
    newHints[index] = value;
    setFormData(prev => ({ ...prev, context_hints: newHints }));
  };

  const addContextHint = () => {
    if (formData.context_hints.length < CONTEXT_HINTS_LIMIT) {
      setFormData(prev => ({
        ...prev,
        context_hints: [...prev.context_hints, '']
      }));
    }
  };

  const removeContextHint = (index: number) => {
    const newHints = formData.context_hints.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, context_hints: newHints }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.instruction_text.trim()) {
      newErrors.instruction_text = 'Instruction text is required';
    } else if (formData.instruction_text.length > INSTRUCTION_TEXT_LIMIT) {
      newErrors.instruction_text = `Instruction text cannot exceed ${INSTRUCTION_TEXT_LIMIT} characters`;
    }

    if (formData.priority < 1 || formData.priority > 10) {
      newErrors.priority = 'Priority must be between 1 and 10';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      // Filter out empty context hints
      const filteredContextHints = formData.context_hints.filter(hint => hint.trim());

      const submitData = {
        instruction_text: formData.instruction_text.trim(),
        category: formData.category,
        priority: formData.priority,
        context_hints: filteredContextHints.length > 0 ? filteredContextHints : undefined,
        enabled: formData.enabled
      };

      await onSubmit(submitData);
    } catch (error) {
      console.error('Error submitting instruction:', error);
      setErrors({ submit: 'Failed to save instruction. Please try again.' });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {instruction ? 'Edit Instruction' : 'Create New Instruction'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Instruction Text */}
            <div>
              <label htmlFor="instruction_text" className="block text-sm font-medium text-gray-700 mb-2">
                Instruction Text <span className="text-red-500">*</span>
              </label>
              <textarea
                id="instruction_text"
                value={formData.instruction_text}
                onChange={(e) => handleInputChange('instruction_text', e.target.value)}
                maxLength={INSTRUCTION_TEXT_LIMIT}
                rows={4}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none ${
                  errors.instruction_text ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="Enter your standing instruction..."
                disabled={isLoading}
              />
              <div className="flex justify-between mt-1">
                {errors.instruction_text && (
                  <p className="text-sm text-red-600">{errors.instruction_text}</p>
                )}
                <span className="text-sm text-gray-500">
                  {formData.instruction_text.length}/{INSTRUCTION_TEXT_LIMIT}
                </span>
              </div>
            </div>

            {/* Category */}
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                Category <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {INSTRUCTION_CATEGORIES.map((cat) => (
                  <label
                    key={cat.value}
                    className={`flex flex-col items-center p-3 border-2 rounded-lg cursor-pointer transition-colors ${
                      formData.category === cat.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="category"
                      value={cat.value}
                      checked={formData.category === cat.value}
                      onChange={(e) => handleInputChange('category', e.target.value)}
                      disabled={isLoading}
                      className="sr-only"
                    />
                    <span className="text-2xl mb-1">{cat.icon}</span>
                    <span className="text-sm font-medium text-center">{cat.label}</span>
                    <span className="text-xs text-gray-500 text-center mt-1">{cat.description}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Priority */}
            <div>
              <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-2">
                Priority Level ({formData.priority}: {PRIORITY_LABELS[formData.priority as keyof typeof PRIORITY_LABELS]})
              </label>
              <input
                type="range"
                id="priority"
                min="1"
                max="10"
                value={formData.priority}
                onChange={(e) => handleInputChange('priority', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                disabled={isLoading}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1 (Very Low)</span>
                <span>10 (Critical)</span>
              </div>
              {errors.priority && (
                <p className="text-sm text-red-600 mt-1">{errors.priority}</p>
              )}
            </div>

            {/* Context Hints */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Context Hints (Optional)
              </label>
              <div className="space-y-2">
                {formData.context_hints.map((hint, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={hint}
                      onChange={(e) => handleContextHintChange(index, e.target.value)}
                      placeholder="Enter context hint (e.g., 'meetings', 'coding', 'urgent')"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      disabled={isLoading}
                    />
                    {formData.context_hints.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeContextHint(index)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        disabled={isLoading}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}

                {formData.context_hints.length < CONTEXT_HINTS_LIMIT && (
                  <button
                    type="button"
                    onClick={addContextHint}
                    className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
                    disabled={isLoading}
                  >
                    + Add Context Hint
                  </button>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Context hints help determine when to apply this instruction. Max {CONTEXT_HINTS_LIMIT} hints.
              </p>
            </div>

            {/* Enabled Toggle */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) => handleInputChange('enabled', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                disabled={isLoading}
              />
              <label htmlFor="enabled" className="ml-2 text-sm text-gray-700">
                Enable this instruction
              </label>
            </div>

            {/* Error Message */}
            {errors.submit && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{errors.submit}</p>
              </div>
            )}

            {/* Form Actions */}
            <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : (instruction ? 'Update Instruction' : 'Create Instruction')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default InstructionForm;