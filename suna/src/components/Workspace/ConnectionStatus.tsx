'use client';

import React from 'react';
import {
  Wifi,
  WifiOff,
  AlertTriangle,
  Activity,
  Clock,
  RotateCcw,
  Monitor,
  Zap,
  Router
} from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';

export const ConnectionStatus: React.FC<{ className?: string }> = ({ className = '' }) => {
  const {
    session,
    metrics,
    config,
    connect,
    disconnect,
    toggleConnectionStatus
  } = useWorkspace();

  const getStatusColor = () => {
    switch (session.connectionState) {
      case 'connected':
        return 'text-green-500';
      case 'connecting':
      case 'reconnecting':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      case 'disconnected':
        return 'text-gray-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = () => {
    switch (session.connectionState) {
      case 'connected':
        return <Wifi className="w-4 h-4" />;
      case 'connecting':
      case 'reconnecting':
        return <Wifi className="w-4 h-4 animate-pulse" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4" />;
      case 'disconnected':
        return <WifiOff className="w-4 h-4" />;
      default:
        return <WifiOff className="w-4 h-4" />;
    }
  };

  const getStatusText = () => {
    switch (session.connectionState) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'reconnecting':
        return 'Reconnecting...';
      case 'error':
        return 'Connection Error';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Unknown';
    }
  };

  const getQualityIndicator = () => {
    if (!session.isConnected) return null;

    const quality = session.connectionQuality;
    const color = quality === 'excellent' ? 'bg-green-500' :
                  quality === 'good' ? 'bg-yellow-500' :
                  quality === 'poor' ? 'bg-orange-500' : 'bg-red-500';

    return (
      <div className="flex items-center space-x-1">
        <div className={`w-2 h-2 rounded-full ${color}`} />
        <span className="text-xs text-gray-400 capitalize">{quality}</span>
      </div>
    );
  };

  const getLatencyIndicator = () => {
    if (!session.isConnected || session.latency === 0) return null;

    const latency = session.latency;
    const color = latency < 100 ? 'text-green-500' :
                  latency < 200 ? 'text-yellow-500' :
                  latency < 500 ? 'text-orange-500' : 'text-red-500';

    return (
      <div className={`flex items-center space-x-1 ${color}`}>
        <Clock className="w-3 h-3" />
        <span className="text-xs">{latency}ms</span>
      </div>
    );
  };

  const getBandwidthIndicator = () => {
    if (!session.isConnected || metrics.bandwidth === 0) return null;

    const bandwidth = metrics.bandwidth;
    return (
      <div className="flex items-center space-x-1 text-gray-400">
        <Router className="w-3 h-3" />
        <span className="text-xs">{Math.round(bandwidth)} kbps</span>
      </div>
    );
  };

  const getFrameRateIndicator = () => {
    if (!session.isConnected || metrics.frameRate === 0) return null;

    const fps = metrics.frameRate;
    const color = fps >= 25 ? 'text-green-500' :
                  fps >= 15 ? 'text-yellow-500' :
                  fps >= 5 ? 'text-orange-500' : 'text-red-500';

    return (
      <div className={`flex items-center space-x-1 ${color}`}>
        <Monitor className="w-3 h-3" />
        <span className="text-xs">{Math.round(fps)} fps</span>
      </div>
    );
  };

  const handleReconnect = () => {
    disconnect();
    setTimeout(() => {
      connect().catch(console.error);
    }, 1000);
  };

  if (!session.isWorkspaceOpen) {
    return null;
  }

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-lg p-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
        <button
          onClick={toggleConnectionStatus}
          className="text-gray-400 hover:text-gray-200 p-1"
          title="Toggle connection details"
        >
          <Activity className="w-4 h-4" />
        </button>
      </div>

      {/* Connection Details */}
      <div className="space-y-2">
        {/* Server Info */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Server:</span>
          <span className="text-gray-200">{config.host}:{config.port}</span>
        </div>

        {/* Status Indicators */}
        {session.isConnected && (
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Quality:</span>
              {getQualityIndicator()}
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Latency:</span>
              {getLatencyIndicator()}
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Bandwidth:</span>
              {getBandwidthIndicator()}
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Frame Rate:</span>
              {getFrameRateIndicator()}
            </div>
          </div>
        )}

        {/* Control Status */}
        {session.isConnected && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Control:</span>
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                session.hasControl ? 'bg-green-500' :
                session.controlOwner === 'agent' ? 'bg-yellow-500' : 'bg-gray-500'
              }`} />
              <span className="text-gray-200">
                {session.hasControl ? 'Your Control' :
                 session.controlOwner === 'agent' ? 'Agent Control' : 'No Control'}
              </span>
            </div>
          </div>
        )}

        {/* Last Activity */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Last Activity:</span>
          <span className="text-gray-200">
            {session.lastActivity.toLocaleTimeString()}
          </span>
        </div>

        {/* Connection Actions */}
        {session.connectionState === 'error' && (
          <div className="mt-3 pt-3 border-t border-gray-700">
            <button
              onClick={handleReconnect}
              className="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reconnect</span>
            </button>
          </div>
        )}

        {/* Performance Warning */}
        {session.isConnected && session.connectionQuality === 'poor' && (
          <div className="mt-2 p-2 bg-orange-900/20 border border-orange-700/50 rounded">
            <div className="flex items-start space-x-2">
              <Zap className="w-3 h-3 text-orange-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-orange-400 font-medium">
                  Poor Connection Quality
                </p>
                <p className="text-xs text-orange-300 mt-1">
                  Consider adjusting quality settings or checking your network connection.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {session.connectionState === 'error' && (
          <div className="mt-2 p-2 bg-red-900/20 border border-red-700/50 rounded">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="w-3 h-3 text-red-500 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-red-400 font-medium">
                  Connection Failed
                </p>
                <p className="text-xs text-red-300 mt-1">
                  Unable to connect to the VNC server. Please check your network connection and try again.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Connection Progress */}
        {(session.connectionState === 'connecting' || session.connectionState === 'reconnecting') && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-400">Connecting...</span>
              <span className="text-gray-200">VNC Server</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div className="bg-blue-500 h-1.5 rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};