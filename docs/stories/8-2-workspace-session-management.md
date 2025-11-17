# Story 8.2: VNC Embed in Suna UI

**Epic:** Epic 8 - Live Workspace (noVNC)
**Status:** Drafted
**Priority:** High
**Estimate:** 5 story points
**Owner:** TBD
**Created:** 2025-11-16
**Target Completion:** TBD

---

## User Story

**As a** founder using Manus Internal,
**I want** to see and control the live VNC workspace directly within the Suna UI,
**so that** I can monitor agent actions in real-time and intervene when necessary without leaving the chat interface.

---

## Story Statement

Build and integrate a noVNC viewer component within the Suna UI that provides real-time desktop control capabilities. This includes embedding the VNC viewer in a sidebar/overlay, implementing WebSocket-based input handling with sub-500ms latency, and enabling founder intervention workflows to pause agents and take manual control of the workspace.

---

## Epic Context

**Epic 8: Live Workspace (noVNC)** - Epic Goal: Enable real-time workspace control with agent oversight and founder intervention capabilities.

**Relationship to other stories in Epic 8:**
- **Story 8.1 (noVNC Server Setup)** - ✅ **Completed** - Prerequisite that establishes the VNC server foundation
- **Story 8.2 (VNC Embed in Suna UI)** - 🔄 **Current** - Builds the frontend integration layer
- **Story 8.3 (Workspace Session Management)** - 📋 **Next** - Will add session persistence and management

**Dependencies:**
- **Must have:** Story 8.1 completed (noVNC server running)
- **Should have:** Basic chat functionality working
- **Nice to have:** Agent Mode functional for demonstration

---

## Acceptance Criteria

### AC1: VNC Viewer Integration
**Given** the noVNC server is running from Story 8.1
**When** the user opens the workspace panel in Suna UI
**Then** the VNC viewer displays the live desktop stream in a sidebar/overlay with proper sizing and responsive behavior

### AC2: Real-time Input Handling
**Given** the VNC viewer is displaying the desktop
**When** the user moves their mouse or types on the keyboard
**Then** input events are transmitted to the VNC server with <300ms latency and visible desktop response

### AC3: Founder Intervention Workflow
**Given** an agent is actively working in the workspace
**When** the founder clicks the "Take Control" button
**Then** agent actions are paused and the founder gains exclusive mouse/keyboard control with visual feedback

### AC4: Display Quality Controls
**Given** the VNC viewer is active
**When** the user opens quality settings
**Then** they can adjust resolution, compression levels, and frame rate with immediate effect on performance

### AC5: Cross-Session Persistence
**Given** the user has the workspace panel open
**When** they refresh the browser or close and reopen the tab
**Then** the VNC connection automatically reconnects and restores the previous session state

### AC6: Responsive Layout
**Given** the VNC viewer is embedded in Suna UI
**When** the browser window is resized or viewed on different screen sizes
**Then** the workspace panel adapts appropriately (collapsible sidebar, overlay modes, mobile support)

### AC7: Connection Status Monitoring
**Given** the VNC workspace is active
**When** connection issues occur (latency, disconnect, server down)
**Then** clear status indicators and error messages guide the user through recovery

---

## Implementation Tasks

### Frontend Development (Suna UI)
- [ ] **Task 8.2.1:** Create VNC viewer React component using noVNC library
- [ ] **Task 8.2.2:** Implement WebSocket connection to noVNC server
- [ ] **Task 8.2.3:** Build responsive sidebar/overlay layout system
- [ ] **Task 8.2.4:** Add mouse/keyboard event capture and transmission
- [ ] **Task 8.2.5:** Implement quality controls (resolution, compression, frame rate)
- [ ] **Task 8.2.6:** Create connection status indicators and error handling
- [ ] **Task 8.2.7:** Build intervention workflow UI (take control/release control)
- [ ] **Task 8.2.8:** Add session persistence and auto-reconnection logic

