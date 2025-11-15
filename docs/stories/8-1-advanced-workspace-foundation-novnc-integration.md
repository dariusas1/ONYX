# Story 8.1: Advanced Workspace Foundation with noVNC Integration

## Story Metadata

- **Story ID**: 8-1-advanced-workspace-foundation-novnc-integration
- **Title**: Advanced Workspace Foundation with noVNC Integration
- **Epic**: Epic 8 (Advanced Workspace Integration & Collaborative Intelligence)
- **Priority**: P0 (Critical)
- **Estimated Points**: 8
- **Status**: drafted
- **Sprint**: Sprint 8-1
- **Assigned To**: TBD
- **Created Date**: 2025-11-15
- **Dependencies**: Epic 1, Epic 2

## Story

As a founder,
I want a high-performance workspace interface embedded in ONYX,
So that I can observe Manus work in real-time and intervene when needed.

## Acceptance Criteria

### AC8.1.1: noVNC Server Deployment
- **Requirement**: noVNC server deployed with WebSocket support on port 6080
- **Evidence**: noVNC container running successfully with WebSocket endpoint accessible
- **Test**: Verify WebSocket connection establishment and basic screen sharing functionality

### AC8.1.2: Workspace Viewer Integration
- **Requirement**: Workspace viewer embedded in Suna UI with resizable panel (20-80% width)
- **Evidence**: Resizable workspace panel integrated into React interface with smooth drag-to-resize
- **Test**: Test panel resizing across different breakpoints and verify responsive behavior

### AC8.1.3: Real-Time Streaming Performance
- **Requirement**: Real-time streaming at 30fps with adaptive compression (1920x1080 base resolution)
- **Evidence**: Performance metrics showing 30fps with adaptive quality based on network conditions
- **Test**: Load test with varying network conditions and verify frame rate maintenance

### AC8.1.4: Low Latency Response
- **Requirement**: Connection latency <500ms measured from UI input to workspace response
- **Evidence**: Latency monitoring showing consistent sub-500ms response times
- **Test**: Input latency testing with mouse movements and keyboard interactions

### AC8.1.5: Session Persistence
- **Requirement**: Workspace state persists across browser sessions and page refreshes
- **Evidence**: Workspace connection restored automatically after page refresh or browser restart
- **Test**: Disconnect and reconnect scenarios with state preservation validation

### AC8.1.6: Mobile Optimization
- **Requirement**: Mobile-optimized controls with touch gestures and virtual keyboard support
- **Evidence**: Touch gesture recognition and mobile-specific controls working on tablets and phones
- **Test**: Mobile device testing with touch interactions and virtual keyboard functionality

### AC8.1.7: Workspace Toolbar
- **Requirement**: Workspace toolbar with essential controls (fullscreen, quality settings, disconnect)
- **Evidence**: Functional toolbar with all controls working and properly positioned
- **Test**: Verify each toolbar control functionality and keyboard shortcuts

## Technical Requirements

### noVNC Configuration
- **WebSocket Server**: Configured on port 6080 with secure WebSocket support
- **Resolution Support**: Base resolution 1920x1080 with automatic scaling
- **Compression**: Adaptive compression based on network bandwidth
- **Authentication**: Secure token-based authentication for workspace access

### React Integration
- **Component Architecture**: Workspace viewer as reusable React component
- **State Management**: Integration with existing Redux/localStorage patterns
- **Responsive Design**: Mobile-first approach with breakpoints at sm, md, lg
- **Performance**: Efficient rendering with requestAnimationFrame optimization

### Network Optimization
- **Bandwidth Detection**: Automatic quality adjustment based on available bandwidth
- **Connection Recovery**: Automatic reconnection with exponential backoff
- **Latency Compensation**: Predictive rendering for improved perceived performance
- **Mobile Data Optimization**: Reduced quality and frame rates for mobile networks

## Implementation Tasks

### Phase 1: Infrastructure Setup (3 points)
- [ ] Task 1.1: Deploy noVNC Docker container with WebSocket configuration
  - [ ] Subtask 1.1.1: Create noVNC Dockerfile with optimization settings
  - [ ] Subtask 1.1.2: Configure WebSocket server with secure connection support
  - [ ] Subtask 1.1.3: Set up authentication middleware for workspace access
  - [ ] Subtask 1.1.4: Configure compression and quality settings
  - [ ] Subtask 1.1.5: Add health checks and monitoring endpoints

- [ ] Task 1.2: Integrate noVNC service into Docker Compose
  - [ ] Subtask 1.2.1: Update docker-compose.yaml with noVNC service definition
  - [ ] Subtask 1.2.2: Configure network and port exposure
  - [ ] Subtask 1.2.3: Set up volume mounting for persistence
  - [ ] Subtask 1.2.4: Configure environment variables and secrets
  - [ ] Subtask 1.2.5: Add dependency management with other services

### Phase 2: Frontend Integration (3 points)
- [ ] Task 2.1: Create React workspace viewer component
  - [ ] Subtask 2.1.1: Install noVNC client library and TypeScript definitions
  - [ ] Subtask 2.1.2: Create WorkspaceViewer.tsx with noVNC integration
  - [ ] Subtask 2.1.3: Implement resizable panel with drag functionality
  - [ ] Subtask 2.1.4: Add connection state management and error handling
  - [ ] Subtask 2.1.5: Implement adaptive quality controls

