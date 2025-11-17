'use client';

import React, { useState, useEffect } from 'react';
import {
  Hand,
  Play,
  Pause,
  User,
  Bot,
  AlertCircle,
  CheckCircle,
  Clock,
  MessageSquare,
  ArrowRight,
  ArrowLeft
} from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';

export const ControlOverlay: React.FC<{ className?: string }> = ({ className = '' }) => {
  const {
    session,
    hasControl,
    controlOwner,
    takeControl,
    releaseControl,
    pendingControlRequest
  } = useWorkspace();

  const [reason, setReason] = useState('');
  const [showReasonDialog, setShowReasonDialog] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Countdown for automatic control return
  useEffect(() => {
    if (hasControl && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (hasControl && countdown === 0) {
      // Auto-release control after countdown
      releaseControl();
    }
  }, [hasControl, countdown, releaseControl]);

  const handleTakeControl = () => {
    if (controlOwner === 'founder' && hasControl) {
      // Already have control
      return;
    }

    if (controlOwner === 'agent') {
      // Show reason dialog for taking control from agent
      setShowReasonDialog(true);
    } else {
      // Take control directly
      takeControl().catch(console.error);
    }
  };

  const handleTakeControlWithReason = () => {
    takeControl(reason).catch(console.error);
    setShowReasonDialog(false);
    setReason('');
  };

  const handleReleaseControl = () => {
    releaseControl();
    setCountdown(0);
  };

  const handleAutoRelease = (seconds: number) => {
    setCountdown(seconds);
  };

  const getControlIcon = () => {
    if (hasControl) {
      return <User className="w-4 h-4" />;
    } else if (controlOwner === 'agent') {
      return <Bot className="w-4 h-4" />;
    } else {
      return <Hand className="w-4 h-4" />;
    }
  };

  const getControlText = () => {
    if (hasControl) {
      return 'You have control';
    } else if (controlOwner === 'agent') {
      return 'Agent has control';
    } else {
      return 'No one has control';
    }
  };

  const getControlColor = () => {
    if (hasControl) {
      return 'bg-green-600 hover:bg-green-700';
    } else if (controlOwner === 'agent') {
      return 'bg-yellow-600 hover:bg-yellow-700';
    } else {
      return 'bg-gray-600 hover:bg-gray-700';
    }
  };

  const getActionButton = () => {
    if (pendingControlRequest) {
      return (
        <div className="flex items-center space-x-2 px-3 py-2 bg-blue-600 rounded-lg animate-pulse">
          <Clock className="w-4 h-4" />
          <span className="text-sm">Requesting control...</span>
        </div>
      );
    }

    if (hasControl) {
      return (
        <div className="flex items-center space-x-2">
          <button
            onClick={handleReleaseControl}
            className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Release Control</span>
          </button>

          {/* Auto-release options */}
          <div className="flex items-center space-x-1">
            <span className="text-xs text-gray-400">Auto-release:</span>
            <button
              onClick={() => handleAutoRelease(30)}
              className={`px-2 py-1 text-xs rounded ${
                countdown === 30 ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              30s
            </button>
            <button
              onClick={() => handleAutoRelease(60)}
              className={`px-2 py-1 text-xs rounded ${
                countdown === 60 ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              1m
            </button>
            <button
              onClick={() => handleAutoRelease(300)}
              className={`px-2 py-1 text-xs rounded ${
                countdown === 300 ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              5m
            </button>
          </div>

          {countdown > 0 && (
            <div className="flex items-center space-x-1 px-2 py-1 bg-orange-600 rounded">
              <Clock className="w-3 h-3" />
              <span className="text-xs">{countdown}s</span>
            </div>
          )}
        </div>
      );
    } else {
      return (
        <button
          onClick={handleTakeControl}
          disabled={pendingControlRequest !== null}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ArrowRight className="w-4 h-4" />
          <span className="text-sm">Take Control</span>
        </button>
      );
    }
  };

  if (!session.isWorkspaceOpen) {
    return null;
  }

  return (
    <>
      <div className={`bg-gray-800 border border-gray-700 rounded-lg p-4 ${className}`}>
        {/* Control Status */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${getControlColor()}`}>
              {getControlIcon()}
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-200">
                {getControlText()}
              </h3>
              <p className="text-xs text-gray-400">
                {session.isConnected ? 'Workspace connected' : 'Workspace disconnected'}
              </p>
            </div>
          </div>

          {session.isConnected && (
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
              hasControl ? 'bg-green-100 text-green-800' :
              controlOwner === 'agent' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {hasControl ? 'Active' : controlOwner === 'agent' ? 'Agent Active' : 'Inactive'}
            </div>
          )}
        </div>

        {/* Control Actions */}
        <div className="space-y-3">
          {/* Main Action Button */}
          <div className="flex items-center justify-center">
            {getActionButton()}
          </div>

          {/* Status Messages */}
          {hasControl && (
            <div className="flex items-start space-x-2 p-3 bg-green-900/20 border border-green-700/50 rounded">
              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-green-400 font-medium">
                  You have workspace control
                </p>
                <p className="text-xs text-green-300 mt-1">
                  You can now interact with the workspace using your mouse and keyboard.
                  Remember to release control when you're done.
                </p>
              </div>
            </div>
          )}

          {controlOwner === 'agent' && !hasControl && (
            <div className="flex items-start space-x-2 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded">
              <AlertCircle className="w-4 h-4 text-yellow-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-yellow-400 font-medium">
                  Agent is currently working
                </p>
                <p className="text-xs text-yellow-300 mt-1">
                  The agent has control of the workspace. Click "Take Control" to interrupt and take manual control.
                  The agent will be paused while you have control.
                </p>
              </div>
            </div>
          )}

          {!hasControl && controlOwner !== 'agent' && session.isConnected && (
            <div className="flex items-start space-x-2 p-3 bg-gray-700/50 border border-gray-600 rounded">
              <Hand className="w-4 h-4 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-gray-300 font-medium">
                  No active control
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Click "Take Control" to start interacting with the workspace.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        {session.isConnected && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Quick Actions:</span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => takeControl('Quick task intervention').catch(console.error)}
                  disabled={!hasControl && controlOwner === 'agent'}
                  className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Quick Control
                </button>
                <button
                  onClick={() => takeControl('Review and fix issue').catch(console.error)}
                  disabled={!hasControl && controlOwner === 'agent'}
                  className="px-2 py-1 text-xs bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Fix Issue
                </button>
                <button
                  onClick={() => takeControl('Manual intervention required').catch(console.error)}
                  disabled={!hasControl && controlOwner === 'agent'}
                  className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Emergency
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Reason Dialog */}
      {showReasonDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <MessageSquare className="w-5 h-5 text-blue-500" />
              <h3 className="text-lg font-medium text-gray-200">
                Reason for Taking Control
              </h3>
            </div>

            <p className="text-sm text-gray-400 mb-4">
              The agent is currently working. Please provide a reason for taking control.
            </p>

            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter your reason..."
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
            />

            <div className="flex items-center justify-between mt-4">
              <button
                onClick={() => setShowReasonDialog(false)}
                className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleTakeControlWithReason}
                  disabled={!reason.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Take Control
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};