'use client';

import React from 'react';
import { VNCWorkspace } from '../../components/VNCWorkspace';

export default function WorkspacePage() {
  // VNC server URL from environment or default
  const vncUrl = process.env.NEXT_PUBLIC_VNC_URL || 'http://localhost:6080';
  const vncPassword = process.env.NEXT_PUBLIC_VNC_PASSWORD;

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="container mx-auto p-4">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-white mb-2">Remote Workspace</h1>
          <p className="text-gray-400">
            Access your remote desktop environment with mouse, keyboard, and touch input support.
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg overflow-hidden shadow-2xl">
          <VNCWorkspace
            vncUrl={vncUrl}
            password={vncPassword}
            width={1920}
            height={1080}
            className="w-full"
            onConnectionChange={(connected) => {
              console.log('VNC connection status:', connected);
            }}
            onError={(error) => {
              console.error('VNC connection error:', error);
            }}
          />
        </div>

        <div className="mt-4 bg-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-2">Usage Instructions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm text-gray-300">
            <div>
              <h3 className="font-medium text-white mb-1">Mouse Input</h3>
              <ul className="space-y-1">
                <li>• Click and drag to interact</li>
                <li>• Scroll with mouse wheel</li>
                <li>• Right-click for context menu</li>
                <li>• Double-click for rapid actions</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Keyboard Input</h3>
              <ul className="space-y-1">
                <li>• Type normally for text input</li>
                <li>• Use Ctrl+C/V for copy/paste</li>
                <li>• Function keys work as expected</li>
                <li>• International layouts supported</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Touch Input</h3>
              <ul className="space-y-1">
                <li>• Tap to click</li>
                <li>• Double-tap for double-click</li>
                <li>• Long-press for right-click</li>
                <li>• Two-finger pinch to zoom</li>
                <li>• Two-finger scroll</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-4 bg-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-2">Performance</h2>
          <p className="text-sm text-gray-300 mb-2">
            Target latency: &lt;500ms round-trip time for optimal responsiveness.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-green-900/50 text-green-300 rounded-full text-xs">
              WebSocket Connected
            </span>
            <span className="px-3 py-1 bg-blue-900/50 text-blue-300 rounded-full text-xs">
              Sub-500ms Latency
            </span>
            <span className="px-3 py-1 bg-purple-900/50 text-purple-300 rounded-full text-xs">
              Mobile Optimized
            </span>
            <span className="px-3 py-1 bg-yellow-900/50 text-yellow-300 rounded-full text-xs">
              Input Prediction
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}