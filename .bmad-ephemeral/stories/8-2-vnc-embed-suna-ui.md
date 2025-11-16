# Story 8.2: VNC Embed in Suna UI

Status: drafted

## Story

As a founder,
I want the VNC viewer embedded in the Suna UI workspace panel,
so that I can view and interact with the live workspace directly from the web interface.

## Acceptance Criteria

1. AC8.2.1: Workspace Toggle Control - VNC viewer appears in right sidebar (30% width)
2. AC8.2.2: VNC Connection & Display - Connects to noVNC WebSocket server with real-time display
3. AC8.2.3: Responsive Design - Adapts to screen size and works on tablets (landscape orientation)
4. AC8.2.4: Workspace Controls - Maximize, disconnect/reconnect, quality settings available
5. AC8.2.5: Error Handling - Graceful error handling with user feedback and retry mechanism
6. AC8.2.6: Performance Optimization - Smooth real-time updates (target: 30fps) with minimal latency
7. AC8.2.7: Integration with Suna UI - Workspace state maintained across page changes

## Tasks / Subtasks

- [ ] Task 1: Workspace Panel Component (AC: 1, 3, 7)
  - [ ] Subtask 1.1: Create WorkspacePanel React component with VNC viewer
  - [ ] Subtask 1.2: Implement right sidebar layout with 30% width
  - [ ] Subtask 1.3: Add responsive design for tablets and landscape orientation
  - [ ] Subtask 1.4: Integrate with Suna UI state management
- [ ] Task 2: VNC Connection Implementation (AC: 2, 6)
  - [ ] Subtask 2.1: Integrate noVNC.js library for WebSocket connections
  - [ ] Subtask 2.2: Implement real-time display with 30fps target
  - [ ] Subtask 2.3: Optimize for minimal latency performance
  - [ ] Subtask 2.4: Connect to WebSocket endpoint from Story 8.1
- [ ] Task 3: Workspace Controls (AC: 4)
  - [ ] Subtask 3.1: Implement maximize/minimize functionality
  - [ ] Subtask 3.2: Add disconnect/reconnect controls
  - [ ] Subtask 3.3: Create quality settings interface
  - [ ] Subtask 3.4: Add connection status indicators
- [ ] Task 4: Error Handling & Reliability (AC: 5)
  - [ ] Subtask 4.1: Implement graceful error handling for connection failures
  - [ ] Subtask 4.2: Add user feedback notifications
  - [ ] Subtask 4.3: Create retry mechanism with exponential backoff
  - [ ] Subtask 4.4: Handle WebSocket disconnection and recovery
- [ ] Task 5: Testing Integration (All ACs)
  - [ ] Subtask 5.1: Unit tests for VNC connection logic
  - [ ] Subtask 5.2: Integration tests with noVNC server
  - [ ] Subtask 5.3: Performance tests for 30fps target
  - [ ] Subtask 5.4: Responsive design testing on tablets

## Dev Notes

### Technical Architecture

- **Frontend Framework**: React + noVNC.js integration in Suna UI
- **WebSocket Connection**: Connects to noVNC server endpoint from Story 8.1 (port :6080)
- **Component Structure**: WorkspacePanel component with embedded VNC canvas
- **Layout Pattern**: Right sidebar panel with 30% width, resizable capabilities
- **Performance Targets**: 30fps display with <500ms round-trip latency
- **Responsive Design**: Tablet support in landscape orientation with adaptive sizing

### Integration Points

- **noVNC Server**: WebSocket endpoint established in Story 8.1
- **Suna UI Architecture**: Follow existing component patterns and state management
- **Auth System**: Leverage existing Google OAuth authentication
- **API Integration**: Use existing /api/workspace/ endpoints for session management
- **Styling**: Tailwind CSS with Manus dark theme consistency

### Component Architecture

```typescript
// Main component structure
suna/src/components/Workspace/
├── WorkspacePanel.tsx      // Main VNC viewer component
├── WorkspaceControls.tsx   // Control buttons and settings
├── VNCViewer.tsx          // noVNC.js integration
└── WorkspaceContainer.tsx // State management wrapper

// API endpoints
suna/src/app/api/workspace/
├── route.ts               // Workspace session management
├── session/route.ts       // Session CRUD operations
└── connect/route.ts       // VNC connection handling
```

### WebSocket Connection Details

- **Endpoint**: `wss://localhost/vnc/{sessionId}` (proxied through Nginx)
- **Authentication**: JWT token from existing auth system
- **Protocol**: noVNC WebSocket protocol with RFB (Remote Frame Buffer)
- **Connection Management**: Auto-reconnect with exponential backoff
- **Error Handling**: Graceful degradation and user notifications

### Performance Optimization

- **Canvas Rendering**: Use requestAnimationFrame for smooth updates
- **Event Throttling**: Throttle mouse/keyboard events to reduce bandwidth
- **Compression**: Leverage VNC compression from Story 8.1
- **Caching**: Cache connection state and optimize reconnection
- **Memory Management**: Proper cleanup of event listeners and canvas contexts

### Learnings from Previous Story

**From Story 8.1 (noVNC Server Setup):**
- **Server Foundation**: noVNC WebSocket server running on :6080 with authentication
- **Security Implementation**: VNC password encryption and secure token management
- **Docker Integration**: Service pattern established in docker-compose.yaml
- **Performance Baseline**: 30fps target at 1920x1080 with compression enabled
- **Port Configuration**: WebSocket on :6080, VNC on :5900 (internal)
- **Health Monitoring**: Health check endpoints and logging integration ready

**Integration Guidelines:**
- Use established noVNC WebSocket endpoints for secure connections
- Leverage existing authentication system for workspace access
- Follow Docker service patterns for deployment consistency
- Maintain performance targets from server setup
- Implement proper error handling and retry mechanisms
- Use existing monitoring and logging infrastructure

### Responsive Design Requirements

- **Desktop**: Full 30% width sidebar with resizable capabilities
- **Tablet (Landscape)**: Adaptive layout with minimum 400px width
- **Mobile**: Portrait mode not supported due to input requirements
- **Breakpoints**:
  - `min-width: 1024px` for full desktop experience
  - `max-width: 1023px` for tablet adaptation
- **Canvas Scaling**: Automatic scaling to fit container while maintaining aspect ratio

### Project Structure Notes

- **Component Location**: `suna/src/components/Workspace/` following Suna patterns
- **API Routes**: `suna/src/app/api/workspace/` following Next.js App Router
- **Styling**: Tailwind CSS classes with Manus dark theme colors
- **State Management**: React hooks with context for workspace state
- **TypeScript**: Strict typing for all components and API interfaces
- **Testing**: Jest + React Testing Library following existing patterns

### Security Considerations

- **Authentication**: JWT token-based access to WebSocket connections
- **Session Isolation**: Each user gets isolated VNC session
- **Token Validation**: Verify workspace access permissions before connection
- **Input Validation**: Sanitize all mouse and keyboard input events
- **Connection Limits**: Rate limiting to prevent abuse
- **Audit Logging**: Track all workspace interactions for security monitoring

### References

- [Source: docs/epics/epic-8-tech-spec.md#Story-82-VNC-Embed-in-Suna-UI]
- [Source: docs/architecture.md#Epic-8-Live-Workspace-noVNC]
- [Source: .bmad-ephemeral/stories/8-1-novnc-server-setup.md#Learnings-from-Previous-Story]
- [Source: docs/sprint-status.yaml#Story-8-2-vnc-embed-suna-ui]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List