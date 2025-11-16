/**
 * StandingInstructionsManager Component
 *
 * Main component for managing standing instructions
 */

import React, { useState, useEffect } from 'react';
import {
  StandingInstruction,
  InstructionCreateRequest,
  InstructionUpdateRequest,
  InstructionCategory,
  InstructionAnalytics
} from './types';
import {
  INSTRUCTION_CATEGORIES,
  SORT_OPTIONS,
  API_ENDPOINTS
} from './constants';
import InstructionCard from './InstructionCard';
import InstructionForm from './InstructionForm';

const StandingInstructionsManager: React.FC = () => {
  const [instructions, setInstructions] = useState<StandingInstruction[]>([]);
  const [analytics, setAnalytics] = useState<InstructionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI State
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<InstructionCategory | ''>('');
  const [sortBy, setSortBy] = useState('priority');
  const [showDisabled, setShowDisabled] = useState(false);
  const [selectedInstructions, setSelectedInstructions] = useState<string[]>([]);
  const [showSelection, setShowSelection] = useState(false);

  // Modal states
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  // Fetch instructions from API
  const fetchInstructions = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        enabled_only: (!showDisabled).toString(),
        sort_by: sortBy,
        ...(selectedCategory && { category: selectedCategory })
      });

      const response = await fetch(`${API_ENDPOINTS.INSTRUCTIONS}?${params}`);

      if (!response.ok) {
        throw new Error('Failed to fetch instructions');
      }

      const data = await response.json();
      setInstructions(data);
    } catch (err) {
      console.error('Error fetching instructions:', err);
      setError('Failed to load instructions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch analytics
  const fetchAnalytics = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.ANALYTICS);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
    }
  };

  // Create instruction
  const handleCreateInstruction = async (data: InstructionCreateRequest) => {
    try {
      const response = await fetch(API_ENDPOINTS.INSTRUCTIONS, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create instruction');
      }

      await fetchInstructions();
      setIsAdding(false);
    } catch (err) {
      console.error('Error creating instruction:', err);
      throw err;
    }
  };

  // Update instruction
  const handleUpdateInstruction = async (data: InstructionUpdateRequest) => {
    if (!editingId) return;

    try {
      const response = await fetch(`${API_ENDPOINTS.INSTRUCTIONS}/${editingId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update instruction');
      }

      await fetchInstructions();
      setEditingId(null);
    } catch (err) {
      console.error('Error updating instruction:', err);
      throw err;
    }
  };

  // Toggle instruction enabled status
  const handleToggleInstruction = async (id: string) => {
    try {
      const instruction = instructions.find(i => i.id === id);
      if (!instruction) return;

      const response = await fetch(`${API_ENDPOINTS.INSTRUCTIONS}/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled: !instruction.enabled }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle instruction');
      }

      await fetchInstructions();
    } catch (err) {
      console.error('Error toggling instruction:', err);
      setError('Failed to update instruction status');
    }
  };

  // Delete instruction
  const handleDeleteInstruction = async (id: string) => {
    try {
      const response = await fetch(`${API_ENDPOINTS.INSTRUCTIONS}/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete instruction');
      }

      await fetchInstructions();
    } catch (err) {
      console.error('Error deleting instruction:', err);
      setError('Failed to delete instruction');
    }
  };

  // Bulk operations
  const handleBulkToggle = async (enabled: boolean) => {
    if (selectedInstructions.length === 0) return;

    try {
      setBulkActionLoading(true);
      const response = await fetch(API_ENDPOINTS.BULK_STATUS, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          instruction_ids: selectedInstructions,
          enabled
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update instructions');
      }

      await fetchInstructions();
      setSelectedInstructions([]);
      setShowSelection(false);
    } catch (err) {
      console.error('Error in bulk operation:', err);
      setError('Failed to update instructions');
    } finally {
      setBulkActionLoading(false);
    }
  };

  // Test instruction injection
  const handleTestInjection = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.TEST_INJECTION);
      if (response.ok) {
        const data = await response.json();
        setTestResult(data);
      }
    } catch (err) {
      console.error('Error testing injection:', err);
      setError('Failed to test instruction injection');
    }
  };

  // Effects
  useEffect(() => {
    fetchInstructions();
    fetchAnalytics();
  }, [selectedCategory, sortBy, showDisabled]);

  // Handle selection
  const handleSelectInstruction = (id: string, selected: boolean) => {
    if (selected) {
      setSelectedInstructions(prev => [...prev, id]);
    } else {
      setSelectedInstructions(prev => prev.filter(i => i !== id));
    }
  };

  const handleSelectAll = () => {
    if (selectedInstructions.length === instructions.length) {
      setSelectedInstructions([]);
    } else {
      setSelectedInstructions(instructions.map(i => i.id));
    }
  };

  // Get category info
  const getCategoryInfo = (category: InstructionCategory) => {
    return INSTRUCTION_CATEGORIES.find(c => c.value === category) || INSTRUCTION_CATEGORIES[4];
  };

  // Get instruction for editing
  const getEditingInstruction = () => {
    return editingId ? instructions.find(i => i.id === editingId) : null;
  };

  if (loading && instructions.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading instructions...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Standing Instructions</h1>
        <p className="text-gray-600">
          Permanent directives that guide Manus behavior in all conversations
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Controls Bar */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setIsAdding(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Add Instruction
            </button>

            <button
              onClick={() => setShowAnalytics(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              📊 Analytics
            </button>

            <button
              onClick={handleTestInjection}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              🧪 Test Injection
            </button>
          </div>

          <div className="flex items-center gap-3">
            {showSelection && selectedInstructions.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  {selectedInstructions.length} selected
                </span>
                <button
                  onClick={() => handleBulkToggle(false)}
                  disabled={bulkActionLoading}
                  className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                >
                  Disable
                </button>
                <button
                  onClick={() => handleBulkToggle(true)}
                  disabled={bulkActionLoading}
                  className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50"
                >
                  Enable
                </button>
              </div>
            )}

            <button
              onClick={() => setShowSelection(!showSelection)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                showSelection
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {showSelection ? 'Done' : 'Select'}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Category:</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as InstructionCategory | '')}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Categories</option>
              {INSTRUCTION_CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>
                  {cat.icon} {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm"
            >
              {SORT_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="showDisabled"
              checked={showDisabled}
              onChange={(e) => setShowDisabled(e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="showDisabled" className="text-sm text-gray-700">
              Show disabled
            </label>
          </div>

          {showSelection && instructions.length > 0 && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedInstructions.length === instructions.length}
                onChange={handleSelectAll}
                className="rounded border-gray-300"
              />
              <label className="text-sm text-gray-700">Select all</label>
            </div>
          )}
        </div>
      </div>

      {/* Instructions List */}
      {instructions.length === 0 ? (
        <div className="bg-white rounded-lg border p-8 text-center">
          <div className="text-gray-500 mb-4">
            <div className="text-4xl mb-2">📝</div>
            <p>No instructions found</p>
          </div>
          <button
            onClick={() => setIsAdding(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Create your first instruction
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {instructions.map((instruction) => (
            <InstructionCard
              key={instruction.id}
              instruction={instruction}
              category={getCategoryInfo(instruction.category)}
              onEdit={setEditingId}
              onToggle={handleToggleInstruction}
              onDelete={handleDeleteInstruction}
              isSelected={selectedInstructions.includes(instruction.id)}
              onSelect={handleSelectInstruction}
              showSelection={showSelection}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {(isAdding || editingId) && (
        <InstructionForm
          instruction={getEditingInstruction()}
          onSubmit={editingId ? handleUpdateInstruction : handleCreateInstruction}
          onCancel={() => {
            setIsAdding(false);
            setEditingId(null);
          }}
        />
      )}

      {/* Analytics Modal */}
      {showAnalytics && analytics && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-2xl font-bold mb-6">Instruction Analytics</h2>

            <div className="grid md:grid-cols-3 gap-6 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{analytics.overall_stats.total_instructions}</div>
                <div className="text-sm text-blue-800">Total Instructions</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{analytics.overall_stats.total_usage}</div>
                <div className="text-sm text-green-800">Total Usage</div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{analytics.overall_stats.avg_usage.toFixed(1)}</div>
                <div className="text-sm text-purple-800">Average Usage</div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold mb-3">Category Breakdown</h3>
                <div className="space-y-2">
                  {analytics.category_breakdown.map((cat, index) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">{cat.category}</div>
                        <div className="text-sm text-gray-600">{cat.count} instructions</div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">{cat.total_usage} uses</div>
                        <div className="text-sm text-gray-600">Avg priority: {cat.avg_priority.toFixed(1)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-3">Top Instructions</h3>
                <div className="space-y-2">
                  {analytics.top_instructions.map((instruction, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="font-medium text-sm truncate">{instruction.instruction_text}</div>
                      <div className="text-sm text-gray-600">
                        {instruction.category} • Used {instruction.usage_count} times • Priority {instruction.priority}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end mt-6 pt-4 border-t">
              <button
                onClick={() => setShowAnalytics(false)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Result Modal */}
      {testResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-2xl font-bold mb-4">Injection Test Results</h2>

            <div className="bg-green-50 p-4 rounded-lg mb-4">
              <div className="text-green-800">
                <div className="font-semibold">✅ {testResult.message}</div>
                <div className="mt-2 text-sm">
                  <div>Instructions injected: {testResult.injection.instructions_count}</div>
                  <div>Memories injected: {testResult.injection.memories_count}</div>
                  <div>Injection time: {testResult.injection.injection_time_ms}ms</div>
                </div>
              </div>
            </div>

            <div className="mb-4">
              <h3 className="font-semibold mb-2">Injected Instructions:</h3>
              <div className="space-y-2">
                {testResult.injection.instructions.map((instruction: any, index: number) => (
                  <div key={index} className="p-3 bg-gray-50 rounded-lg">
                    <div className="font-medium">{instruction.instruction_text}</div>
                    <div className="text-sm text-gray-600">
                      {instruction.category} • Priority {instruction.priority} • Used {instruction.usage_count} times
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setTestResult(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StandingInstructionsManager;