- [ ] Task 2.2: Integrate workspace into Suna UI layout
  - [ ] Subtask 2.2.1: Update main layout to accommodate workspace panel
  - [ ] Subtask 2.2.2: Implement responsive design for different screen sizes
  - [ ] Subtask 2.2.3: Add workspace toggle and visibility controls
  - [ ] Subtask 2.2.4: Implement keyboard shortcuts for workspace control
  - [ ] Subtask 2.2.5: Add accessibility features and screen reader support

### Phase 3: Performance & Mobile Optimization (2 points)
- [ ] Task 3.1: Implement adaptive streaming optimization
  - [ ] Subtask 3.1.1: Add bandwidth detection and quality adjustment
  - [ ] Subtask 3.1.2: Implement frame rate optimization based on device capabilities
  - [ ] Subtask 3.1.3: Add connection quality monitoring and alerts
  - [ ] Subtask 3.1.4: Implement progressive loading and buffering strategies
  - [ ] Subtask 3.1.5: Add performance metrics collection and reporting

- [ ] Task 3.2: Mobile touch optimization
  - [ ] Subtask 3.2.1: Implement touch gesture recognition (pinch, swipe, tap)
  - [ ] Subtask 3.2.2: Add virtual keyboard integration for mobile devices
  - [ ] Subtask 3.2.3: Optimize UI controls for touch interfaces
  - [ ] Subtask 3.2.4: Implement mobile-specific toolbar and controls
  - [ ] Subtask 3.2.5: Add orientation change handling and responsive adjustments

## Database Schema

### workspace_sessions Table
```sql
CREATE TABLE workspace_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  session_token VARCHAR(255) UNIQUE NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE,
  duration_seconds INTEGER,
  connection_info JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_workspace_sessions_user_id (user_id),
  INDEX idx_workspace_sessions_token (session_token),
  INDEX idx_workspace_sessions_started_at (started_at)
);
```

### workspace_connections Table
```sql
CREATE TABLE workspace_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES workspace_sessions(id),
  client_info JSONB,
  connection_quality JSONB,
  bandwidth_metrics JSONB,
  latency_metrics JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_workspace_connections_session_id (session_id),
  INDEX idx_workspace_connections_created_at (created_at)
);
```

## API Endpoints

### Workspace Session Management
- `POST /api/workspace/sessions` - Create new workspace session
- `GET /api/workspace/sessions/{id}` - Get session details and connection info
- `DELETE /api/workspace/sessions/{id}` - End workspace session
- `GET /api/workspace/sessions/{id}/status` - Get session status and metrics

### Connection Management
- `POST /api/workspace/connect` - Establish workspace connection
- `GET /api/workspace/quality` - Get current connection quality metrics
- `POST /api/workspace/quality/adjust` - Manually adjust streaming quality
- `GET /api/workspace/stats` - Get performance statistics

### Configuration
- `GET /api/workspace/config` - Get workspace configuration
- `POST /api/workspace/config/update` - Update workspace preferences
- `GET /api/workspace/capabilities` - Get supported features and limits

## Configuration

### Environment Variables
```env
# noVNC Configuration
NOVNC_PORT=6080
NOVNC_HOST=0.0.0.0
NOVNC_RESOLUTION=1920x1080
NOVNC_QUALITY=8
NOVNC_COMPRESSION=true

# Workspace Security
WORKSPACE_SECRET_KEY=your-secret-key
WORKSPACE_TOKEN_EXPIRY=3600
WORKSPACE_MAX_SESSIONS=5

# Performance Settings
WORKSPACE_MAX_BANDWIDTH=10000000  # 10 Mbps
WORKSPACE_TARGET_FPS=30
WORKSPACE_ADAPTIVE_QUALITY=true
```

