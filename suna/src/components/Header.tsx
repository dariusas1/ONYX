'use client';

import React from 'react';
import { Menu } from 'lucide-react';
import { useAgentModeContext } from '@/components/AgentModeProvider';
import ModeToggle from '@/components/ModeToggle';
import type { AgentMode } from '@/components/ModeToggle';

export interface HeaderProps {
  className?: string;
  agentMode?: AgentMode;
  onModeChange?: (mode: AgentMode) => void;
  modeDisabled?: boolean;
}

export function Header({
  className = '',
  agentMode,
  onModeChange,
  modeDisabled = false
}: HeaderProps) {
  const agentModeContext = useAgentModeContext();

  // Use context values if props not provided
  const currentMode = agentMode || agentModeContext.mode;
  const handleModeChange = onModeChange || agentModeContext.changeMode;

  return (
    <header
      className={`flex items-center justify-between px-3 sm:px-4 py-3 border-b border-manus-border bg-manus-surface ${className}`}
      role="banner"
    >
      {/* Logo/Branding */}
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-manus-accent">
          <span className="text-white font-bold text-lg sm:text-xl" aria-hidden="true">O</span>
        </div>
        <div>
          <h1 className="text-lg sm:text-xl font-semibold text-manus-text leading-tight">
            ONYX
          </h1>
          <p className="text-xs text-manus-muted hidden sm:block">
            Strategic Intelligence Assistant
          </p>
        </div>
      </div>

      {/* Navigation/Actions */}
      <nav className="flex items-center gap-2" aria-label="Main navigation">
        {/* Mode Toggle */}
        <ModeToggle
          currentMode={currentMode}
          onModeChange={handleModeChange}
          disabled={modeDisabled}
          showLabel={false}
          className="hidden sm:flex"
        />

        {/* User menu placeholder */}
        <button
          type="button"
          className="p-2 sm:p-2.5 rounded-lg hover:bg-manus-bg transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-manus-accent focus-visible:ring-offset-2 focus-visible:ring-offset-manus-surface min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Open menu"
          title="Open navigation menu"
          aria-expanded="false"
          aria-haspopup="true"
        >
          <Menu className="w-4 h-4 sm:w-5 sm:h-5 text-manus-text" />
          <span className="sr-only">Menu</span>
        </button>
      </nav>
    </header>
  );
}
