import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { Header } from '@/components/Header';

describe('Header', () => {
  it('renders without crashing', () => {
    render(<Header />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('displays ONYX logo and branding', () => {
    render(<Header />);

    // Check for logo "O"
    expect(screen.getByText('O')).toBeInTheDocument();

    // Check for ONYX title
    expect(screen.getByText('ONYX')).toBeInTheDocument();
  });

  it('renders the logo with correct styling', () => {
    render(<Header />);

    const logo = screen.getByText('O');
    expect(logo).toHaveClass('text-white', 'font-bold', 'text-lg');

    // Logo should be in a container with accent background
    const logoContainer = logo.parentElement;
    expect(logoContainer).toHaveClass('bg-manus-accent');
  });

  it('renders ONYX heading with correct styling', () => {
    render(<Header />);

    const heading = screen.getByText('ONYX');
    expect(heading).toHaveClass('text-xl', 'font-semibold', 'text-manus-text');

    // Check it's an h1 element
    expect(heading.tagName).toBe('H1');
  });

  it('renders menu button with proper ARIA labels', () => {
    render(<Header />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toBeInTheDocument();
    expect(menuButton).toHaveAttribute('aria-label', 'Open menu');
    expect(menuButton).toHaveAttribute('title', 'Menu');
  });

  it('menu button is clickable', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });

    // Button should be enabled and clickable (even if no handler yet)
    expect(menuButton).not.toBeDisabled();
    await user.click(menuButton);

    // No error should occur (it's a placeholder button)
  });

  it('applies custom className prop', () => {
    const customClass = 'custom-header-class';
    render(<Header className={customClass} />);

    const header = screen.getByRole('banner');
    expect(header).toHaveClass(customClass);
  });

  it('has proper semantic HTML structure', () => {
    render(<Header />);

    const header = screen.getByRole('banner');
    expect(header.tagName).toBe('HEADER');
  });

  it('applies Manus theme colors', () => {
    render(<Header />);

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('bg-manus-surface', 'border-manus-border');
  });

  it('has correct layout classes for responsive design', () => {
    render(<Header />);

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('flex', 'items-center', 'justify-between');
  });

  it('contains menu icon', () => {
    render(<Header />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });

    // Menu icon should be present (lucide-react Menu component)
    // Check for SVG element inside button
    const svg = menuButton.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders all key sections', () => {
    render(<Header />);

    // Logo section
    expect(screen.getByText('O')).toBeInTheDocument();
    expect(screen.getByText('ONYX')).toBeInTheDocument();

    // Navigation/Actions section
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('maintains consistent spacing and padding', () => {
    render(<Header />);

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('px-4', 'py-3');
  });

  it('has border styling', () => {
    render(<Header />);

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('border-b', 'border-manus-border');
  });

  it('menu button has hover effect classes', () => {
    render(<Header />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toHaveClass('hover:bg-manus-bg', 'transition-colors');
  });
});
