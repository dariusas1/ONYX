'use client';

import React from 'react';
import { Menu } from 'lucide-react';
import { useMode } from '../contexts/ModeContext';
import ToggleSwitch from './ToggleSwitch/ToggleSwitch';

export interface HeaderProps {
  className?: string;
}

export function Header({ className = '' }: HeaderProps) {
  const { isAgentMode, toggleMode } = useMode();
  return (
    <header
      className={`flex items-center justify-between px-4 py-3 border-b border-manus-border bg-manus-surface ${className}`}
      role="banner"
    >
      {/* Logo/Branding */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-manus-accent">
          <span className="text-white font-bold text-lg">O</span>
        </div>
        <h1 className="text-xl font-semibold text-manus-text">
          ONYX
        </h1>
      </div>

      {/* Navigation/Actions */}
      <div className="flex items-center gap-3">
        {/* Agent Mode Toggle */}
        <div className="flex items-center">
          <ToggleSwitch
            isAgentMode={isAgentMode}
            onToggle={toggleMode}
            size="sm"
            showLabel={false}
          />
        </div>

        {/* User menu */}
        <button
          type="button"
          className="p-2 rounded-lg hover:bg-manus-bg transition-colors duration-200"
          aria-label="Open menu"
          title="Menu"
        >
          <Menu className="w-5 h-5 text-manus-text" />
        </button>
      </div>
    </header>
  );
}
