const mockRFB = jest.fn().mockImplementation(() => {
  const mockInstance = {
    addEventListener: jest.fn(),
    disconnect: jest.fn(),
    resize: jest.fn(),
    sendMouseButton: jest.fn(),
    sendMouseMove: jest.fn(),
    sendMouseWheel: jest.fn(),
    sendKeyboardEvent: jest.fn(),
    keyboardEvents: {
      push: jest.fn()
    }
  };

  // Add connect event listener support
  mockInstance.connectListeners = [];
  mockInstance.addEventListener.mockImplementation((event, handler) => {
    mockInstance.connectListeners.push({ event, handler });
  });

  // Helper to trigger events
  mockInstance.triggerEvent = (event, data) => {
    const listener = mockInstance.connectListeners.find(l => l.event === event);
    if (listener) {
      if (data) {
        listener.handler({ detail: data });
      } else {
        listener.handler();
      }
    }
  };

  return mockInstance;
});

module.exports = mockRFB;