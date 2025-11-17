# Story 8.3: Mouse & Keyboard Input Handling

Status: drafted

## Story

As a user,
I want to control VPS desktop via mouse and keyboard in workspace panel,
so that I can intervene, take over, or adjust agent actions.

## Acceptance Criteria

1. Mouse movement captured and forwarded to VNC server
2. Mouse clicks (left/right/middle) executed on remote desktop
3. Keyboard input captured and sent to remote desktop
4. Special keys (Cmd/Ctrl/Alt/Shift) handled correctly
5. Latency <500ms round-trip (browser → VNC → VPS → browser)
6. Cursor visibility and tracking on remote desktop
7. Mobile touch input support for tablets and phones

## Tasks / Subtasks

- Task 8.3.1: Implement comprehensive mouse input handling (AC: 1, 2, 6)
  - Subtask 8.3.1.1: Mouse movement capture and coordinate mapping
  - Subtask 8.3.1.2: Mouse click detection and event transmission
  - Subtask 8.3.1.3: Cursor visibility and tracking implementation
  - Subtask 8.3.1.4: Multi-button support (left/right/middle/wheel)
- Task 8.3.2: Implement keyboard input handling system (AC: 3, 4)
  - Subtask 8.3.2.1: Keyboard event capture and character mapping
  - Subtask 8.3.2.2: Special modifier key handling (Cmd/Ctrl/Alt/Shift)
  - Subtask 8.3.2.3: Function key and media key support
  - Subtask 8.3.2.4: Input validation and sanitization
- Task 8.3.3: Optimize input latency and performance (AC: 5)
  - Subtask 8.3.3.1: Input event batching and transmission optimization
  - Subtask 8.3.3.2: Round-trip latency measurement and monitoring
  - Subtask 8.3.3.3: Network congestion handling and adaptive quality
  - Subtask 8.3.3.4: Performance testing and validation
- Task 8.3.4: Implement mobile touch input support (AC: 7)
  - Subtask 8.3.4.1: Touch event capture and coordinate mapping
  - Subtask 8.3.4.2: Touch gesture support (tap, long press, swipe)
  - Subtask 3.3.4.3: Virtual keyboard integration for mobile devices
  - Subtask 8.3.4.4: Mobile-specific UI adaptations and responsive design
- Task 8.3.5: Integration testing and validation (AC: 1, 2, 3, 4, 5, 6, 7)
  - Subtask 8.3.5.1: End-to-end input flow testing
  - Subtask 8.3.5.2: Cross-browser compatibility testing
  - Subtask 8.3.5.3: Mobile device testing and validation
  - Subtask 8.3.5.4: Performance benchmarking and optimization

## Dev Notes

### Learnings from Previous Story

**From Story 8-2-workspace-session-management (Status: done)**

- **New VNC Integration**: Real noVNC RFB client integration established with comprehensive WebSocket support and VNC protocol encoding. Available at `suna/src/components/Workspace/VNCViewer.tsx` and `suna/src/components/Workspace/WorkspaceProvider.tsx`.
- **Authentication System**: JWT-based authentication system implemented with workspace-specific permission validation and secure token management.
- **Performance Framework**: 30fps target performance optimization system with intelligent auto-quality adjustment and real-time monitoring implemented.
- **Security Architecture**: Multi-layer security with WebSocket encryption (wss:// protocol detection), input validation, and comprehensive audit logging.
- **Technical Debt**: None noted in review - Story 8.2 achieved 4.5/5 code quality rating.

### Project Structure Notes

**File Structure Integration:**
- Extend existing `suna/src/components/Workspace/` directory structure
- Leverage existing `WorkspaceProvider.tsx` state management system
- Integrate with established authentication and security patterns
- Maintain consistency with existing component architecture

**Architecture Alignment:**
- Follow established noVNC RFB client integration patterns from Story 8.2
- Use existing WebSocket connection management and error handling
- Maintain performance optimization and auto-quality adjustment systems
- Preserve security-first approach with proper input validation

### References

- [Source: docs/epics.md#story-83-mouse-keyboard-input-handling]
- [Source: docs/stories/8-2-workspace-session-management.md#Technical-Architecture]
- [Source: docs/stories/8-2-workspace-session-management.md#Code-Review]
- [Source: docs/sprint-status.yaml#epic-8]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List