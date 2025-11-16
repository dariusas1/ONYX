import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { VNCViewer } from '../VNCViewer';

// Mock noVNC library
jest.mock('@novnc/novnc/core/rfb', () => {
  return jest.fn().mockImplementation(() => ({
    addEventListener: jest.fn(),
    scaleViewport: true,
    resizeSession: false,
    qualityLevel: 6,
    compressionLevel: 1,
    disconnect: jest.fn(),
    sendCredentials: jest.fn(),
    sendKey: jest.fn(),
    sendMouseEvent: jest.fn(),
    _fbWidth: 1920,
    _fbHeight: 1080,
  }));
});

jest.mock('@novnc/novnc/core/input/keysym', () => ({
  XK_VoidSymbol: 'VoidSymbol',
  XK_Return: 'Return',
  XK_Space: 'space',
  XK_Escape: 'Escape',
  XK_Left: 'Left',
  XK_Right: 'Right',
  XK_Up: 'Up',
  XK_Down: 'Down',
}));

jest.mock('@novnc/novnc/core/input/mouse', () => ({}));

describe('VNCViewer Component', () => {
  const defaultProps = {
    url: 'ws://localhost:6080',
    onConnect: jest.fn(),
    onDisconnect: jest.fn(),
    onError: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock requestFullscreen and exitFullscreen
    document.requestFullscreen = jest.fn().mockResolvedValue();
    document.exitFullscreen = jest.fn().mockResolvedValue();
    Object.defineProperty(document, 'fullscreenElement', {
      writable: true,
      value: null,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Component Rendering', () => {
    test('renders VNC viewer with initial connection state', () => {
      render(<VNCViewer {...defaultProps} />);

      const canvas = screen.getByRole('img'); // canvas role
      expect(canvas).toBeInTheDocument();
      expect(canvas).toHaveClass('w-full', 'h-full');
    });

    test('renders with custom className', () => {
      render(<VNCViewer {...defaultProps} className="custom-class" />);

      const container = screen.getByRole('img').parentElement;
      expect(container).toHaveClass('custom-class');
    });

    test('renders connection status indicators', () => {
      render(<VNCViewer {...defaultProps} />);

      // Should show connecting status initially
      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    test('renders workspace info when dimensions are set', async () => {
      render(<VNCViewer {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('1920 × 1080')).toBeInTheDocument();
      });
    });

    test('renders performance indicator when connected', async () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        qualityLevel: 6,
        compressionLevel: 1,
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} />);

      // Simulate connected state
      const connectCallback = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );
      if (connectCallback) {
        connectCallback[1]();
      }

      await waitFor(() => {
        expect(screen.getByText(/Scaled.*Quality: 6\/9/)).toBeInTheDocument();
      });
    });
  });

  describe('Connection Management', () => {
    test('initializes RFB connection on mount', () => {
      const RFB = require('@novnc/novnc/core/rfb').default;
      render(<VNCViewer {...defaultProps} />);

      expect(RFB).toHaveBeenCalledWith(
        expect.any(HTMLCanvasElement),
        'ws://localhost:6080',
        expect.objectContaining({
          shared: true,
          repeaterID: '',
          credentials: expect.any(Function),
        })
      );
    });

    test('calls onConnect when RFB connects', async () => {
      const onConnect = jest.fn();
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} onConnect={onConnect} />);

      // Find the connect event listener
      const connectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );

      if (connectCall) {
        connectCall[1](); // Simulate connection
      }

      await waitFor(() => {
        expect(onConnect).toHaveBeenCalled();
      });
    });

    test('calls onDisconnect when RFB disconnects', async () => {
      const onDisconnect = jest.fn();
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} onDisconnect={onDisconnect} />);

      // Find the disconnect event listener
      const disconnectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'disconnect'
      );

      if (disconnectCall) {
        disconnectCall[1]({ detail: { reason: 'Test disconnect' } });
      }

      await waitFor(() => {
        expect(onDisconnect).toHaveBeenCalledWith('Test disconnect');
      });
    });

    test('handles connection errors', async () => {
      const onError = jest.fn();
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} onError={onError} />);

      // Find the securityfailure event listener
      const errorCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'securityfailure'
      );

      if (errorCall) {
        errorCall[1]({ detail: { reason: 'Authentication failed' } });
      }

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Security failure: Authentication failed');
        expect(screen.getByText('Connection Error')).toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    test('handles keyboard events when connected', async () => {
      const user = userEvent.setup();
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        sendKey: jest.fn(),
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} />);

      // Simulate connected state
      const connectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );
      if (connectCall) {
        connectCall[1]();
      }

      await waitFor(() => {
        const container = screen.getByRole('img').parentElement;
        expect(container).toBeInTheDocument();
      });

      const container = screen.getByRole('img').parentElement;

      // Test key down event
      await user.keyboard('{Enter}');
      expect(mockRFB.sendKey).toHaveBeenCalledWith('Return', 1, false, false, false, false);

      // Test key up event
      await user.keyboard('{Enter}');
      expect(mockRFB.sendKey).toHaveBeenLastCalledWith('Return', 0, false, false, false, false);
    });

    test('handles mouse events when connected', async () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        sendMouseEvent: jest.fn(),
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} />);

      // Simulate connected state
      const connectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );
      if (connectCall) {
        connectCall[1]();
      }

      await waitFor(() => {
        const canvas = screen.getByRole('img');
        expect(canvas).toBeInTheDocument();
      });

      const canvas = screen.getByRole('img');

      // Test mouse down event
      fireEvent.mouseDown(canvas, { clientX: 100, clientY: 100, button: 0 });
      expect(mockRFB.sendMouseEvent).toHaveBeenCalledWith(100, 100, 1, 1);

      // Test mouse up event
      fireEvent.mouseUp(canvas, { clientX: 100, clientY: 100, button: 0 });
      expect(mockRFB.sendMouseEvent).toHaveBeenCalledWith(100, 100, 1, 0);

      // Test mouse move event
      fireEvent.mouseMove(canvas, { clientX: 150, clientY: 150, buttons: 1 });
      expect(mockRFB.sendMouseEvent).toHaveBeenCalledWith(150, 150, 1, true);
    });

    test('toggles fullscreen mode', async () => {
      const user = userEvent.setup();
      render(<VNCViewer {...defaultProps} />);

      await waitFor(() => {
        const fullscreenButton = screen.getByTitle('Enter Fullscreen');
        expect(fullscreenButton).toBeInTheDocument();
      });

      const fullscreenButton = screen.getByTitle('Enter Fullscreen');
      await user.click(fullscreenButton);

      expect(document.requestFullscreen).toHaveBeenCalled();
    });

    test('retries connection on retry button click', async () => {
      const user = userEvent.setup();
      render(<VNCViewer {...defaultProps} />);

      // Wait for connecting state to show retry button
      await waitFor(() => {
        const retryButton = screen.getByRole('button', { name: /retry/i });
        expect(retryButton).toBeInTheDocument();
      });

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      // Should attempt to reconnect (mock RFB should be called again)
      const RFB = require('@novnc/novnc/core/rfb').default;
      expect(RFB).toHaveBeenCalledTimes(2); // Initial mount + retry
    });
  });

  describe('Responsive Design', () => {
    test('applies touch-action none for tablets', () => {
      render(<VNCViewer {...defaultProps} />);

      const canvas = screen.getByRole('img');
      expect(canvas).toHaveStyle({
        touchAction: 'none'
      });
    });

    test('handles window resize events', async () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} />);

      // Trigger window resize
      fireEvent(window, new Event('resize'));

      await waitFor(() => {
        expect(screen.getByText('1920 × 1080')).toBeInTheDocument();
      });
    });
  });

  describe('Settings Updates', () => {
    test('updates VNC settings when props change', async () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      const { rerender } = render(
        <VNCViewer {...defaultProps} quality={6} compression={1} />
      );

      // Simulate connected state
      const connectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );
      if (connectCall) {
        connectCall[1]();
      }

      await waitFor(() => {
        expect(screen.getByText(/Quality: 6\/9/)).toBeInTheDocument();
      });

      // Update settings
      rerender(<VNCViewer {...defaultProps} quality={9} compression={0} />);

      await waitFor(() => {
        expect(mockRFB.qualityLevel).toBe(9);
        expect(mockRFB.compressionLevel).toBe(0);
      });
    });

    test('shows original size when scale is false', async () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: false, // Scale disabled
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      render(<VNCViewer {...defaultProps} scale={false} />);

      // Simulate connected state
      const connectCall = mockRFB.addEventListener.mock.calls.find(
        call => call[0] === 'connect'
      );
      if (connectCall) {
        connectCall[1]();
      }

      await waitFor(() => {
        expect(screen.getByText(/Original Size.*Quality: 6\/9/)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    test('handles canvas unavailability gracefully', () => {
      // Mock canvas ref to be null
      const { rerender } = render(<VNCViewer {...defaultProps} />);

      // Component should still render without crashing
      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    test('handles fullscreen API errors gracefully', async () => {
      const user = userEvent.setup();
      // Mock fullscreen rejection
      document.requestFullscreen = jest.fn().mockRejectedValue(new Error('Fullscreen denied'));

      render(<VNCViewer {...defaultProps} />);

      await waitFor(() => {
        const fullscreenButton = screen.getByTitle('Enter Fullscreen');
        expect(fullscreenButton).toBeInTheDocument();
      });

      const fullscreenButton = screen.getByTitle('Enter Fullscreen');

      // Should not throw error
      await user.click(fullscreenButton);
    });
  });

  describe('Cleanup', () => {
    test('disconnects RFB on unmount', () => {
      const mockRFB = {
        addEventListener: jest.fn(),
        scaleViewport: true,
        resizeSession: false,
        qualityLevel: 6,
        compressionLevel: 1,
        disconnect: jest.fn(),
        _fbWidth: 1920,
        _fbHeight: 1080,
      };

      const RFB = require('@novnc/novnc/core/rfb').default;
      RFB.mockImplementation(() => mockRFB);

      const { unmount } = render(<VNCViewer {...defaultProps} />);

      unmount();

      expect(mockRFB.disconnect).toHaveBeenCalled();
    });

    test('removes event listeners on unmount', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');

      const { unmount } = render(<VNCViewer {...defaultProps} />);

      unmount();

      // Should remove fullscreen change listener
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'fullscreenchange',
        expect.any(Function)
      );

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });
});