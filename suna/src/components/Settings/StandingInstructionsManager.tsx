/**
 * Standing Instructions Manager Component
 *
 * Comprehensive UI component for managing standing instructions with full CRUD operations,
 * categorization, priority management, and analytics dashboard.
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  StandingInstruction,
  InstructionCategory,
  CreateInstructionRequest,
  UpdateInstructionRequest,
  InstructionFilters,
  BulkOperationRequest,
  INSTRUCTION_CATEGORIES,
  InstructionAnalytics,
  InstructionConflict
} from '@/lib/types/instructions';

// UI Components
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// Icons
import { Plus, Edit, Trash2, Eye, EyeOff, BarChart3, AlertTriangle, CheckCircle, Clock, Settings, Search, Filter, MoreVertical } from 'lucide-react';

interface StandingInstructionsManagerProps {
  className?: string;
}

export const StandingInstructionsManager: React.FC<StandingInstructionsManagerProps> = ({ className }) => {
  const [instructions, setInstructions] = useState<StandingInstruction[]>([]);
  const [analytics, setAnalytics] = useState<InstructionAnalytics[]>([]);
  const [conflicts, setConflicts] = useState<InstructionConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInstructions, setSelectedInstructions] = useState<string[]>([]);

  // UI State
  const [isAddingInstruction, setIsAddingInstruction] = useState(false);
  const [editingInstruction, setEditingInstruction] = useState<StandingInstruction | null>(null);
  const [activeTab, setActiveTab] = useState('instructions');
  const [filters, setFilters] = useState<InstructionFilters>({});
  const [searchQuery, setSearchQuery] = useState('');

  // Form State
  const [formData, setFormData] = useState<CreateInstructionRequest>({
    instruction_text: '',
    priority: 5,
    category: InstructionCategory.BEHAVIOR,
    enabled: true,
    context_hints: {}
  });

  const supabase = createClient();

  // Load instructions on component mount
  useEffect(() => {
    loadInstructions();
    loadAnalytics();
    checkConflicts();
  }, []);

  const loadInstructions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error('User not authenticated');

      const response = await fetch('/api/instructions?' + new URLSearchParams({
        ...(filters.category && { category: filters.category }),
        ...(filters.enabled !== undefined && { enabled: filters.enabled.toString() }),
        ...(searchQuery && { search: searchQuery }),
        ...(filters.sort_by && { sort_by: filters.sort_by }),
        ...(filters.sort_order && { sort_order: filters.sort_order })
      }));

      if (!response.ok) {
        throw new Error('Failed to fetch instructions');
      }

      const result = await response.json();
      if (result.success) {
        setInstructions(result.data.instructions);
      } else {
        throw new Error(result.error || 'Failed to fetch instructions');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading instructions:', err);
    } finally {
      setLoading(false);
    }
  }, [filters, searchQuery, supabase]);

  const loadAnalytics = useCallback(async () => {
    try {
      const response = await fetch('/api/instructions/analytics');
      if (!response.ok) return;

      const result = await response.json();
      if (result.success) {
        setAnalytics([result.data]); // Wrap in array for compatibility
      }
    } catch (err) {
      console.error('Error loading analytics:', err);
    }
  }, []);

  const checkConflicts = useCallback(async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const response = await fetch('/api/instructions/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_context: {
            messageContent: 'test message',
            agentMode: 'chat',
            confidence: 0.8,
            involvesSensitiveData: false,
            requiresSecureHandling: false,
            isAgentMode: false,
            isTaskExecution: false
          }
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setConflicts(result.data.conflicts_detected || []);
        }
      }
    } catch (err) {
      console.error('Error checking conflicts:', err);
    }
  }, [supabase]);

  const handleCreateInstruction = async () => {
    try {
      if (!formData.instruction_text.trim()) {
        setError('Instruction text is required');
        return;
      }

      const response = await fetch('/api/instructions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const result = await response.json();
      if (result.success) {
        setIsAddingInstruction(false);
        setFormData({
          instruction_text: '',
          priority: 5,
          category: InstructionCategory.BEHAVIOR,
          enabled: true,
          context_hints: {}
        });
        loadInstructions();
        loadAnalytics();
      } else {
        setError(result.error || 'Failed to create instruction');
      }
    } catch (err) {
      setError('An error occurred while creating the instruction');
      console.error('Error creating instruction:', err);
    }
  };

  const handleUpdateInstruction = async (instructionId: string, updates: UpdateInstructionRequest) => {
    try {
      const response = await fetch(`/api/instructions/${instructionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      const result = await response.json();
      if (result.success) {
        setEditingInstruction(null);
        loadInstructions();
        loadAnalytics();
      } else {
        setError(result.error || 'Failed to update instruction');
      }
    } catch (err) {
      setError('An error occurred while updating the instruction');
      console.error('Error updating instruction:', err);
    }
  };

  const handleDeleteInstruction = async (instructionId: string) => {
    if (!confirm('Are you sure you want to delete this instruction?')) return;

    try {
      const response = await fetch(`/api/instructions/${instructionId}`, {
        method: 'DELETE'
      });

      const result = await response.json();
      if (result.success) {
        loadInstructions();
        loadAnalytics();
      } else {
        setError(result.error || 'Failed to delete instruction');
      }
    } catch (err) {
      setError('An error occurred while deleting the instruction');
      console.error('Error deleting instruction:', err);
    }
  };

  const handleBulkOperation = async (operation: 'enable' | 'disable' | 'delete') => {
    if (selectedInstructions.length === 0) return;

    const confirmMessage = {
      enable: `Enable ${selectedInstructions.length} instruction(s)?`,
      disable: `Disable ${selectedInstructions.length} instruction(s)?`,
      delete: `Delete ${selectedInstructions.length} instruction(s)? This cannot be undone.`
    }[operation];

    if (!confirm(confirmMessage)) return;

    try {
      const response = await fetch('/api/instructions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation,
          instruction_ids: selectedInstructions
        } as BulkOperationRequest)
      });

      const result = await response.json();
      if (result.success) {
        setSelectedInstructions([]);
        loadInstructions();
        loadAnalytics();
      } else {
        setError(result.error || 'Failed to perform bulk operation');
      }
    } catch (err) {
      setError('An error occurred during bulk operation');
      console.error('Error in bulk operation:', err);
    }
  };

  const getCategoryConfig = (category: InstructionCategory) => {
    return INSTRUCTION_CATEGORIES.find(cat => cat.value === category);
  };

  const formatLastUsed = (lastUsedAt?: string) => {
    if (!lastUsedAt) return 'Never used';
    const date = new Date(lastUsedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading instructions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`standing-instructions-manager ${className}`}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Standing Instructions</h2>
            <p className="text-gray-600 mt-1">
              Permanent directives that guide Manus behavior in all conversations
            </p>
          </div>
          <Button onClick={() => setIsAddingInstruction(true)} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Add Instruction
          </Button>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Conflicts Alert */}
        {conflicts.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Conflicts Detected</AlertTitle>
            <AlertDescription>
              {conflicts.length} instruction conflict(s) found. Review the Analytics tab for details.
            </AlertDescription>
          </Alert>
        )}

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="instructions">Instructions</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Instructions Tab */}
          <TabsContent value="instructions" className="space-y-4">
            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search instructions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>

              <Select value={filters.category || ''} onValueChange={(value) =>
                setFilters(prev => ({ ...prev, category: value as any || undefined }))
              }>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Categories</SelectItem>
                  {INSTRUCTION_CATEGORIES.map(cat => (
                    <SelectItem key={cat.value} value={cat.value}>
                      <div className="flex items-center gap-2">
                        <span>{cat.icon}</span>
                        <span>{cat.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={filters.enabled?.toString() || ''} onValueChange={(value) =>
                setFilters(prev => ({ ...prev, enabled: value === '' ? undefined : value === 'true' }))
              }>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All</SelectItem>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Bulk Actions */}
            {selectedInstructions.length > 0 && (
              <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                <span className="text-sm text-blue-700">
                  {selectedInstructions.length} instruction(s) selected
                </span>
                <Button size="sm" variant="outline" onClick={() => handleBulkOperation('enable')}>
                  Enable
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleBulkOperation('disable')}>
                  Disable
                </Button>
                <Button size="sm" variant="destructive" onClick={() => handleBulkOperation('delete')}>
                  Delete
                </Button>
                <Button size="sm" variant="outline" onClick={() => setSelectedInstructions([])}>
                  Clear Selection
                </Button>
              </div>
            )}

            {/* Instructions List */}
            <div className="space-y-3">
              {instructions.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <p className="text-gray-500">No instructions found</p>
                    <p className="text-sm text-gray-400 mt-2">
                      Create your first standing instruction to guide Manus behavior
                    </p>
                  </CardContent>
                </Card>
              ) : (
                instructions.map((instruction) => {
                  const categoryConfig = getCategoryConfig(instruction.category);
                  return (
                    <Card key={instruction.id} className={!instruction.enabled ? 'opacity-60' : ''}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            <Checkbox
                              checked={selectedInstructions.includes(instruction.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedInstructions(prev => [...prev, instruction.id]);
                                } else {
                                  setSelectedInstructions(prev => prev.filter(id => id !== instruction.id));
                                }
                              }}
                            />

                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-lg">{categoryConfig?.icon}</span>
                                <Badge variant="secondary" style={{ backgroundColor: categoryConfig?.color + '20', color: categoryConfig?.color }}>
                                  {categoryConfig?.label}
                                </Badge>
                                <Badge variant="outline">
                                  Priority {instruction.priority}
                                </Badge>
                                {!instruction.enabled && (
                                  <Badge variant="secondary">Inactive</Badge>
                                )}
                              </div>

                              <p className="text-gray-900 mb-2">{instruction.instruction_text}</p>

                              <div className="flex items-center gap-4 text-sm text-gray-500">
                                <div className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  <span>Used {instruction.usage_count} times</span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <Eye className="h-3 w-3" />
                                  <span>{formatLastUsed(instruction.last_used_at)}</span>
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setEditingInstruction(instruction)}
                                  >
                                    <Edit className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Edit instruction</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>

                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleDeleteInstruction(instruction.id)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Delete instruction</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Instructions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{instructions.length}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Active Instructions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {instructions.filter(i => i.enabled).length}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {instructions.reduce((sum, i) => sum + i.usage_count, 0)}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Conflicts</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">{conflicts.length}</div>
                </CardContent>
              </Card>
            </div>

            {/* Category Breakdown */}
            {analytics.length > 0 && analytics[0].categories && (
              <Card>
                <CardHeader>
                  <CardTitle>Category Breakdown</CardTitle>
                  <CardDescription>Usage statistics by instruction category</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {analytics[0].categories.map((cat: any) => {
                      const config = getCategoryConfig(cat.category);
                      return (
                        <div key={cat.category} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{config?.icon}</span>
                            <span className="font-medium">{config?.label}</span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm text-gray-500">{cat.total_count} instructions</div>
                            <div className="text-sm font-medium">{cat.total_usage} uses</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Conflicts */}
            {conflicts.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-red-600">Instruction Conflicts</CardTitle>
                  <CardDescription>Detected conflicts between instructions</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {conflicts.map((conflict, index) => (
                      <div key={index} className="p-3 border border-red-200 rounded-lg bg-red-50">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                          <span className="font-medium text-red-800 capitalize">
                            {conflict.conflict_type.replace('_', ' ')}
                          </span>
                          <Badge variant={conflict.severity === 'high' ? 'destructive' : 'secondary'}>
                            {conflict.severity}
                          </Badge>
                        </div>
                        <div className="text-sm space-y-1">
                          <p><strong>Instruction 1:</strong> {conflict.instruction_1_text}</p>
                          <p><strong>Instruction 2:</strong> {conflict.instruction_2_text}</p>
                          {conflict.resolution_suggestion && (
                            <p className="text-blue-700"><strong>Suggestion:</strong> {conflict.resolution_suggestion}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Instruction Settings</CardTitle>
                <CardDescription>Configure global instruction management settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable conflict detection</Label>
                    <p className="text-sm text-gray-500">Automatically detect conflicts between instructions</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Show usage analytics</Label>
                    <p className="text-sm text-gray-500">Display usage statistics and effectiveness metrics</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable instruction evaluation</Label>
                    <p className="text-sm text-gray-500">Automatically evaluate instructions during conversations</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Add/Edit Instruction Modal */}
      <Dialog open={isAddingInstruction || !!editingInstruction} onOpenChange={(open) => {
        if (!open) {
          setIsAddingInstruction(false);
          setEditingInstruction(null);
          setFormData({
            instruction_text: '',
            priority: 5,
            category: InstructionCategory.BEHAVIOR,
            enabled: true,
            context_hints: {}
          });
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingInstruction ? 'Edit Instruction' : 'Add New Instruction'}
            </DialogTitle>
            <DialogDescription>
              {editingInstruction
                ? 'Modify the existing standing instruction'
                : 'Create a new standing instruction to guide Manus behavior'
              }
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="instruction_text">Instruction Text</Label>
              <Textarea
                id="instruction_text"
                placeholder="Enter the instruction text (1-500 characters)..."
                value={formData.instruction_text}
                onChange={(e) => setFormData(prev => ({ ...prev, instruction_text: e.target.value }))}
                rows={3}
                maxLength={500}
              />
              <div className="text-sm text-gray-500">
                {formData.instruction_text.length}/500 characters
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, category: value as any }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INSTRUCTION_CATEGORIES.map(cat => (
                      <SelectItem key={cat.value} value={cat.value}>
                        <div className="flex items-center gap-2">
                          <span>{cat.icon}</span>
                          <div>
                            <div className="font-medium">{cat.label}</div>
                            <div className="text-sm text-gray-500">{cat.description}</div>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority: {formData.priority}</Label>
                <Slider
                  id="priority"
                  min={1}
                  max={10}
                  step={1}
                  value={[formData.priority]}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, priority: value[0] }))}
                  className="mt-2"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Low (1)</span>
                  <span>High (10)</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="enabled"
                checked={formData.enabled}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, enabled: checked }))}
              />
              <Label htmlFor="enabled">Enable this instruction</Label>
            </div>

            {getCategoryConfig(formData.category) && (
              <div className="p-3 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-2">{getCategoryConfig(formData.category)?.label}</h4>
                <p className="text-sm text-gray-600 mb-2">{getCategoryConfig(formData.category)?.description}</p>
                <div className="text-xs text-gray-500">
                  <strong>Example instructions:</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    {getCategoryConfig(formData.category)?.example_instructions.map((example, index) => (
                      <li key={index}>{example}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => {
              setIsAddingInstruction(false);
              setEditingInstruction(null);
            }}>
              Cancel
            </Button>
            <Button onClick={handleCreateInstruction}>
              {editingInstruction ? 'Update' : 'Create'} Instruction
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};