### Docker Service Configuration
```yaml
services:
  novnc:
    image: novnc/novnc:latest
    container_name: onyx-novnc
    ports:
      - "6080:6080"
    environment:
      - NOVNC_PORT=${NOVNC_PORT}
      - NOVNC_RESOLUTION=${NOVNC_RESOLUTION}
      - NOVNC_QUALITY=${NOVNC_QUALITY}
    volumes:
      - ./workspace:/workspace
    networks:
      - onyx-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Testing Strategy

### Unit Tests
- **Workspace Component**: React component rendering and state management
- **Connection Management**: WebSocket connection lifecycle and error handling
- **Quality Adjustment**: Adaptive streaming quality logic
- **Mobile Optimization**: Touch gesture recognition and mobile controls

### Integration Tests
- **End-to-End Connection**: Full workspace connection from UI to noVNC server
- **Multi-Device Support**: Workspace functionality across desktop, tablet, and mobile
- **Performance Testing**: Latency and frame rate validation under different conditions
- **Security Testing**: Authentication and authorization validation

### Performance Tests
- **Latency Testing**: Measure and validate sub-500ms response times
- **Bandwidth Testing**: Test adaptive quality under varying network conditions
- **Load Testing**: Multiple concurrent workspace sessions
- **Mobile Performance**: Battery usage and memory consumption on mobile devices

### Accessibility Tests
- **Screen Reader**: Workspace navigation and control with screen readers
- **Keyboard Navigation**: Full functionality via keyboard only
- **Touch Accessibility**: Touch controls for users with motor impairments
- **Color Contrast**: UI elements meet WCAG AA contrast requirements

## Success Metrics

### Performance Metrics
- **Connection Success Rate**: >99% successful workspace connections
- **Latency Compliance**: 95% of interactions under 500ms
- **Frame Rate Consistency**: 30fps maintained 90% of session time
- **Mobile Performance**: <5% battery drain per hour of active use

### User Experience Metrics
- **Session Duration**: Average 30+ minutes per workspace session
- **Feature Adoption**: 80% of users using workspace features within first week
- **User Satisfaction**: NPS score above 70 for workspace experience
- **Error Rate**: <1% workspace session failures

### Technical Metrics
- **Resource Usage**: <2GB additional RAM for workspace services
- **Network Efficiency**: Adaptive quality reducing bandwidth by 40% on mobile
- **Reliability**: 99.5% workspace service uptime
- **Scalability**: Support for 5 concurrent workspace sessions

## Dependencies

### Internal Dependencies
- **Epic 1**: Foundation infrastructure for Docker and service orchestration
- **Epic 2**: Chat interface integration and UI framework
- **Story 5.1**: Agent mode toggle for workspace interaction modes

### External Dependencies
- **noVNC**: VNC client library for web-based workspace access
- **React**: Frontend framework for workspace UI components
- **WebSocket**: Real-time communication protocol for workspace streaming
- **Docker**: Container platform for noVNC service deployment

## Risk Assessment

### Technical Risks
- **Performance Issues**: High-resolution streaming may impact system performance
  - **Mitigation**: Adaptive compression and quality management
- **Network Reliability**: Workspace requires stable internet connection
  - **Mitigation**: Robust reconnection handling and offline indicators
- **Mobile Compatibility**: Touch interfaces may be challenging for precise control
  - **Mitigation**: Mobile-specific controls and gesture optimization

### User Experience Risks
- **Learning Curve**: Users may need time to adapt to workspace interface
  - **Mitigation**: Progressive disclosure and contextual help system
- **Trust Issues**: Users may be hesitant about remote workspace control
  - **Mitigation**: Transparent operation logging and easy disconnection controls

## Definition of Done

### Code Requirements
- [ ] All acceptance criteria met and tested
- [ ] Code review completed and approved
- [ ] Documentation updated and complete
- [ ] Performance benchmarks met

### Testing Requirements
- [ ] Unit test coverage >90%
- [ ] Integration tests covering all major workflows
- [ ] Performance tests meeting latency and frame rate requirements
- [ ] Accessibility tests meeting WCAG AA standards
- [ ] Mobile device testing completed

### Operational Requirements
- [ ] Monitoring and alerting configured
- [ ] Documentation for troubleshooting and maintenance
- [ ] Deployment scripts validated
- [ ] Rollback procedures documented

### User Experience Requirements
- [ ] Workspace interface intuitive and responsive
- [ ] Mobile experience optimized and functional
- [ ] Performance meets or exceeds targets
- [ ] User acceptance testing passed

## Notes

### Important Considerations
- **Progressive Enhancement**: Start with basic workspace functionality and enhance iteratively
- **Performance First**: Optimize for latency and frame rate above all other features
- **Mobile Priority**: Ensure excellent mobile experience from the beginning
- **Security Focus**: Implement secure authentication and session management

### Future Enhancements
- **Multi-Monitor Support**: Extended workspace across multiple displays
- **Gesture Recognition**: Advanced hand gestures for intuitive control
- **Voice Control**: Voice commands for workspace navigation and control
- **AI Assistance**: Intelligent workspace layout and tool suggestions

---

This story provides the foundation for Epic 8's advanced workspace integration, enabling real-time visualization and interaction with agent operations. The implementation establishes critical infrastructure for human-AI collaboration while maintaining high performance and accessibility standards.

## Dev Agent Record

### Context Reference
<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes List
- noVNC server configuration and deployment architecture defined
- React workspace viewer component specifications created
- Mobile optimization and touch control requirements established
- Performance targets and testing strategy outlined
- Database schema for session management designed
- API endpoints for workspace control specified
- Comprehensive acceptance criteria with measurable success metrics

### File List
**Files to Create:**
- docker-compose.yaml (update for noVNC service)
- suna/src/components/WorkspaceViewer.tsx
- suna/src/hooks/useWorkspaceConnection.ts
- onyx-core/api/workspace/sessions.py
- onyx-core/models/workspace.py

**Files to Modify:**
- suna/src/app/layout.tsx (workspace integration)
- suna/src/styles/globals.css (workspace styling)
- suna/package.json (noVNC client dependency)

## Change Log
**Created:** 2025-11-15
**Status:** drafted
**Last Updated:** 2025-11-15
**Workflow:** BMAD create-story workflow execution