'use client';

import React from 'react';
import { Menu } from 'lucide-react';

export interface HeaderProps {
  className?: string;
}

export function Header({ className = '' }: HeaderProps) {
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

      {/* Navigation/Actions - Placeholder for future features */}
      <nav className="flex items-center gap-2" aria-label="Main navigation">
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
