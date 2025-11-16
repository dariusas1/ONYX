# Story 8.1: noVNC Server Setup

Status: drafted

## Story

As a ops engineer,
I want noVNC VNC server running on VPS,
so that founder can remotely view and control VPS desktop.

## Acceptance Criteria

1. Given: VPS running (Hostinger KVM 4)
2. When: noVNC service started
3. Then: VNC server listening on :6080 (WebSocket)
4. And: Supports resolution 1920x1080
5. And: Framerate 30fps target
6. And: Compression enabled for lower bandwidth
7. And: Security: VNC password set (stored encrypted)

## Tasks / Subtasks

- [ ] Task 1: Set up noVNC Docker service (AC: 3, 4, 5, 6, 7)
  - [ ] Subtask 1.1: Deploy noVNC container with websockify proxy
  - [ ] Subtask 1.2: Configure VNC server connection and display
  - [ ] Subtask 1.3: Set up WebSocket endpoint on port 6080
  - [ ] Subtask 1.4: Configure resolution (1920x1080) and framerate (30fps)
  - [ ] Subtask 1.5: Enable compression for bandwidth optimization
  - [ ] Subtask 1.6: Implement VNC password encryption and storage
- [ ] Task 2: Integration with Docker Compose (AC: 3)
  - [ ] Subtask 2.1: Add noVNC service to docker-compose.yaml
  - [ ] Subtask 2.2: Configure networking and port exposure
  - [ ] Subtask 2.3: Set up environment variables and secrets
- [ ] Task 3: Health checks and monitoring (AC: 3)
  - [ ] Subtask 3.1: Implement health check endpoint
  - [ ] Subtask 3.2: Add logging and monitoring integration
  - [ ] Subtask 3.3: Test connectivity and performance

## Dev Notes

### Technical Architecture

- **noVNC Server**: WebSocket-based VNC client running in browser
- **websockify**: Proxy that translates VNC protocol to WebSocket
- **Port Configuration**:
  - :6080 - WebSocket interface for noVNC
  - :5900 - Standard VNC port (internal)
- **Performance Targets**: 30fps at 1920x1080 with <500ms latency
- **Security**: VNC password authentication with encrypted storage

### Integration Points

- **Docker Compose**: Add as service alongside existing containers
- **Nginx**: Route /vnc/* traffic to noVNC service (configured in Story 1.2)
- **Environment Variables**: VNC password, display settings, compression options
- **Health Monitoring**: Integration with existing logging infrastructure

### VPS Requirements

- **Hostinger KVM 4**: 4 vCPU, 16GB RAM, sufficient for VNC + desktop environment
- **Display**: Configure virtual display (Xvfb or similar) for headless operation
- **Desktop Environment**: Lightweight desktop (XFCE, LXDE) for remote access

### Project Structure Notes

- Follow Docker service pattern established in Story 1.1
- Use environment variable management from Story 1.3
- Integrate with monitoring from Story 1.6
- No conflicts with existing architecture - new service addition

### References

- [Source: docs/epics.md#Epic-8-Live-Workspace-noVNC]
- [Source: docs/architecture.md#VNC-Workspace-noVNC]
- [Source: docs/PRD.md#Live-Workspace-noVNC]
- [Source: docs/architecture.md#Decision-Summary]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List