### Backend Integration
- [ ] **Task 8.2.9:** Configure Nginx routes for WebSocket upgrade (/vnc/* paths)
- [ ] **Task 8.2.10:** Implement session management API endpoints
- [ ] **Task 8.2.11:** Add agent control coordination (pause/resume for intervention)
- [ ] **Task 8.2.12:** Build audit logging for workspace actions

### Testing & Validation
- [ ] **Task 8.2.13:** Test VNC connection and display quality
- [ ] **Task 8.2.14:** Validate input latency performance (<300ms target)
- [ ] **Task 8.2.15:** Test intervention workflow timing and state management
- [ ] **Task 8.2.16:** Verify responsive design across screen sizes
- [ ] **Task 8.2.17:** Test session persistence and reconnection scenarios

---

## Definition of Done

- [ ] VNC viewer successfully embedded in Suna UI
- [ ] Real-time input transmission with measured latency <300ms
- [ ] Founder can pause agents and take control with visual feedback
- [ ] Quality controls functional and responsive
- [ ] Workspace persists across browser sessions
- [ ] Connection status monitoring and error handling implemented
- [ ] Responsive layout works on desktop, tablet, and mobile
- [ ] All tasks completed and passed testing
- [ ] Code reviewed and merged to main branch
- [ ] Documentation updated

---

## Technical Architecture

### Frontend Components
```
suna/src/components/Workspace/
├── VNCViewer.tsx           # Main noVNC viewer component
├── WorkspacePanel.tsx      # Sidebar/overlay container
├── ControlOverlay.tsx      # Intervention controls
├── QualityControls.tsx     # Resolution, compression settings
├── ConnectionStatus.tsx    # Status indicators and error display
└── WorkspaceProvider.tsx   # State management for workspace
```

### API Endpoints
```
GET  /api/workspace/status    # VNC server status and connection info
POST /api/workspace/take-control  # Request control from agent
POST /api/workspace/release-control  # Return control to agent
GET  /api/workspace/settings  # Quality settings and preferences
POST /api/workspace/settings  # Update quality settings
```

### Integration Points
- **noVNC Server:** WebSocket connection to `ws://localhost:6080/websockify`
- **Agent Coordination:** Pause/resume signals via task management system
- **Session Storage:** Workspace preferences and connection state in Redis
- **Audit Logging:** All control changes logged to PostgreSQL

### Performance Targets
- **Initial connection:** <2 seconds to first frame
- **Input latency:** <300ms round-trip (mouse move to desktop response)
- **Frame rate:** 30fps at 1920x1080 resolution
- **Reconnection:** <5 seconds to restore session after disconnect

---

## Testing Strategy

### Unit Tests
- VNC viewer component mounting and connection logic
- Input event handling and transmission
- Quality control state management
- Session persistence and recovery

### Integration Tests
- End-to-end VNC connection flow
- Agent intervention workflow timing
- WebSocket reconnection scenarios
- Cross-browser compatibility

### Performance Tests
- Latency measurement under load
- Memory usage with extended sessions
- Network interruption recovery
- Multi-user session handling (future)

### Manual Validation
- Real-world founder workflow testing
- Mobile and tablet usability validation
- Connection failure scenario testing
- Long-duration stability testing

---

## Dependencies & Risks

### Technical Dependencies
- **noVNC server** (Story 8.1) - Must be operational and accessible
- **WebSocket support** - Browser and network compatibility
- **Agent coordination system** - For pause/resume functionality
- **Session management** - Redis for state persistence

### Risk Mitigation
- **Connection reliability:** Implement auto-reconnection with exponential backoff
- **Performance latency:** Optimize WebSocket framing and compression
- **Browser compatibility:** Test across Chrome, Firefox, Safari, Edge
- **Mobile limitations:** Graceful degradation for touch-only devices
- **Security concerns:** Ensure VNC access is properly authenticated and authorized

---

## Acceptance Test Scenarios

### Scenario 1: Basic VNC Viewing
1. User opens Suna UI in browser
2. User clicks "Workspace" button to open panel
3. VNC viewer loads and displays remote desktop
4. User can see desktop in real-time with minimal lag

### Scenario 2: Input Control
1. VNC viewer is displaying desktop
2. User moves mouse cursor within viewer area
3. Cursor on remote desktop moves correspondingly
4. User types text using keyboard
5. Text appears on remote desktop within 300ms

### Scenario 3: Agent Intervention
1. Agent is actively working in workspace (visible in viewer)
2. User clicks "Take Control" button
3. Agent actions pause immediately
4. User gains exclusive mouse/keyboard control
5. User clicks "Release Control" to return control to agent
6. Agent resumes work from previous state

### Scenario 4: Quality Adjustment
1. VNC connection is active but performance is slow
2. User opens quality settings panel
3. User reduces resolution from 1920x1080 to 1280x720
4. User increases compression level
5. Performance improves with acceptable quality trade-off

### Scenario 5: Session Recovery
1. User has active workspace session
2. User closes browser tab
3. User reopens browser and navigates to Suna UI
4. Workspace panel automatically reconnects to previous session
5. Desktop state is preserved from previous session

---

## Notes & Questions

### Open Questions
- **Mobile support:** How should touch events be mapped to mouse events?
- **Multi-monitor:** Should we support multiple remote displays?
- **Clipboard sync:** Should we implement bidirectional clipboard synchronization?
- **Recording:** Should we offer to record workspace sessions for playback?

### Decisions Made
- **Layout approach:** Sidebar primary, overlay secondary for better UX
- **Connection method:** WebSocket via Nginx proxy for reliability
- **Quality defaults:** Balanced settings prioritizing responsiveness over resolution
- **Security model:** Workspace access inherits user authentication, no additional auth required

### Lessons from Story 8.1
- noVNC server setup confirmed working with WebSocket proxy configuration
- Performance baseline established with current VPS resources
- Network topology validated for WebSocket upgrade handling
- Integration patterns established for backend coordination

---

**Story created:** 2025-11-16
**Last updated:** 2025-11-16
**Ready for development:** ✅ Yes