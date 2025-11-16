import React, { useState, useRef, useEffect } from 'react';
import { Bot, MessageSquare, AlertTriangle } from 'lucide-react';

const ToggleSwitch = ({
  isAgentMode,
  onToggle,
  size = 'md',
  disabled = false,
  showLabel = true
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const tooltipTimeoutRef = useRef(null);

  // Handle mode toggle with animation
  const handleToggle = () => {
    if (disabled || isAnimating) return;

    setIsAnimating(true);
    onToggle();

    // Reset animation after transition
    setTimeout(() => setIsAnimating(false), 300);
  };

  // Tooltip interaction handlers
  const handleMouseEnter = () => {
    if (tooltipTimeoutRef.current) {
      clearTimeout(tooltipTimeoutRef.current);
    }
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    tooltipTimeoutRef.current = setTimeout(() => {
      setShowTooltip(false);
    }, 100);
  };

  // Size configurations
  const sizeClasses = {
    sm: {
      container: 'w-12 h-6',
      thumb: 'w-4 h-4',
      label: 'text-xs'
    },
    md: {
      container: 'w-14 h-7',
      thumb: 'w-5 h-5',
      label: 'text-sm'
    },
    lg: {
      container: 'w-16 h-8',
      thumb: 'w-6 h-6',
      label: 'text-base'
    }
  };

  const currentSize = sizeClasses[size] || sizeClasses.md;

  return (
    <div className="relative flex items-center gap-3">
      {/* Mode Icon and Label */}
      <div className={`flex items-center gap-2 ${currentSize.label} ${isAgentMode ? 'text-orange-400' : 'text-blue-400'} transition-colors duration-300`}>
        {isAgentMode ? (
          <Bot size={size === 'sm' ? 16 : size === 'lg' ? 24 : 20} />
        ) : (
          <MessageSquare size={size === 'sm' ? 16 : size === 'lg' ? 24 : 20} />
        )}
        {showLabel && (
          <span className="font-medium">
            {isAgentMode ? 'Agent Mode' : 'Chat Mode'}
          </span>
        )}
      </div>

      {/* Toggle Container */}
      <div
        className="relative"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Toggle Switch */}
        <button
          onClick={handleToggle}
          disabled={disabled}
          className={`
            ${currentSize.container}
            relative rounded-full transition-all duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            ${isAgentMode
              ? 'bg-orange-500 focus:ring-orange-400'
              : 'bg-blue-500 focus:ring-blue-400'
            }
            ${isAnimating ? 'scale-95' : 'scale-100'}
          `}
          aria-label={`Switch to ${isAgentMode ? 'Chat Mode' : 'Agent Mode'}`}
          aria-checked={isAgentMode}
          role="switch"
        >
          {/* Toggle Thumb */}
          <div
            className={`
              ${currentSize.thumb}
              absolute top-0.5 rounded-full bg-white shadow-md transform transition-all duration-300 ease-in-out
              ${isAgentMode ? 'translate-x-full' : 'translate-x-0.5'}
              ${isAnimating ? 'scale-90' : 'scale-100'}
            `}
          />
        </button>

        {/* Tooltip */}
        {showTooltip && (
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
            <div className="bg-gray-800 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg border border-gray-700">
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className="text-yellow-400" />
                <span>
                  Agent Mode enables autonomous task execution.
                  <br />
                  Review approval gates before executing.
                </span>
              </div>
              {/* Tooltip Arrow */}
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                <div className="w-2 h-2 bg-gray-800 border-r border-b border-gray-700 transform rotate-45"></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ToggleSwitch;