'use client';

import React, { useState } from 'react';
import {
  Settings,
  Monitor,
  Zap,
  Image,
  Sliders,
  Save,
  RotateCcw,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';

export const QualityControls: React.FC<{ className?: string }> = ({ className = '' }) => {
  const {
    session,
    qualitySettings,
    updateQualitySettings,
    showQualityControls,
    toggleQualityControls
  } = useWorkspace();

  const [localSettings, setLocalSettings] = useState(qualitySettings);
  const [isExpanded, setIsExpanded] = useState(false);

  const presets = [
    {
      name: 'High Quality',
      description: 'Best visual quality, higher bandwidth',
      settings: { quality: 0, compression: 0, scaleLevel: 1.0 },
      icon: <Image className="w-4 h-4" />,
      color: 'bg-green-600'
    },
    {
      name: 'Balanced',
      description: 'Good balance of quality and performance',
      settings: { quality: 6, compression: 2, scaleLevel: 1.0 },
      icon: <Sliders className="w-4 h-4" />,
      color: 'bg-blue-600'
    },
    {
      name: 'High Performance',
      description: 'Fastest response, lower quality',
      settings: { quality: 9, compression: 9, scaleLevel: 0.8 },
      icon: <Zap className="w-4 h-4" />,
      color: 'bg-orange-600'
    },
    {
      name: 'Mobile',
      description: 'Optimized for mobile devices',
      settings: { quality: 7, compression: 5, scaleLevel: 0.7 },
      icon: <Monitor className="w-4 h-4" />,
      color: 'bg-purple-600'
    }
  ];

  const handlePresetSelect = (preset: typeof presets[0]) => {
    setLocalSettings({ ...localSettings, ...preset.settings });
  };

  const handleQualityChange = (value: number) => {
    setLocalSettings({ ...localSettings, quality: value });
  };

  const handleCompressionChange = (value: number) => {
    setLocalSettings({ ...localSettings, compression: value });
  };

  const handleScaleChange = (value: number) => {
    setLocalSettings({ ...localSettings, scaleLevel: value });
  };

  const handleApplySettings = () => {
    updateQualitySettings(localSettings);
  };

  const handleResetSettings = () => {
    const defaultSettings = { quality: 6, compression: 2, scaleLevel: 1.0 };
    setLocalSettings(defaultSettings);
    updateQualitySettings(defaultSettings);
  };

  const getQualityLabel = (quality: number) => {
    if (quality <= 2) return 'Excellent';
    if (quality <= 4) return 'High';
    if (quality <= 6) return 'Medium';
    if (quality <= 8) return 'Low';
    return 'Very Low';
  };

  const getCompressionLabel = (compression: number) => {
    if (compression <= 2) return 'Low';
    if (compression <= 4) return 'Medium';
    if (compression <= 6) return 'High';
    return 'Maximum';
  };

  const getScaleLabel = (scale: number) => {
    if (scale >= 1.0) return '100%';
    if (scale >= 0.9) return '90%';
    if (scale >= 0.8) return '80%';
    if (scale >= 0.7) return '70%';
    return `${Math.round(scale * 100)}%`;
  };

  const hasChanges = JSON.stringify(localSettings) !== JSON.stringify(qualitySettings);

  if (!showQualityControls) {
    return null;
  }

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-medium text-gray-200">Quality Settings</h3>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-400 hover:text-gray-200 p-1"
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Presets */}
        <div>
          <h4 className="text-sm font-medium text-gray-300 mb-3">Quick Presets</h4>
          <div className="grid grid-cols-2 gap-2">
            {presets.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handlePresetSelect(preset)}
                className={`p-3 rounded-lg border transition-colors ${
                  JSON.stringify(localSettings) === JSON.stringify({ ...localSettings, ...preset.settings })
                    ? 'border-blue-500 bg-blue-900/20'
                    : 'border-gray-700 bg-gray-900/50 hover:border-gray-600'
                }`}
              >
                <div className="flex items-center space-x-2 mb-1">
                  <div className={`p-1 rounded ${preset.color}`}>
                    {preset.icon}
                  </div>
                  <span className="text-sm font-medium text-gray-200">
                    {preset.name}
                  </span>
                </div>
                <p className="text-xs text-gray-400 text-left">
                  {preset.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Settings */}
        {isExpanded && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3">Advanced Settings</h4>

              {/* Quality */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-gray-400">Quality</label>
                  <span className="text-sm text-gray-200">
                    {getQualityLabel(localSettings.quality)} ({localSettings.quality}/9)
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="9"
                  value={localSettings.quality}
                  onChange={(e) => handleQualityChange(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(localSettings.quality / 9) * 100}%, #4b5563 ${(localSettings.quality / 9) * 100}%, #4b5563 100%)`
                  }}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Best</span>
                  <span>Fast</span>
                </div>
              </div>

              {/* Compression */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-gray-400">Compression</label>
                  <span className="text-sm text-gray-200">
                    {getCompressionLabel(localSettings.compression)} ({localSettings.compression}/9)
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="9"
                  value={localSettings.compression}
                  onChange={(e) => handleCompressionChange(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(localSettings.compression / 9) * 100}%, #4b5563 ${(localSettings.compression / 9) * 100}%, #4b5563 100%)`
                  }}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Low</span>
                  <span>High</span>
                </div>
              </div>

              {/* Scale */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-gray-400">Scale</label>
                  <span className="text-sm text-gray-200">
                    {getScaleLabel(localSettings.scaleLevel)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.1"
                  value={localSettings.scaleLevel}
                  onChange={(e) => handleScaleChange(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((localSettings.scaleLevel - 0.5) / 0.5) * 100}%, #4b5563 ${((localSettings.scaleLevel - 0.5) / 0.5) * 100}%, #4b5563 100%)`
                  }}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>

            {/* Info */}
            <div className="p-3 bg-blue-900/20 border border-blue-700/50 rounded">
              <div className="flex items-start space-x-2">
                <Info className="w-4 h-4 text-blue-500 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-blue-400 font-medium">
                    Quality vs Performance
                  </p>
                  <p className="text-xs text-blue-300 mt-1">
                    Lower quality values provide better visual quality but use more bandwidth.
                    Higher compression improves performance but may reduce image clarity.
                    Scale affects both quality and performance.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-700">
          <button
            onClick={handleResetSettings}
            className="flex items-center space-x-2 px-3 py-2 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            <span className="text-sm">Reset</span>
          </button>

          <div className="flex items-center space-x-2">
            {hasChanges && (
              <div className="flex items-center space-x-1 px-2 py-1 bg-yellow-600/20 border border-yellow-600/50 rounded">
                <div className="w-2 h-2 bg-yellow-500 rounded-full" />
                <span className="text-xs text-yellow-400">Unsaved changes</span>
              </div>
            )}

            <button
              onClick={handleApplySettings}
              disabled={!hasChanges}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Save className="w-4 h-4" />
              <span className="text-sm">Apply</span>
            </button>
          </div>
        </div>

        {/* Current Settings Summary */}
        <div className="p-3 bg-gray-900/50 rounded border border-gray-700">
          <h4 className="text-xs font-medium text-gray-400 mb-2">Current Settings</h4>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <div className="text-gray-500">Quality</div>
              <div className="text-gray-200 font-medium">
                {getQualityLabel(qualitySettings.quality)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Compression</div>
              <div className="text-gray-200 font-medium">
                {getCompressionLabel(qualitySettings.compression)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Scale</div>
              <div className="text-gray-200 font-medium">
                {getScaleLabel(qualitySettings.scaleLevel)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};