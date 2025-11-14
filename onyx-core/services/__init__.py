"""
ONYX Core Services Package

This package contains service modules for the ONYX Core application.
"""

from .browser_manager import BrowserManager, create_browser_manager

__all__ = ['BrowserManager', 'create_browser_manager']
