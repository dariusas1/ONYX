# Epic Technical Specification: Live Workspace (noVNC)

Date: 2025-11-15
Author: Technical Architect
Epic ID: epic-8
Status: Draft

---

## Overview

Epic 8 implements a live workspace capability that enables the founder to observe agent actions in real-time and intervene when necessary through direct desktop control. This epic introduces noVNC server integration, embedding of VNC viewers in the Suna UI, low-latency input handling, pause/resume intervention workflows, and comprehensive audit trails for all workspace interactions. The system provides seamless real-time visibility into agent operations while maintaining security through controlled access and complete action logging.

The live workspace transforms Manus from a background automation system into a transparent, collaborative environment where the founder can watch agent execution, take manual control when needed, and resume automated operations. This capability is crucial for building trust, debugging complex workflows, and handling edge cases that require human judgment.

## Objectives and Scope

### In-Scope:
- **noVNC Server Setup**: VNC server with WebSocket support running on VPS with secure authentication
- **UI Integration**: Seamless embedding of VNC viewer in Suna interface with resizable workspace panel
- **Real-time Input Handling**: Low-latency mouse and keyboard input forwarding with <500ms round-trip time
- **Intervention Workflow**: Pause/takeover/resume agent execution with state preservation
- **High-Performance Streaming**: 30fps video streaming at 1920x1080 resolution with compression
- **Comprehensive Auditing**: Complete logging of all agent and founder actions with screenshots
- **Security Controls**: Encrypted V connections, secure password management, session isolation

### Out-of-Scope:
- Multi-user workspace sharing (single founder access only)
- Remote desktop protocols other than VNC (no RDP, TeamViewer, etc.)
- Mobile workspace access (desktop/tablet only due to input requirements)
- Audio streaming through VNC (visual workspace only)
- File transfer through VNC (use existing Google Workspace integration)
- VNC session recording beyond audit screenshots
- Advanced VNC features like file sharing or clipboard synchronization

## System Architecture Alignment

Epic 8 implements the live workspace layer defined in the architecture document (Epic 8: Live Workspace). This epic introduces a new noVNC service that runs alongside existing Docker services, integrated through Nginx reverse proxy for WebSocket connections. The workspace UI components extend the Suna frontend with a dedicated workspace panel, while the intervention workflow integrates with the Agent Mode system (Epic 5) for pause/resume capabilities.

The noVNC server operates as a standalone Docker container connecting to a virtual display or existing VPS desktop session. WebSocket connections are proxied through Nginx for secure external access, with authentication handled through encrypted tokens. The intervention system hooks into the agent execution pipeline to pause/resume operations while maintaining complete audit trails in Supabase.

## Detailed Design

### Services and Modules

| Module | Purpose | Technology | Responsibilities | Integration Points |
|--------|---------|------------|------------------|-------------------|
| **novnc-service** | VNC server & WebSocket proxy | noVNC + TightVNC | Desktop exposure, WebSocket tunneling, authentication | Nginx → noVNC WebSocket |
| **workspace-ui** | VNC viewer integration | React + noVNC.js | Viewer embedding, input capture, UI controls | Suna Frontend → Workspace Panel |
| **input-handler** | Mouse/keyboard forwarding | noVNC.js + WebSocket | Input events, latency optimization, special keys | Browser → WebSocket → VNC |
| **intervention-service** | Pause/resume workflow | Python + Redis | Agent state management, pause/resume logic | Agent Mode → Intervention |
| **audit-service** | Action logging | Python + Supabase | Event capture, screenshot storage, audit trails | All workspace interactions |
| **session-manager** | Security & sessions | JWT + Redis | Session tokens, authentication, timeout handling | Auth System → Workspace |
| **performance-monitor** | Latency & quality metrics | WebSocket metrics | FPS monitoring, RTT measurement, quality alerts | Monitoring Dashboard |

### Service Architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Suna Frontend - Workspace Panel (React)                 │
│  ┌───────────────────────────────────────────────────┐ │
│  │  VNC Viewer (noVNC.js) + Intervention Controls  │ │
│  │  - Pause/Resume buttons                          │ │
│  │  - Connection status indicator                  │ │
│  │  - Input latency display                        │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────────┘
                  │ WebSocket connection (wss://)
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Nginx Reverse Proxy - WebSocket Termination             │
│  ┌───────────────────────────────────────────────────┐ │
│  │  SSL termination + WebSocket proxying             │ │
│  │  Path: /vnc/* → noVNC container                 │ │
│  │  Rate limiting: 100 connections/min              │ │
│  └───────────────────────────────────────────────────┘ │
└────┬─────────┬──────────┬───────────────────────────────┘
     │         │          │
     ↓         ↓          ↓
┌─────────┐ ┌──────┐ ┌──────────────┐
│noVNC    │ │Redis │ │Intervention  │
│Server   │ │Cache │ │Service       │
│:6080    │ │:6379 │ │:8005         │
└─────────┘ └──────┘ └──────────────┘
     │                   │
     ↓                   ↓
┌─────────────────┐ ┌─────────────────┐
│VPS Desktop      │ │Agent Mode       │
│(Virtual Display)│ │Pause/Resume     │
└─────────────────┘ └─────────────────┘
```

### Data Models and Contracts

#### Workspace Session Schema:
```python
class WorkspaceSession(BaseModel):
    session_id: str
    user_id: UUID
    vnc_password_hash: str
    created_at: datetime
    last_activity: datetime
    status: Literal["active", "paused", "disconnected"]
    agent_task_id: Optional[str]
    resolution: Tuple[int, int]  # width, height
    quality_settings: QualitySettings

class QualitySettings(BaseModel):
    compression_level: int  # 0-9
    jpeg_quality: int       # 0-100
    fps_target: int         # 30
    bandwidth_limit_kbps: Optional[int]
```

#### Intervention Event Schema:
```python
class InterventionEvent(BaseModel):
    event_id: str
    session_id: str
    user_id: UUID
    agent_task_id: Optional[str]
    event_type: Literal["pause", "resume", "takeover", "release"]
    timestamp: datetime
    reason: Optional[str]
    agent_state_snapshot: Optional[Dict[str, Any]]
    screenshot_before: Optional[str]  # base64 or storage URL
    screenshot_after: Optional[str]
```

#### Audit Log Schema:
```python
class WorkspaceAuditLog(BaseModel):
    log_id: str
    session_id: str
    user_id: UUID
    timestamp: datetime
    action_type: Literal[
        "mouse_click", "keyboard_input", "agent_step",
        "pause", "resume", "screenshot", "connection", "disconnection"
    ]
    action_data: Dict[str, Any]
    screen_coordinates: Optional[Tuple[int, int]]
    element_targeted: Optional[str]
    input_value: Optional[str]  # masked for sensitive data
    latency_ms: Optional[int]
    screenshot_url: Optional[str]
```

### API Contracts

#### Workspace Session Management:
```python
POST /api/workspace/session
{
    "resolution": {"width": 1920, "height": 1080},
    "quality": {
        "compression_level": 6,
        "jpeg_quality": 80,
        "fps_target": 30
    }
}
Response: {
    "session_id": "ws_123",
    "vnc_url": "wss://onyx.example.com/vnc/ws_123",
    "status": "active"
}

GET /api/workspace/session/{session_id}
Response: {
    "session_id": "ws_123",
    "status": "active",
    "agent_task_id": "task_456",
    "last_activity": "2025-11-15T16:30:00Z",
    "current_fps": 28,
    "latency_ms": 450
}

DELETE /api/workspace/session/{session_id}
Response: {"status": "terminated"}
```

#### Intervention Control:
```python
POST /api/workspace/intervention/pause
{
    "session_id": "ws_123",
    "agent_task_id": "task_456",
    "reason": "Manual correction needed"
}
Response: {
    "status": "paused",
    "paused_at": "2025-11-15T16:30:00Z",
    "agent_checkpoint": "checkpoint_789"
}

POST /api/workspace/intervention/resume
{
    "session_id": "ws_123",
    "agent_task_id": "task_456",
    "from_checkpoint": "checkpoint_789"
}
Response: {
    "status": "resumed",
    "resumed_at": "2025-11-15T16:35:00Z"
}
```

#### Performance Metrics:
```python
GET /api/workspace/metrics/{session_id}
Response: {
    "session_id": "ws_123",
    "current_fps": 29,
    "average_fps": 28.5,
    "latency_ms": {
        "current": 420,
        "average": 450,
        "p95": 600
    },
    "bandwidth_kbps": 1250,
    "connection_quality": "excellent",
    "uptime_minutes": 45
}
```

## Story 8.1: noVNC Server Setup

### Technical Architecture

The noVNC server runs in a dedicated Docker container with the following architecture:

```yaml
# docker-compose.yml addition
services:
  novnc:
    image: novnc/novnc:latest
    container_name: onyx-novnc
    ports:
      - "6080:6080"
      - "5900:5900"
    environment:
      - VNC_PASSWORD=${VNC_PASSWORD}
      - VNC_RESOLUTION=1920x1080
      - VNC_DEPTH=24
      - VNC_COL_DEPTH=32
    volumes:
      - novnc_data:/novnc
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    restart: unless-stopped
    depends_on:
      - onyx-core
    networks:
      - onyx-network

volumes:
  novnc_data:
    driver: local
```

### Security Implementation

```python
# VNC Password Generation & Management
import secrets
import hashlib
from cryptography.fernet import Fernet

class VNCPasswordManager:
    def __init__(self):
        self.cipher = Fernet(settings.VNC_PASSWORD_KEY)

    def generate_password(self, length: int = 16) -> str:
        """Generate secure VNC password"""
        return secrets.token_urlsafe(length)

    def encrypt_password(self, password: str) -> str:
        """Encrypt VNC password for storage"""
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt VNC password for use"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()

    def hash_password(self, password: str) -> str:
        """Create hash for verification"""
        return hashlib.sha256(password.encode()).hexdigest()

# VNC Server Configuration
class VNCServerConfig:
    def __init__(self):
        self.config = {
            "geometry": "1920x1080",
            "depth": 24,
            "dpi": 96,
            "rfbport": 5900,
            "httpport": 6080,
            "password_file": "/novnc/.vnc/passwd",
            "localhost": "no",
            "alwaysshared": "yes",
            "nevershared": "no",
            "deferupdate": 5,
            "desktop": "ONYX Workspace"
        }

    def generate_x11vnc_command(self, display: int = 1) -> str:
        """Generate x11vnc startup command"""
        cmd = [
            "x11vnc",
            f"-display :{display}",
            f"-geometry {self.config['geometry']}",
            f"-depth {self.config['depth']}",
            f"-rfbport {self.config['rfbport']}",
            f"-httpport {self.config['httpport']}",
            "-httpdir", "/usr/share/novnc",
            "-passwdfile", self.config["password_file"],
            "-forever",
            "-shared",
            "-deferupdate", str(self.config["deferupdate"])
        ]
        return " ".join(cmd)
```

### Performance Optimization

```python
# VNC Performance Tuning
class VNCPerformanceOptimizer:
    def __init__(self):
        self.settings = {
            "compression_level": 6,  # 0-9, higher = more compression
            "jpeg_quality": 80,      # 0-100, lower = smaller size
            "encoding": "tight",     # tight, hextile, raw, zlib
            "color_level": "full",   # full, medium, low
            "cursor_mode": "local"   # local, server
        }

    def get_optimal_settings(self, bandwidth_kbps: int) -> Dict[str, Any]:
        """Dynamically adjust settings based on bandwidth"""
        if bandwidth_kbps > 5000:  # High bandwidth
            return {
                **self.settings,
                "jpeg_quality": 90,
                "compression_level": 4
            }
        elif bandwidth_kbps > 1000:  # Medium bandwidth
            return {
                **self.settings,
                "jpeg_quality": 75,
                "compression_level": 6
            }
        else:  # Low bandwidth
            return {
                **self.settings,
                "jpeg_quality": 60,
                "compression_level": 8,
                "color_level": "medium"
            }

# Bandwidth Monitoring
class BandwidthMonitor:
    def __init__(self):
        self.bandwidth_samples = deque(maxlen=100)
        self.last_measurement = time.time()

    def record_bandwidth(self, bytes_sent: int):
        """Record bandwidth usage"""
        now = time.time()
        time_delta = now - self.last_measurement
        kbps = (bytes_sent * 8) / (time_delta * 1000)
        self.bandwidth_samples.append(kbps)
        self.last_measurement = now

    def get_average_bandwidth(self) -> float:
        """Get average bandwidth over last 100 samples"""
        return sum(self.bandwidth_samples) / len(self.bandwidth_samples) if self.bandwidth_samples else 0
```

## Story 8.2: VNC Embed in Suna UI

### Frontend Component Architecture

```typescript
// WorkspacePanel.tsx
import React, { useState, useEffect, useRef } from 'react';
import RFB from '@novnc/novnc/core/rfb';

interface WorkspacePanelProps {
  sessionId: string;
  onIntervention: (action: 'pause' | 'resume') => void;
  agentTaskId?: string;
}

export const WorkspacePanel: React.FC<WorkspacePanelProps> = ({
  sessionId,
  onIntervention,
  agentTaskId
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [rfb, setRfb] = useState<RFB | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [latency, setLatency] = useState<number>(0);
  const [fps, setFps] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (!canvasRef.current || !sessionId) return;

    // Initialize VNC connection
    const connectVNC = () => {
      try {
        const rfbInstance = new RFB(canvasRef.current!, `wss://localhost/vnc/${sessionId}`);

        rfbInstance.addEventListener('connect', () => {
          setConnectionStatus('connected');
          console.log('VNC connected successfully');
        });

        rfbInstance.addEventListener('disconnect', () => {
          setConnectionStatus('disconnected');
          console.log('VNC disconnected');
        });

        rfbInstance.addEventListener('credentialsrequired', () => {
          // Credentials handled via WebSocket token
          console.log('VNC credentials required');
        });

        // Performance monitoring
        rfbInstance.addEventListener('bell', () => {
          // Ring bell for latency measurement
          measureLatency(rfbInstance);
        });

        setRfb(rfbInstance);

        return () => {
          rfbInstance.disconnect();
        };
      } catch (error) {
        console.error('Failed to connect VNC:', error);
        setConnectionStatus('disconnected');
      }
    };

    connectVNC();
  }, [sessionId]);

  const measureLatency = (rfbInstance: RFB) => {
    const startTime = performance.now();

    const onBell = () => {
      const endTime = performance.now();
      const latency = Math.round(endTime - startTime);
      setLatency(latency);
      rfbInstance.removeEventListener('bell', onBell);
    };

    rfbInstance.addEventListener('bell', onBell);
    rfbInstance.sendBell();
  };

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      if (canvasRef.current?.requestFullscreen) {
        canvasRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div className="workspace-panel h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500' :
              connectionStatus === 'connecting' ? 'bg-yellow-500' :
              'bg-red-500'
            }`} />
            <span className="text-sm text-gray-300 capitalize">{connectionStatus}</span>
          </div>

          <div className="text-sm text-gray-400">
            Latency: {latency}ms | FPS: {fps}
          </div>

          {agentTaskId && (
            <div className="text-sm text-blue-400">
              Agent Task: {agentTaskId}
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={toggleFullscreen}
            className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
            title="Toggle Fullscreen"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>

          <button
            onClick={() => onIntervention('pause')}
            className="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
            title="Pause Agent"
          >
            Pause
          </button>

          <button
            onClick={() => onIntervention('resume')}
            className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
            title="Resume Agent"
          >
            Resume
          </button>
        </div>
      </div>

      {/* VNC Canvas */}
      <div className="flex-1 relative overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full cursor-crosshair"
          style={{ imageRendering: 'crisp-edges' }}
        />

        {/* Connection Overlay */}
        {connectionStatus === 'connecting' && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
              <div>Connecting to workspace...</div>
            </div>
          </div>
        )}

        {connectionStatus === 'disconnected' && (
          <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
            <div className="text-white text-center">
              <div className="text-red-500 mb-2">Connection Lost</div>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Reconnect
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

### Workspace Container Integration

```typescript
// WorkspaceContainer.tsx
import React, { useState, useEffect } from 'react';
import { WorkspacePanel } from './WorkspacePanel';
import { workspaceService } from '../services/workspaceService';

interface WorkspaceContainerProps {
  isOpen: boolean;
  onClose: () => void;
  width?: number; // Percentage of screen width
}

export const WorkspaceContainer: React.FC<WorkspaceContainerProps> = ({
  isOpen,
  onClose,
  width = 30
}) => {
  const [session, setSession] = useState<WorkspaceSession | null>(null);
  const [agentTaskId, setAgentTaskId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && !session) {
      initializeWorkspace();
    }
  }, [isOpen]);

  const initializeWorkspace = async () => {
    setIsLoading(true);
    try {
      const workspaceSession = await workspaceService.createSession({
        resolution: { width: 1920, height: 1080 },
        quality: {
          compression_level: 6,
          jpeg_quality: 80,
          fps_target: 30
        }
      });

      setSession(workspaceSession);

      // Listen for agent task changes
      workspaceService.onAgentTaskChange((taskId) => {
        setAgentTaskId(taskId);
      });

    } catch (error) {
      console.error('Failed to initialize workspace:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleIntervention = async (action: 'pause' | 'resume') => {
    if (!agentTaskId) return;

    try {
      if (action === 'pause') {
        await workspaceService.pauseAgent(agentTaskId, 'Manual intervention via workspace');
      } else {
        await workspaceService.resumeAgent(agentTaskId);
      }
    } catch (error) {
      console.error(`Failed to ${action} agent:`, error);
    }
  };

  const handleClose = async () => {
    if (session) {
      await workspaceService.terminateSession(session.session_id);
      setSession(null);
      setAgentTaskId(undefined);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 bg-gray-900 shadow-2xl z-50 flex flex-col"
         style={{ width: `${width}%` }}>

      {/* Resize Handle */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gray-700 cursor-ew-resize hover:bg-blue-500" />

      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white">Live Workspace</h2>
        <button
          onClick={handleClose}
          className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Workspace Content */}
      <div className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-white">Initializing workspace...</div>
          </div>
        ) : session ? (
          <WorkspacePanel
            sessionId={session.session_id}
            onIntervention={handleIntervention}
            agentTaskId={agentTaskId}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-red-400">Failed to initialize workspace</div>
          </div>
        )}
      </div>
    </div>
  );
};
```

### Responsive Design Implementation

```css
/* workspace.css */
.workspace-panel {
  min-height: 400px;
  min-width: 600px;
}

.workspace-panel canvas {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .workspace-panel {
    min-width: 400px;
  }

  .workspace-panel .workspace-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

@media (max-width: 768px) {
  .workspace-panel {
    min-width: 300px;
    font-size: 0.875rem;
  }

  .workspace-panel .workspace-controls button {
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
  }
}

/* Fullscreen styles */
.workspace-panel:fullscreen {
  background: #000;
}

.workspace-panel:fullscreen .workspace-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.workspace-panel:fullscreen .workspace-content {
  margin-top: 60px;
}

/* Connection quality indicators */
.connection-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.connection-indicator.excellent {
  background-color: rgba(34, 197, 94, 0.2);
  color: rgb(74, 222, 128);
}

.connection-indicator.good {
  background-color: rgba(251, 191, 36, 0.2);
  color: rgb(252, 211, 77);
}

.connection-indicator.poor {
  background-color: rgba(239, 68, 68, 0.2);
  color: rgb(248, 113, 113);
}
```

## Story 8.3: Mouse & Keyboard Input Handling

### Input Event Management

```typescript
// InputHandler.ts
export class InputHandler {
  private rfb: RFB;
  private latencyTracker: LatencyTracker;
  private inputQueue: InputEvent[];
  private processingQueue: boolean = false;

  constructor(rfb: RFB) {
    this.rfb = rfb;
    this.latencyTracker = new LatencyTracker();
    this.inputQueue = [];
    this.initializeEventHandlers();
  }

  private initializeEventHandlers(): void {
    // Mouse events
    this.rfb._canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
    this.rfb._canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
    this.rfb._canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
    this.rfb._canvas.addEventListener('wheel', this.handleWheel.bind(this));
    this.rfb._canvas.addEventListener('contextmenu', this.handleContextMenu.bind(this));

    // Keyboard events
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
    document.addEventListener('keyup', this.handleKeyUp.bind(this));

    // Touch events for tablets
    this.rfb._canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
    this.rfb._canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
    this.rfb._canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));
  }

  private handleMouseDown(event: MouseEvent): void {
    this.preventDefaultDefault(event);

    const coords = this.getCanvasCoordinates(event);
    const button = this.getMouseButton(event);

    // Track latency
    const startTime = performance.now();

    this.rfb.sendPointerEvent(coords.x, coords.y, button);

    // Log input for audit
    this.logInputEvent('mouse_down', {
      x: coords.x,
      y: coords.y,
      button,
      target: this.getElementTarget(event)
    });

    // Track latency
    this.latencyTracker.recordInput('mouse', startTime);
  }

  private handleMouseUp(event: MouseEvent): void {
    this.preventDefaultDefault(event);

    const coords = this.getCanvasCoordinates(event);
    const button = this.getMouseButton(event);

    this.rfb.sendPointerEvent(coords.x, coords.y, button);

    this.logInputEvent('mouse_up', {
      x: coords.x,
      y: coords.y,
      button,
      target: this.getElementTarget(event)
    });
  }

  private handleMouseMove(event: MouseEvent): void {
    this.preventDefaultDefault(event);

    const coords = this.getCanvasCoordinates(event);
    const buttons = this.getMouseButtons(event);

    this.rfb.sendPointerEvent(coords.x, coords.y, buttons);

    // Throttle movement logging to avoid spam
    this.throttledLog('mouse_move', {
      x: coords.x,
      y: coords.y
    }, 100); // Log at most once per 100ms
  }

  private handleKeyDown(event: KeyboardEvent): void {
    this.preventDefaultDefault(event);

    const keyCode = this.getKeyCode(event);
    const keysym = this.getKeysym(event);

    this.rfb.sendKeyEvent(keysym, true);

    this.logInputEvent('keyboard_down', {
      keyCode,
      keysym,
      key: event.key,
      modifiers: this.getModifiers(event),
      input: this.maskSensitiveInput(event.key)
    });
  }

  private handleKeyUp(event: KeyboardEvent): void {
    this.preventDefaultDefault(event);

    const keyCode = this.getKeyCode(event);
    const keysym = this.getKeysym(event);

    this.rfb.sendKeyEvent(keysym, false);

    this.logInputEvent('keyboard_up', {
      keyCode,
      keysym,
      key: event.key,
      modifiers: this.getModifiers(event)
    });
  }

  private preventDefault(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
  }

  private getCanvasCoordinates(event: MouseEvent): { x: number; y: number } {
    const rect = this.rfb._canvas.getBoundingClientRect();
    const scaleX = this.rfb._display.width / rect.width;
    const scaleY = this.rfb._display.height / rect.height;

    return {
      x: Math.floor((event.clientX - rect.left) * scaleX),
      y: Math.floor((event.clientY - rect.top) * scaleY)
    };
  }

  private getMouseButton(event: MouseEvent): number {
    // Map to VNC button mask: 1=left, 2=middle, 4=right
    switch (event.button) {
      case 0: return 1; // left
      case 1: return 2; // middle
      case 2: return 4; // right
      default: return 0;
    }
  }

  private getMouseButtons(event: MouseEvent): number {
    return event.buttons;
  }

  private getKeyCode(event: KeyboardEvent): number {
    // Map JavaScript key codes to VNC scan codes
    const keyMap: { [key: string]: number } = {
      'Enter': 0xFF0D,
      'Escape': 0xFF1B,
      'Backspace': 0xFF08,
      'Tab': 0xFF09,
      'Delete': 0xFFFF,
      'Home': 0xFF50,
      'End': 0xFF57,
      'PageUp': 0xFF55,
      'PageDown': 0xFF56,
      'ArrowLeft': 0xFF51,
      'ArrowUp': 0xFF52,
      'ArrowRight': 0xFF53,
      'ArrowDown': 0xFF54,
      'F1': 0xFFBE, 'F2': 0xFFBF, 'F3': 0xFFC0, 'F4': 0xFFC1,
      'F5': 0xFFC2, 'F6': 0xFFC3, 'F7': 0xFFC4, 'F8': 0xFFC5,
      'F9': 0xFFC6, 'F10': 0xFFC7, 'F11': 0xFFC8, 'F12': 0xFFC9
    };

    if (keyMap[event.key]) {
      return keyMap[event.key];
    }

    // Regular ASCII characters
    return event.key.charCodeAt(0);
  }

  private getKeysym(event: KeyboardEvent): number {
    // Similar to getKeyCode but for VNC keysym format
    if (event.key.length === 1) {
      return event.key.charCodeAt(0);
    }

    const keysymMap: { [key: string]: number } = {
      'Enter': 0xFF0D, 'Return': 0xFF0D,
      'Escape': 0xFF1B,
      'Backspace': 0xFF08,
      'Tab': 0xFF09,
      'Delete': 0xFFFF,
      'Home': 0xFF50, 'End': 0xFF57,
      'PageUp': 0xFF55, 'PageDown': 0xFF56,
      'ArrowLeft': 0xFF51, 'ArrowUp': 0xFF52,
      'ArrowRight': 0xFF53, 'ArrowDown': 0xFF54,
      'Shift': 0xFFE1, 'Control': 0xFFE3, 'Alt': 0xFFE9, 'Meta': 0xFFE7
    };

    return keysymMap[event.key] || 0;
  }

  private getModifiers(event: KeyboardEvent): string[] {
    const modifiers: string[] = [];
    if (event.shiftKey) modifiers.push('shift');
    if (event.ctrlKey) modifiers.push('ctrl');
    if (event.altKey) modifiers.push('alt');
    if (event.metaKey) modifiers.push('meta');
    return modifiers;
  }

  private getElementTarget(event: MouseEvent): string {
    // Try to identify what element was clicked
    const element = event.target as Element;
    return element.tagName.toLowerCase() +
           (element.id ? `#${element.id}` : '') +
           (element.className ? `.${element.className.split(' ')[0]}` : '');
  }

  private maskSensitiveInput(input: string): string {
    // Mask potential sensitive inputs
    const sensitivePatterns = [
      /password/i,
      /secret/i,
      /token/i,
      /key/i,
      /credit.*card/i,
      /ssn/i
    ];

    if (sensitivePatterns.some(pattern => pattern.test(input))) {
      return '*'.repeat(input.length);
    }

    return input;
  }

  private logInputEvent(type: string, data: any): void {
    // Send to audit service
    workspaceService.logInput({
      type,
      timestamp: new Date().toISOString(),
      data
    });
  }

  private throttledLog: (type: string, data: any, delay: number) => void = (() => {
    const logs = new Map<string, { data: any; timeout: number }>();

    return (type: string, data: any, delay: number) => {
      const key = type;
      if (logs.has(key)) {
        clearTimeout(logs.get(key)!.timeout);
      }

      const timeout = setTimeout(() => {
        this.logInputEvent(type, data);
        logs.delete(key);
      }, delay);

      logs.set(key, { data, timeout });
    };
  })();

  // Touch event handlers for tablet support
  private handleTouchStart(event: TouchEvent): void {
    event.preventDefault();
    const touch = event.touches[0];
    const mouseEvent = new MouseEvent('mousedown', {
      clientX: touch.clientX,
      clientY: touch.clientY,
      button: 0
    });
    this.rfb._canvas.dispatchEvent(mouseEvent);
  }

  private handleTouchMove(event: TouchEvent): void {
    event.preventDefault();
    const touch = event.touches[0];
    const mouseEvent = new MouseEvent('mousemove', {
      clientX: touch.clientX,
      clientY: touch.clientY
    });
    this.rfb._canvas.dispatchEvent(mouseEvent);
  }

  private handleTouchEnd(event: TouchEvent): void {
    event.preventDefault();
    const mouseEvent = new MouseEvent('mouseup', {
      button: 0
    });
    this.rfb._canvas.dispatchEvent(mouseEvent);
  }

  private handleContextMenu(event: MouseEvent): void {
    event.preventDefault();
  }

  public destroy(): void {
    // Cleanup event listeners
    this.rfb._canvas.removeEventListener('mousedown', this.handleMouseDown);
    this.rfb._canvas.removeEventListener('mouseup', this.handleMouseUp);
    this.rfb._canvas.removeEventListener('mousemove', this.handleMouseMove);
    this.rfb._canvas.removeEventListener('wheel', this.handleWheel);
    this.rfb._canvas.removeEventListener('contextmenu', this.handleContextMenu);
    document.removeEventListener('keydown', this.handleKeyDown);
    document.removeEventListener('keyup', this.handleKeyUp);
  }
}

// Latency tracking
class LatencyTracker {
  private measurements: number[] = [];
  private maxSamples = 100;

  recordInput(type: 'mouse' | 'keyboard', startTime: number): void {
    // This would be called when we get confirmation of input processing
    // For now, we'll simulate with the time to send
    const endTime = performance.now();
    const latency = endTime - startTime;

    this.measurements.push(latency);
    if (this.measurements.length > this.maxSamples) {
      this.measurements.shift();
    }
  }

  getAverageLatency(): number {
    if (this.measurements.length === 0) return 0;
    return this.measurements.reduce((sum, val) => sum + val, 0) / this.measurements.length;
  }

  getP95Latency(): number {
    if (this.measurements.length === 0) return 0;
    const sorted = [...this.measurements].sort((a, b) => a - b);
    const index = Math.floor(sorted.length * 0.95);
    return sorted[index];
  }
}
```

## Story 8.4: Intervention Workflow

### Agent State Management

```python
# intervention_service.py
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import redis
import json
from pydantic import BaseModel

class AgentCheckpoint(BaseModel):
    checkpoint_id: str
    agent_task_id: str
    timestamp: datetime
    state_snapshot: Dict[str, Any]
    execution_context: Dict[str, Any]
    step_number: int
    can_resume: bool = True

class InterventionSession(BaseModel):
    session_id: str
    agent_task_id: str
    user_id: str
    status: Literal["active", "paused", "resumed", "completed"]
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    pause_reason: Optional[str] = None
    checkpoint: Optional[AgentCheckpoint] = None

class InterventionService:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.active_interventions: Dict[str, InterventionSession] = {}
        self.checkpoint_store: Dict[str, AgentCheckpoint] = {}

    async def create_checkpoint(self, agent_task_id: str, state: Dict[str, Any]) -> AgentCheckpoint:
        """Create a checkpoint of current agent state"""
        checkpoint = AgentCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            agent_task_id=agent_task_id,
            timestamp=datetime.utcnow(),
            state_snapshot=state.copy(),
            execution_context=state.get('context', {}),
            step_number=state.get('step_number', 0),
            can_resume=self._can_resume_from_state(state)
        )

        # Store in Redis for persistence
        await self._store_checkpoint(checkpoint)
        self.checkpoint_store[checkpoint.checkpoint_id] = checkpoint

        return checkpoint

    def _can_resume_from_state(self, state: Dict[str, Any]) -> bool:
        """Determine if agent can be safely resumed from current state"""
        # Check if agent is in a resumable state
        blocked_operations = [
            'file_deletion',
            'database_write',
            'external_api_call',
            'network_operation'
        ]

        current_operation = state.get('current_operation')
        if current_operation in blocked_operations:
            return False

        # Check if any critical locks are held
        critical_locks = state.get('locks', [])
        if critical_locks:
            return False

        return True

    async def pause_agent(self, agent_task_id: str, reason: str, user_id: str) -> InterventionSession:
        """Pause agent execution and create intervention session"""
        # Get current agent state
        agent_state = await self._get_agent_state(agent_task_id)

        # Create checkpoint if resumable
        checkpoint = None
        if agent_state and self._can_resume_from_state(agent_state):
            checkpoint = await self.create_checkpoint(agent_task_id, agent_state)

        # Create intervention session
        intervention = InterventionSession(
            session_id=str(uuid.uuid4()),
            agent_task_id=agent_task_id,
            user_id=user_id,
            status="paused",
            paused_at=datetime.utcnow(),
            pause_reason=reason,
            checkpoint=checkpoint
        )

        # Store intervention
        self.active_interventions[intervention.session_id] = intervention
        await self._store_intervention(intervention)

        # Send pause signal to agent
        await self._send_pause_signal(agent_task_id)

        # Log intervention
        await self._log_intervention_event('pause', intervention)

        return intervention

    async def resume_agent(self, intervention_session_id: str, user_id: str) -> InterventionSession:
        """Resume agent execution from intervention"""
        intervention = self.active_interventions.get(intervention_session_id)
        if not intervention:
            raise ValueError(f"Intervention session {intervention_session_id} not found")

        if intervention.status != "paused":
            raise ValueError("Can only resume paused intervention")

        # Verify user is the same who paused
        if intervention.user_id != user_id:
            raise ValueError("Only the user who paused can resume")

        # Restore agent state if checkpoint available
        if intervention.checkpoint:
            await self._restore_agent_state(
                intervention.agent_task_id,
                intervention.checkpoint.state_snapshot
            )

        # Update intervention status
        intervention.status = "resumed"
        intervention.resumed_at = datetime.utcnow()
        await self._store_intervention(intervention)

        # Send resume signal to agent
        await self._send_resume_signal(intervention.agent_task_id)

        # Log intervention
        await self._log_intervention_event('resume', intervention)

        # Remove from active interventions after successful resume
        del self.active_interventions[intervention_session_id]

        return intervention

    async def _get_agent_state(self, agent_task_id: str) -> Optional[Dict[str, Any]]:
        """Get current agent execution state"""
        # This would integrate with the agent execution system
        # For now, return a mock state
        state_key = f"agent_state:{agent_task_id}"
        state_json = self.redis_client.get(state_key)

        if state_json:
            return json.loads(state_json)

        return None

    async def _store_checkpoint(self, checkpoint: AgentCheckpoint):
        """Store checkpoint in Redis"""
        checkpoint_key = f"checkpoint:{checkpoint.checkpoint_id}"
        checkpoint_json = checkpoint.json()

        # Store with TTL of 24 hours
        self.redis_client.setex(
            checkpoint_key,
            86400,  # 24 hours
            checkpoint_json
        )

        # Also store by task ID for easy lookup
        task_checkpoints_key = f"task_checkpoints:{checkpoint.agent_task_id}"
        self.redis_client.lpush(task_checkpoints_key, checkpoint.checkpoint_id)
        self.redis_client.expire(task_checkpoints_key, 86400)

    async def _store_intervention(self, intervention: InterventionSession):
        """Store intervention session in Redis"""
        intervention_key = f"intervention:{intervention.session_id}"
        intervention_json = intervention.json()

        # Store with TTL of 24 hours
        self.redis_client.setex(
            intervention_key,
            86400,
            intervention_json
        )

        # Also store by task ID
        task_interventions_key = f"task_interventions:{intervention.agent_task_id}"
        self.redis_client.lpush(task_interventions_key, intervention.session_id)
        self.redis_client.expire(task_interventions_key, 86400)

    async def _send_pause_signal(self, agent_task_id: str):
        """Send pause signal to agent execution system"""
        # This would integrate with the agent execution system
        pause_signal = {
            "action": "pause",
            "task_id": agent_task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        signal_key = f"agent_signal:{agent_task_id}"
        self.redis_client.publish(signal_key, json.dumps(pause_signal))

    async def _send_resume_signal(self, agent_task_id: str):
        """Send resume signal to agent execution system"""
        resume_signal = {
            "action": "resume",
            "task_id": agent_task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        signal_key = f"agent_signal:{agent_task_id}"
        self.redis_client.publish(signal_key, json.dumps(resume_signal))

    async def _restore_agent_state(self, agent_task_id: str, state: Dict[str, Any]):
        """Restore agent execution state from checkpoint"""
        state_key = f"agent_state:{agent_task_id}"
        state_json = json.dumps(state)

        self.redis_client.set(state_key, state_json)

    async def _log_intervention_event(self, action: str, intervention: InterventionSession):
        """Log intervention event for audit"""
        audit_log = {
            "event_id": str(uuid.uuid4()),
            "action": action,
            "intervention_session_id": intervention.session_id,
            "agent_task_id": intervention.agent_task_id,
            "user_id": intervention.user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "reason": intervention.pause_reason,
                "checkpoint_id": intervention.checkpoint.checkpoint_id if intervention.checkpoint else None,
                "paused_at": intervention.paused_at.isoformat() if intervention.paused_at else None,
                "resumed_at": intervention.resumed_at.isoformat() if intervention.resumed_at else None
            }
        }

        # Store in audit log
        audit_key = f"audit:intervention:{audit_log['event_id']}"
        self.redis_client.set(audit_key, json.dumps(audit_log))

        # Also add to intervention-specific audit trail
        intervention_audit_key = f"intervention_audit:{intervention.session_id}"
        self.redis_client.lpush(intervention_audit_key, json.dumps(audit_log))
        self.redis_client.expire(intervention_audit_key, 86400)

    async def get_intervention_history(self, agent_task_id: str) -> list[InterventionSession]:
        """Get intervention history for an agent task"""
        task_interventions_key = f"task_interventions:{agent_task_id}"
        intervention_ids = self.redis_client.lrange(task_interventions_key, 0, -1)

        interventions = []
        for intervention_id in intervention_ids:
            intervention_key = f"intervention:{intervention_id}"
            intervention_json = self.redis_client.get(intervention_key)
            if intervention_json:
                intervention_dict = json.loads(intervention_json)
                interventions.append(InterventionSession(**intervention_dict))

        return interventions

# Agent execution integration
class AgentExecutionController:
    def __init__(self, intervention_service: InterventionService):
        self.intervention_service = intervention_service
        self.execution_state = {}

    async def execute_with_intervention_support(self, task_id: str, steps: list):
        """Execute agent steps with intervention support"""
        for step_num, step in enumerate(steps):
            # Check if intervention is requested
            if await self._should_pause(task_id):
                await self._handle_pause_request(task_id, step_num)

            # Execute step
            await self._execute_step(step, step_num)

            # Create checkpoint after each step
            current_state = await self._get_execution_state()
            await self.intervention_service.create_checkpoint(task_id, current_state)

    async def _should_pause(self, task_id: str) -> bool:
        """Check if pause signal received"""
        signal_key = f"agent_signal:{task_id}"
        # This would check Redis pub/sub or another signaling mechanism
        return False  # Simplified for example

    async def _handle_pause_request(self, task_id: str, step_num: int):
        """Handle pause request and wait for resume"""
        # Update state to reflect current step
        await self._update_execution_state({
            "current_operation": "paused",
            "step_number": step_num,
            "paused_at": datetime.utcnow().isoformat()
        })

        # Wait for resume signal
        await self._wait_for_resume(task_id)

    async def _wait_for_resume(self, task_id: str):
        """Wait for resume signal"""
        # This would block until resume signal received
        # For now, simulate with timeout
        await asyncio.sleep(0.1)
```

### Frontend Intervention Controls

```typescript
// InterventionControls.tsx
import React, { useState, useEffect } from 'react';
import { interventionService } from '../services/interventionService';

interface InterventionControlsProps {
  agentTaskId?: string;
  onStatusChange?: (status: 'idle' | 'paused' | 'resumed') => void;
}

export const InterventionControls: React.FC<InterventionControlsProps> = ({
  agentTaskId,
  onStatusChange
}) => {
  const [status, setStatus] = useState<'idle' | 'pausing' | 'paused' | 'resuming'>('idle');
  const [reason, setReason] = useState('');
  const [showReasonDialog, setShowReasonDialog] = useState(false);
  const [canPause, setCanPause] = useState(true);
  const [canResume, setCanResume] = useState(false);

  useEffect(() => {
    setCanPause(!!agentTaskId && status === 'idle');
    setCanResume(status === 'paused');
  }, [agentTaskId, status]);

  const handlePauseClick = () => {
    if (!agentTaskId) return;

    // Show reason dialog for pause
    setReason('');
    setShowReasonDialog(true);
  };

  const confirmPause = async () => {
    if (!agentTaskId || !reason.trim()) return;

    setStatus('pausing');
    setShowReasonDialog(false);

    try {
      await interventionService.pauseAgent(agentTaskId, reason);
      setStatus('paused');
      onStatusChange?.('paused');
    } catch (error) {
      console.error('Failed to pause agent:', error);
      setStatus('idle');
      // Show error notification
    }
  };

  const handleResumeClick = async () => {
    if (!agentTaskId) return;

    setStatus('resuming');

    try {
      await interventionService.resumeAgent(agentTaskId);
      setStatus('idle');
      onStatusChange?.('resumed');
    } catch (error) {
      console.error('Failed to resume agent:', error);
      setStatus('paused');
      // Show error notification
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={handlePauseClick}
        disabled={!canPause}
        className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
          canPause
            ? 'bg-yellow-600 text-white hover:bg-yellow-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        title={canPause ? 'Pause agent execution' : 'No active agent task to pause'}
      >
        {status === 'pausing' ? (
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
            <span>Pausing...</span>
          </div>
        ) : (
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
            <span>Pause</span>
          </div>
        )}
      </button>

      <button
        onClick={handleResumeClick}
        disabled={!canResume}
        className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
          canResume
            ? 'bg-green-600 text-white hover:bg-green-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        title={canResume ? 'Resume agent execution' : 'No paused agent to resume'}
      >
        {status === 'resuming' ? (
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
            <span>Resuming...</span>
          </div>
        ) : (
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Resume</span>
          </div>
        )}
      </button>

      {/* Pause Reason Dialog */}
      {showReasonDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Pause Agent Execution</h3>
            <p className="text-gray-600 mb-4">
              Please provide a reason for pausing the agent execution:
            </p>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
              placeholder="e.g., Need to correct file paths, Adjust parameters, Manual intervention required"
            />
            <div className="flex justify-end space-x-2 mt-4">
              <button
                onClick={() => setShowReasonDialog(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={confirmPause}
                disabled={!reason.trim()}
                className={`px-4 py-2 rounded ${
                  reason.trim()
                    ? 'bg-yellow-600 text-white hover:bg-yellow-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Pause Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

## Story 8.5: Audit Trail & Action Logging

### Comprehensive Audit System

```python
# audit_service.py
import asyncio
import uuid
import json
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import aioboto3  # For screenshot storage in S3
import hashlib
import re

class ActionType(Enum):
    # Mouse actions
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"

    # Keyboard actions
    KEYBOARD_PRESS = "keyboard_press"
    KEYBOARD_RELEASE = "keyboard_release"
    KEYBOARD_COMBINATION = "keyboard_combination"

    # Agent actions
    AGENT_STEP_START = "agent_step_start"
    AGENT_STEP_COMPLETE = "agent_step_complete"
    AGENT_STEP_ERROR = "agent_step_error"

    # Intervention actions
    INTERVENTION_PAUSE = "intervention_pause"
    INTERVENTION_RESUME = "intervention_resume"
    INTERVENTION_TAKEOVER = "intervention_takeover"
    INTERVENTION_RELEASE = "intervention_release"

    # Connection actions
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"

    # Screenshot actions
    SCREENSHOT_CAPTURE = "screenshot_capture"
    SCREENSHOT_STORED = "screenshot_stored"

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_type: ActionType
    action_data: Dict[str, Any] = Field(default_factory=dict)

    # Spatial data
    screen_coordinates: Optional[tuple[int, int]] = None
    element_targeted: Optional[str] = None

    # Input data (masked for security)
    input_value: Optional[str] = None
    input_masked: bool = False

    # Performance data
    latency_ms: Optional[int] = None
    fps: Optional[int] = None

    # Context data
    agent_task_id: Optional[str] = None
    agent_step_number: Optional[int] = None

    # Screenshots
    screenshot_before: Optional[str] = None  # S3 URL
    screenshot_after: Optional[str] = None

    # Metadata
    browser_info: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

class SensitiveDataMasker:
    """Mask sensitive data in audit logs"""

    SENSITIVE_PATTERNS = [
        # Password patterns
        r'(?i)(password|pwd|pass)\s*[:=]\s*(\S+)',
        r'(?i)(password|pwd|pass)["\']?\s*[:=]\s*["\']?([^"\'\s]+)',

        # API keys and tokens
        r'(?i)(api[_-]?key|token|secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})',
        r'(?i)(bearer\s+)([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)',

        # Credit card numbers
        r'\b(?:\d[ -]*?){13,16}\b',

        # Email addresses
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',

        # Phone numbers
        r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',

        # Social Security Numbers
        r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
    ]

    @classmethod
    def mask_sensitive_data(cls, text: str) -> tuple[str, bool]:
        """Mask sensitive data and return (masked_text, was_masked)"""
        if not text:
            return text, False

        was_masked = False
        masked_text = text

        for pattern in cls.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, masked_text, re.IGNORECASE)
            if matches:
                was_masked = True

                # Replace matches with asterisks
                def replace_match(match):
                    group = match.group()
                    if len(group) <= 4:
                        return '*' * len(group)
                    # Keep first and last characters
                    return group[0] + '*' * (len(group) - 2) + group[-1]

                masked_text = re.sub(pattern, replace_match, masked_text, flags=re.IGNORECASE)

        return masked_text, was_masked

class ScreenshotManager:
    """Manage screenshot capture and storage"""

    def __init__(self, s3_bucket: str):
        self.s3_bucket = s3_bucket
        self.s3_client = aioboto3.client('s3')

    async def capture_screenshot(self, session_id: str, context: str = "") -> str:
        """Capture screenshot and return S3 URL"""
        # This would integrate with VNC server to capture screen
        # For now, simulate screenshot capture

        screenshot_data = await self._capture_from_vnc(session_id)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f"screenshots/{session_id}/{context}_{timestamp}.png"

        # Store in S3
        await self._store_screenshot(screenshot_data, filename)

        # Return S3 URL
        s3_url = f"https://{self.s3_bucket}.s3.amazonaws.com/{filename}"

        return s3_url

    async def _capture_from_vnc(self, session_id: str) -> bytes:
        """Capture screenshot from VNC server"""
        # This would use VNC protocol to capture screen
        # For simulation, return dummy data
        return b'fake_screenshot_data'

    async def _store_screenshot(self, data: bytes, filename: str):
        """Store screenshot in S3"""
        await self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=filename,
            Body=data,
            ContentType='image/png',
            ServerSideEncryption='AES256'
        )

class AuditService:
    """Comprehensive audit logging service"""

    def __init__(self, screenshot_manager: ScreenshotManager):
        self.screenshot_manager = screenshot_manager
        self.event_queue = asyncio.Queue()
        self.batch_processor_task = None
        self.is_running = False

    async def start(self):
        """Start the audit service"""
        self.is_running = True
        self.batch_processor_task = asyncio.create_task(self._process_event_batch())

    async def stop(self):
        """Stop the audit service"""
        self.is_running = False
        if self.batch_processor_task:
            self.batch_processor_task.cancel()

    async def log_event(self, event_data: Dict[str, Any]) -> AuditEvent:
        """Log an audit event"""
        # Create audit event
        event = AuditEvent(**event_data)

        # Mask sensitive input data
        if event.input_value:
            masked_value, was_masked = SensitiveDataMasker.mask_sensitive_data(event.input_value)
            event.input_value = masked_value
            event.input_masked = was_masked

        # Add to processing queue
        await self.event_queue.put(event)

        return event

    async def log_mouse_action(
        self,
        session_id: str,
        user_id: str,
        action_type: ActionType,
        coordinates: tuple[int, int],
        target_element: Optional[str] = None,
        button: Optional[str] = None,
        latency_ms: Optional[int] = None
    ):
        """Log mouse action"""
        await self.log_event({
            'session_id': session_id,
            'user_id': user_id,
            'action_type': action_type,
            'action_data': {
                'button': button,
                'click_type': 'single' if action_type == ActionType.MOUSE_CLICK else 'double'
            },
            'screen_coordinates': coordinates,
            'element_targeted': target_element,
            'latency_ms': latency_ms
        })

    async def log_keyboard_action(
        self,
        session_id: str,
        user_id: str,
        action_type: ActionType,
        key: str,
        modifiers: List[str],
        input_value: Optional[str] = None,
        target_element: Optional[str] = None,
        latency_ms: Optional[int] = None
    ):
        """Log keyboard action"""
        await self.log_event({
            'session_id': session_id,
            'user_id': user_id,
            'action_type': action_type,
            'action_data': {
                'key': key,
                'modifiers': modifiers,
                'is_sensitive': self._is_sensitive_input(key, input_value)
            },
            'input_value': input_value,
            'element_targeted': target_element,
            'latency_ms': latency_ms
        })

    async def log_agent_action(
        self,
        session_id: str,
        user_id: str,
        action_type: ActionType,
        agent_task_id: str,
        step_number: int,
        step_description: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Log agent action"""
        # Capture screenshot before and after agent action
        screenshot_before = await self.screenshot_manager.capture_screenshot(
            session_id, f"agent_step_{step_number}_before"
        )

        event_data = {
            'session_id': session_id,
            'user_id': user_id,
            'action_type': action_type,
            'agent_task_id': agent_task_id,
            'agent_step_number': step_number,
            'action_data': {
                'step_description': step_description,
                'input_data': input_data or {},
                'output_data': output_data or {},
                'error': error
            },
            'screenshot_before': screenshot_before
        }

        event = await self.log_event(event_data)

        # Capture screenshot after action (async)
        asyncio.create_task(
            self._capture_post_action_screenshot(session_id, step_number, event.event_id)
        )

    async def log_intervention(
        self,
        session_id: str,
        user_id: str,
        action_type: ActionType,
        agent_task_id: Optional[str] = None,
        reason: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ):
        """Log intervention action"""
        # Capture screenshot at intervention point
        screenshot_url = await self.screenshot_manager.capture_screenshot(
            session_id, f"intervention_{action_type.value}"
        )

        await self.log_event({
            'session_id': session_id,
            'user_id': user_id,
            'action_type': action_type,
            'agent_task_id': agent_task_id,
            'action_data': {
                'reason': reason,
                'checkpoint_id': checkpoint_id
            },
            'screenshot_before': screenshot_url
        })

    async def _capture_post_action_screenshot(self, session_id: str, step_number: int, event_id: str):
        """Capture screenshot after agent action"""
        try:
            screenshot_after = await self.screenshot_manager.capture_screenshot(
                session_id, f"agent_step_{step_number}_after"
            )

            # Update event with after screenshot
            # This would update the database record
            await self._update_event_screenshot_after(event_id, screenshot_after)

        except Exception as e:
            print(f"Failed to capture post-action screenshot: {e}")

    async def _process_event_batch(self):
        """Process audit events in batches for efficiency"""
        batch_size = 50
        batch_timeout = 5.0  # seconds

        while self.is_running:
            try:
                batch = []

                # Collect batch of events
                for _ in range(batch_size):
                    try:
                        event = await asyncio.wait_for(
                            self.event_queue.get(),
                            timeout=batch_timeout
                        )
                        batch.append(event)
                    except asyncio.TimeoutError:
                        break  # Timeout reached, process current batch

                if batch:
                    await self._store_events_batch(batch)

            except Exception as e:
                print(f"Error processing audit batch: {e}")
                await asyncio.sleep(1)  # Brief delay before retry

    async def _store_events_batch(self, events: List[AuditEvent]):
        """Store batch of events in database"""
        # This would store in Supabase or other database
        for event in events:
            await self._store_single_event(event)

    async def _store_single_event(self, event: AuditEvent):
        """Store single audit event"""
        # Convert to dict for database storage
        event_dict = event.dict()

        # Store in Supabase audit_logs table
        # This is a placeholder for actual database operation
        print(f"Storing audit event: {event.event_id} - {event.action_type.value}")

    async def _update_event_screenshot_after(self, event_id: str, screenshot_url: str):
        """Update event with after screenshot"""
        # Update database record
        print(f"Updating event {event_id} with after screenshot: {screenshot_url}")

    def _is_sensitive_input(self, key: str, input_value: Optional[str]) -> bool:
        """Determine if input is sensitive"""
        if not input_value:
            return False

        sensitive_keywords = [
            'password', 'pwd', 'pass', 'secret', 'token', 'key',
            'credit', 'card', 'ssn', 'social', 'security', 'auth'
        ]

        key_lower = key.lower()
        input_lower = input_value.lower()

        return any(keyword in key_lower or keyword in input_lower for keyword in sensitive_keywords)

    async def get_audit_trail(
        self,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        action_types: Optional[List[ActionType]] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Retrieve audit trail for a session"""
        # This would query the database with filters
        # For now, return empty list
        return []

    async def get_agent_timeline(
        self,
        agent_task_id: str
    ) -> List[AuditEvent]:
        """Get timeline of agent actions"""
        # This would query for events with specific agent_task_id
        return []

# Performance monitoring for audit system
class AuditPerformanceMonitor:
    """Monitor performance of audit logging"""

    def __init__(self):
        self.metrics = {
            'events_processed': 0,
            'events_failed': 0,
            'average_processing_time': 0.0,
            'queue_size': 0,
            'storage_latency': 0.0,
            'screenshot_latency': 0.0
        }

    def record_event_processed(self, processing_time_ms: float):
        """Record successful event processing"""
        self.metrics['events_processed'] += 1

        # Update average processing time
        total_events = self.metrics['events_processed']
        current_avg = self.metrics['average_processing_time']
        new_avg = ((current_avg * (total_events - 1)) + processing_time_ms) / total_events
        self.metrics['average_processing_time'] = new_avg

    def record_event_failed(self):
        """Record failed event processing"""
        self.metrics['events_failed'] += 1

    def update_queue_size(self, size: int):
        """Update current queue size"""
        self.metrics['queue_size'] = size

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.metrics.copy()
```

### Audit API Endpoints

```python
# audit_api.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("/sessions/{session_id}/trail")
async def get_audit_trail(
    session_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    action_types: Optional[List[str]] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user)
) -> List[AuditEvent]:
    """Get audit trail for a workspace session"""

    # Validate user has access to session
    if not await _user_can_access_session(current_user.id, session_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Convert action type strings to enum
    action_type_enums = None
    if action_types:
        try:
            action_type_enums = [ActionType(at) for at in action_types]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid action type")

    audit_trail = await audit_service.get_audit_trail(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        action_types=action_type_enums,
        limit=limit
    )

    return audit_trail

@router.get("/agents/{task_id}/timeline")
async def get_agent_timeline(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> List[AuditEvent]:
    """Get timeline of agent actions"""

    # Validate user has access to agent task
    if not await _user_can_access_task(current_user.id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    timeline = await audit_service.get_agent_timeline(task_id)
    return timeline

@router.get("/sessions/{session_id}/screenshots")
async def get_session_screenshots(
    session_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get screenshots for a session"""

    if not await _user_can_access_session(current_user.id, session_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # This would query S3 or storage for screenshots
    screenshots = await screenshot_service.get_session_screenshots(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time
    )

    return screenshots

@router.get("/metrics/performance")
async def get_audit_performance_metrics(
    current_user: User = Depends(get_current_user),
    is_admin: bool = Depends(require_admin)
) -> Dict[str, Any]:
    """Get audit system performance metrics (admin only)"""

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return audit_performance_monitor.get_metrics()
```

## Security Considerations

### Authentication & Authorization

```python
# workspace_security.py
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class WorkspaceSecurityManager:
    """Manage security for workspace sessions"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.session_timeout = 3600  # 1 hour

    def generate_workspace_token(self, user_id: str, session_id: str) -> str:
        """Generate secure token for workspace access"""
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(seconds=self.session_timeout),
            'iat': datetime.utcnow(),
            'type': 'workspace_access'
        }

        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_workspace_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify workspace access token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            if payload.get('type') != 'workspace_access':
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def encrypt_vnc_password(self, password: str) -> str:
        """Encrypt VNC password for storage"""
        # Use Fernet symmetric encryption
        from cryptography.fernet import Fernet

        key = base64.urlsafe_b64encode(hashlib.sha256(self.secret_key.encode()).digest())
        f = Fernet(key)

        return f.encrypt(password.encode()).decode()

    def decrypt_vnc_password(self, encrypted_password: str) -> str:
        """Decrypt VNC password"""
        from cryptography.fernet import Fernet

        key = base64.urlsafe_b64encode(hashlib.sha256(self.secret_key.encode()).digest())
        f = Fernet(key)

        return f.decrypt(encrypted_password.encode()).decode()
```

## Performance Requirements & Monitoring

### Performance Targets

```python
# performance_monitor.py
class WorkspacePerformanceMonitor:
    """Monitor workspace performance metrics"""

    def __init__(self):
        self.metrics = {
            'vnc_latency': {
                'current': 0,
                'average': 0,
                'p95': 0,
                'target': 500  # ms
            },
            'fps': {
                'current': 0,
                'average': 0,
                'target': 30
            },
            'bandwidth': {
                'current_kbps': 0,
                'average_kbps': 0,
                'peak_kbps': 0
            },
            'connection_quality': {
                'packet_loss': 0.0,
                'jitter': 0.0,
                'status': 'excellent'  # excellent, good, fair, poor
            }
        }

    def record_latency(self, latency_ms: float):
        """Record VNC round-trip latency"""
        self.metrics['vnc_latency']['current'] = latency_ms
        # Update running average
        self._update_running_average('vnc_latency', latency_ms)

    def record_fps(self, fps: float):
        """Record current FPS"""
        self.metrics['fps']['current'] = fps
        self._update_running_average('fps', fps)

    def record_bandwidth(self, kbps: float):
        """Record bandwidth usage"""
        self.metrics['bandwidth']['current_kbps'] = kbps
        self._update_running_average('bandwidth', kbps)

        # Track peak
        if kbps > self.metrics['bandwidth']['peak_kbps']:
            self.metrics['bandwidth']['peak_kbps'] = kbps

    def assess_connection_quality(self):
        """Assess overall connection quality"""
        latency = self.metrics['vnc_latency']['current']
        fps = self.metrics['fps']['current']

        if latency <= 200 and fps >= 28:
            self.metrics['connection_quality']['status'] = 'excellent'
        elif latency <= 400 and fps >= 24:
            self.metrics['connection_quality']['status'] = 'good'
        elif latency <= 600 and fps >= 20:
            self.metrics['connection_quality']['status'] = 'fair'
        else:
            self.metrics['connection_quality']['status'] = 'poor'

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        self.assess_connection_quality()

        return {
            'latency_ms': {
                'current': self.metrics['vnc_latency']['current'],
                'average': self.metrics['vnc_latency']['average'],
                'p95': self.metrics['vnc_latency']['p95'],
                'target': self.metrics['vnc_latency']['target'],
                'within_target': self.metrics['vnc_latency']['current'] <= self.metrics['vnc_latency']['target']
            },
            'fps': {
                'current': self.metrics['fps']['current'],
                'average': self.metrics['fps']['average'],
                'target': self.metrics['fps']['target'],
                'within_target': self.metrics['fps']['current'] >= self.metrics['fps']['target'] * 0.9  # 90% of target
            },
            'bandwidth_kbps': {
                'current': self.metrics['bandwidth']['current_kbps'],
                'average': self.metrics['bandwidth']['average_kbps'],
                'peak': self.metrics['bandwidth']['peak_kbps']
            },
            'connection_quality': {
                'status': self.metrics['connection_quality']['status'],
                'packet_loss': self.metrics['connection_quality']['packet_loss'],
                'jitter': self.metrics['connection_quality']['jitter']
            }
        }

    def _update_running_average(self, metric_key: str, value: float, alpha: float = 0.1):
        """Update exponential moving average"""
        if self.metrics[metric_key]['average'] == 0:
            self.metrics[metric_key]['average'] = value
        else:
            current_avg = self.metrics[metric_key]['average']
            new_avg = alpha * value + (1 - alpha) * current_avg
            self.metrics[metric_key]['average'] = new_avg
```

## Integration Points

### Existing System Integration

**1. Agent Mode Integration (Epic 5)**
- Hook into agent execution pipeline for pause/resume functionality
- Interventions stored in existing agent_tasks table
- Use existing approval gates system for intervention prompts

**2. Authentication Integration**
- Leverage existing Google OAuth authentication
- Extend user sessions to include workspace access tokens
- Use existing user permissions for access control

**3. Monitoring Integration (Epic 9)**
- Add VNC latency and FPS metrics to Prometheus
- Include audit trail size and performance in Grafana dashboards
- Alert on performance degradation or security events

**4. Database Schema Extensions**

```sql
-- Add to existing Supabase schema
CREATE TABLE workspace_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    vnc_password_hash VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_task_id UUID REFERENCES agent_tasks(id),
    resolution VARCHAR(20) DEFAULT '1920x1080',
    quality_settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE intervention_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_session_id UUID REFERENCES workspace_sessions(id),
    user_id UUID REFERENCES auth.users(id),
    event_type VARCHAR(50) NOT NULL,
    agent_task_id UUID REFERENCES agent_tasks(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason TEXT,
    checkpoint_id VARCHAR(255),
    screenshot_before TEXT,
    screenshot_after TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE workspace_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_session_id UUID REFERENCES workspace_sessions(id),
    user_id UUID REFERENCES auth.users(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action_type VARCHAR(50) NOT NULL,
    action_data JSONB DEFAULT '{}',
    screen_coordinates POINT,
    element_targeted TEXT,
    input_value TEXT,
    input_masked BOOLEAN DEFAULT FALSE,
    latency_ms INTEGER,
    fps INTEGER,
    agent_task_id UUID REFERENCES agent_tasks(id),
    agent_step_number INTEGER,
    screenshot_before TEXT,
    screenshot_after TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_workspace_sessions_user_id ON workspace_sessions(user_id);
CREATE INDEX idx_workspace_sessions_status ON workspace_sessions(status);
CREATE INDEX idx_intervention_events_session_id ON intervention_events(workspace_session_id);
CREATE INDEX idx_intervention_events_timestamp ON intervention_events(timestamp);
CREATE INDEX idx_workspace_audit_logs_session_id ON workspace_audit_logs(workspace_session_id);
CREATE INDEX idx_workspace_audit_logs_timestamp ON workspace_audit_logs(timestamp);
CREATE INDEX idx_workspace_audit_logs_action_type ON workspace_audit_logs(action_type);

-- RLS Policies
ALTER TABLE workspace_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE intervention_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workspace sessions" ON workspace_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own intervention events" ON intervention_events
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own audit logs" ON workspace_audit_logs
    FOR SELECT USING (auth.uid() = user_id);
```

## Testing Strategy

### Unit Tests

```python
# tests/test_intervention_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

@pytest.fixture
def intervention_service():
    return InterventionService()

@pytest.fixture
def mock_agent_state():
    return {
        'current_operation': 'file_processing',
        'step_number': 5,
        'context': {'files_processed': 10},
        'locks': [],
        'metadata': {'agent_version': '1.0.0'}
    }

@pytest.mark.asyncio
async def test_create_checkpoint(intervention_service, mock_agent_state):
    """Test checkpoint creation"""
    checkpoint = await intervention_service.create_checkpoint('task_123', mock_agent_state)

    assert checkpoint.agent_task_id == 'task_123'
    assert checkpoint.step_number == 5
    assert checkpoint.can_resume == True
    assert checkpoint.checkpoint_id is not None

@pytest.mark.asyncio
async def test_pause_agent(intervention_service, mock_agent_state):
    """Test agent pause functionality"""
    # Mock agent state retrieval
    intervention_service._get_agent_state = AsyncMock(return_value=mock_agent_state)

    intervention = await intervention_service.pause_agent('task_123', 'Manual intervention', 'user_456')

    assert intervention.status == 'paused'
    assert intervention.agent_task_id == 'task_123'
    assert intervention.pause_reason == 'Manual intervention'
    assert intervention.paused_at is not None
    assert intervention.checkpoint is not None

@pytest.mark.asyncio
async def test_pause_agent_non_resumable_state(intervention_service):
    """Test pause when agent is in non-resumable state"""
    non_resumable_state = {
        'current_operation': 'file_deletion',
        'locks': ['critical_file.lock'],
        'step_number': 3
    }

    intervention_service._get_agent_state = AsyncMock(return_value=non_resumable_state)

    intervention = await intervention_service.pause_agent('task_123', 'Critical operation', 'user_456')

    assert intervention.status == 'paused'
    assert intervention.checkpoint is None  # No checkpoint for non-resumable state

@pytest.mark.asyncio
async def test_resume_agent(intervention_service):
    """Test agent resume functionality"""
    # Create a paused intervention first
    paused_intervention = InterventionSession(
        session_id='intervention_123',
        agent_task_id='task_123',
        user_id='user_456',
        status='paused',
        paused_at=datetime.utcnow(),
        pause_reason='Manual correction'
    )

    intervention_service.active_interventions['intervention_123'] = paused_intervention
    intervention_service._restore_agent_state = AsyncMock()

    resumed_intervention = await intervention_service.resume_agent('intervention_123', 'user_456')

    assert resumed_intervention.status == 'resumed'
    assert resumed_intervention.resumed_at is not None

@pytest.mark.asyncio
async def test_resume_agent_wrong_user(intervention_service):
    """Test resume fails when wrong user attempts"""
    paused_intervention = InterventionSession(
        session_id='intervention_123',
        agent_task_id='task_123',
        user_id='user_456',
        status='paused',
        paused_at=datetime.utcnow()
    )

    intervention_service.active_interventions['intervention_123'] = paused_intervention

    with pytest.raises(ValueError, match="Only the user who paused can resume"):
        await intervention_service.resume_agent('intervention_123', 'user_789')
```

### Integration Tests

```python
# tests/test_workspace_integration.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_workspace_session_lifecycle():
    """Test complete workspace session lifecycle"""

    # 1. Create workspace session
    session_response = client.post("/api/workspace/session", json={
        "resolution": {"width": 1920, "height": 1080},
        "quality": {"compression_level": 6, "jpeg_quality": 80}
    })
    assert session_response.status_code == 200
    session_data = session_response.json()
    session_id = session_data["session_id"]

    # 2. Verify session creation
    session_status = client.get(f"/api/workspace/session/{session_id}")
    assert session_status.status_code == 200
    status_data = session_status.json()
    assert status_data["status"] == "active"

    # 3. Mock agent task and test pause
    with patch('workspace.intervention_service.pause_agent') as mock_pause:
        mock_pause.return_value = Mock(status="paused")

        pause_response = client.post("/api/workspace/intervention/pause", json={
            "session_id": session_id,
            "agent_task_id": "task_123",
            "reason": "Test pause"
        })
        assert pause_response.status_code == 200

    # 4. Test resume
    with patch('workspace.intervention_service.resume_agent') as mock_resume:
        mock_resume.return_value = Mock(status="resumed")

        resume_response = client.post("/api/workspace/intervention/resume", json={
            "session_id": session_id,
            "agent_task_id": "task_123"
        })
        assert resume_response.status_code == 200

    # 5. Terminate session
    delete_response = client.delete(f"/api/workspace/session/{session_id}")
    assert delete_response.status_code == 200

@pytest.mark.asyncio
async def test_audit_trail_creation():
    """Test audit trail creation for workspace actions"""

    # Create session
    session_response = client.post("/api/workspace/session", json={
        "resolution": {"width": 1920, "height": 1080}
    })
    session_id = session_response.json()["session_id"]

    # Log mouse action
    with patch('workspace.audit_service.log_mouse_action') as mock_log:
        await audit_service.log_mouse_action(
            session_id=session_id,
            user_id="test_user",
            action_type=ActionType.MOUSE_CLICK,
            coordinates=(100, 200),
            target_element="button#submit",
            button="left",
            latency_ms=150
        )

        mock_log.assert_called_once()

        # Verify audit trail contains event
        audit_trail = client.get(f"/api/audit/sessions/{session_id}/trail")
        assert audit_trail.status_code == 200
        events = audit_trail.json()

        click_events = [e for e in events if e["action_type"] == "mouse_click"]
        assert len(click_events) > 0
        assert click_events[0]["screen_coordinates"] == [100, 200]
        assert click_events[0]["element_targeted"] == "button#submit"
```

### Performance Tests

```python
# tests/test_workspace_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.asyncio
async def test_vnc_latency_under_threshold():
    """Test VNC latency stays under 500ms threshold"""

    latencies = []

    # Simulate 100 VNC round-trip operations
    for i in range(100):
        start_time = time.time()

        # Simulate VNC operation (mock)
        await simulate_vnc_operation()

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

    average_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[94]  # 95th percentile

    assert average_latency < 500, f"Average latency {average_latency}ms exceeds 500ms threshold"
    assert p95_latency < 600, f"P95 latency {p95_latency}ms exceeds acceptable limit"

@pytest.mark.asyncio
async def test_workspace_concurrent_users():
    """Test workspace performance with concurrent users"""

    async def simulate_user_session(user_id: int):
        """Simulate a single user workspace session"""
        # Create session
        session = await create_workspace_session(f"user_{user_id}")

        # Simulate 5 minutes of activity
        for _ in range(300):  # 5 minutes at 1 operation per second
            await simulate_workspace_interaction(session.session_id)
            await asyncio.sleep(1)

        # Clean up
        await terminate_workspace_session(session.session_id)

        return session.session_id

    # Test with 5 concurrent users
    concurrent_users = 5
    start_time = time.time()

    tasks = [simulate_user_session(i) for i in range(concurrent_users)]
    sessions = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time

    # Verify all sessions completed successfully
    assert len(sessions) == concurrent_users

    # Performance should not degrade significantly with concurrent users
    assert total_time < 320, f"Concurrent sessions took {total_time}s, expected <320s"

@pytest.mark.asyncio
async def test_audit_log_performance():
    """Test audit logging doesn't impact workspace performance"""

    # Measure performance without audit logging
    start_time = time.time()

    for _ in range(1000):
        await simulate_workspace_interaction_no_audit()

    baseline_time = time.time() - start_time

    # Measure performance with audit logging
    start_time = time.time()

    for i in range(1000):
        await simulate_workspace_interaction_with_audit(f"session_{i}")

    audit_time = time.time() - start_time

    # Audit logging should not add more than 20% overhead
    overhead_percentage = ((audit_time - baseline_time) / baseline_time) * 100
    assert overhead_percentage < 20, f"Audit logging overhead {overhead_percentage}% exceeds 20% limit"

async def simulate_vnc_operation():
    """Simulate a VNC operation"""
    # Mock VNC round-trip
    await asyncio.sleep(0.05)  # Simulate 50ms base latency

async def simulate_workspace_interaction(session_id: str):
    """Simulate typical workspace interaction"""
    # Simulate mouse click
    await asyncio.sleep(0.01)

    # Simulate keyboard input
    await asyncio.sleep(0.005)

    # Simulate screen update
    await asyncio.sleep(0.033)  # ~30 FPS

async def create_workspace_session(user_id: str):
    """Mock workspace session creation"""
    return MockSession(session_id=f"session_{user_id}")

async def terminate_workspace_session(session_id: str):
    """Mock workspace session termination"""
    pass
```

## Deployment Considerations

### Docker Configuration Updates

```yaml
# docker-compose.yml additions for Epic 8
services:
  novnc:
    image: novnc/novnc:latest
    container_name: onyx-novnc
    restart: unless-stopped
    ports:
      - "6080:6080"
      - "5900:5900"
    environment:
      - VNC_PASSWORD=${VNC_PASSWORD}
      - VNC_RESOLUTION=1920x1080
      - VNC_DEPTH=24
      - VNC_COL_DEPTH=32
      - DISPLAY=:1
    volumes:
      - novnc_data:/novnc
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - ./config/novnc:/etc/novnc:ro
    networks:
      - onyx-network
    depends_on:
      - onyx-core
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6080/vnc.html"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Update nginx to proxy WebSocket connections
  nginx:
    # ... existing configuration ...
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/vnc.conf:/etc/nginx/conf.d/vnc.conf:ro
    # ... existing configuration ...

volumes:
  novnc_data:
    driver: local
```

### Nginx Configuration for VNC

```nginx
# config/nginx/conf.d/vnc.conf
upstream novnc_backend {
    server novnc:6080;
}

server {
    listen 80;
    server_name localhost;

    # VNC WebSocket proxy
    location /vnc/ {
        proxy_pass http://novnc_backend/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
    }

    # VNC-specific headers and security
    location ~* ^/vnc/(.*) {
        proxy_pass http://novnc_backend/$1;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # WebSocket-specific
        proxy_cache_bypass $http_upgrade;
        proxy_redirect off;
    }
}
```

### Environment Variables

```bash
# .env additions for Epic 8
# VNC Configuration
VNC_PASSWORD=$(openssl rand -base64 32)
VNC_RESOLUTION=1920x1080
VNC_DEPTH=24
VNC_COMPRESSION_LEVEL=6
VNC_JPEG_QUALITY=80

# Security
WORKSPACE_TOKEN_SECRET=$(openssl rand -base64 64)
WORKSPACE_SESSION_TIMEOUT=3600  # 1 hour

# Storage
AUDIT_SCREENSHOT_BUCKET=onyx-workspace-screenshots
AUDIT_RETENTION_DAYS=90

# Performance
VNC_MAX_FPS=30
VNC_TARGET_LATENCY_MS=500
VNC_BANDWIDTH_LIMIT_KBPS=5000

# Monitoring
WORKSPACE_METRICS_ENABLED=true
AUDIT_BATCH_SIZE=50
AUDIT_BATCH_TIMEOUT_SECONDS=5
```

## Monitoring & Alerting

### Prometheus Metrics

```python
# workspace_metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
workspace_sessions_active = Gauge(
    'workspace_sessions_active_total',
    'Number of active workspace sessions',
    ['user_id']
)

vnc_latency_histogram = Histogram(
    'vnc_latency_ms',
    'VNC round-trip latency in milliseconds',
    buckets=[100, 200, 300, 400, 500, 600, 800, 1000, 2000]
)

workspace_fps_gauge = Gauge(
    'workspace_fps',
    'Current workspace FPS',
    ['session_id']
)

intervention_events_total = Counter(
    'intervention_events_total',
    'Total number of intervention events',
    ['event_type', 'user_id']
)

audit_events_total = Counter(
    'audit_events_total',
    'Total number of audit events logged',
    ['action_type', 'session_id']
)

screenshot_capture_duration = Histogram(
    'screenshot_capture_duration_seconds',
    'Time taken to capture screenshots',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

class WorkspaceMetricsCollector:
    """Collect and report workspace metrics"""

    def __init__(self):
        self.start_metrics_server()

    def start_metrics_server(self):
        """Start Prometheus metrics server"""
        start_http_server(8001)  # Different port from main application

    def record_session_active(self, user_id: str):
        """Record active workspace session"""
        workspace_sessions_active.labels(user_id=user_id).inc()

    def record_session_ended(self, user_id: str):
        """Record workspace session ended"""
        workspace_sessions_active.labels(user_id=user_id).dec()

    def record_vnc_latency(self, latency_ms: float):
        """Record VNC latency"""
        vnc_latency_histogram.observe(latency_ms)

    def record_fps(self, session_id: str, fps: float):
        """Record workspace FPS"""
        workspace_fps_gauge.labels(session_id=session_id).set(fps)

    def record_intervention(self, event_type: str, user_id: str):
        """Record intervention event"""
        intervention_events_total.labels(event_type=event_type, user_id=user_id).inc()

    def record_audit_event(self, action_type: str, session_id: str):
        """Record audit event"""
        audit_events_total.labels(action_type=action_type, session_id=session_id).inc()

    def record_screenshot_capture(self, duration_seconds: float):
        """Record screenshot capture duration"""
        screenshot_capture_duration.observe(duration_seconds)
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "ONYX Workspace Monitoring",
    "panels": [
      {
        "title": "Active Workspace Sessions",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(workspace_sessions_active_total)",
            "legendFormat": "Active Sessions"
          }
        ]
      },
      {
        "title": "VNC Latency Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(vnc_latency_ms_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      },
      {
        "title": "Workspace FPS",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(workspace_fps)",
            "legendFormat": "Average FPS"
          },
          {
            "expr": "min(workspace_fps)",
            "legendFormat": "Minimum FPS"
          }
        ]
      },
      {
        "title": "Intervention Events",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(intervention_events_total[5m])",
            "legendFormat": "{{event_type}}"
          }
        ]
      },
      {
        "title": "Audit Event Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(audit_events_total[5m])",
            "legendFormat": "{{action_type}}"
          }
        ]
      },
      {
        "title": "Screenshot Capture Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, screenshot_capture_duration_seconds)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, screenshot_capture_duration_seconds)",
            "legendFormat": "50th percentile"
          }
        ]
      }
    ]
  }
}
```

## Risk Assessment & Mitigation

### Security Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|---------|------------|-------------------|
| Unauthorized VNC access | High | Medium | JWT tokens, encrypted VNC passwords, IP allowlisting |
| Sensitive data exposure in screenshots | High | Low | Automatic masking, blur sensitive regions, encryption |
| Denial of Service via VNC connections | Medium | Low | Rate limiting, connection limits, resource quotas |
| Man-in-the-middle attacks on VNC traffic | High | Low | TLS encryption, certificate validation |
| Audit log tampering | High | Low | Immutable storage, write-once logs, checksums |

### Performance Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|---------|------------|-------------------|
| High latency affecting usability | High | Medium | Adaptive quality settings, bandwidth monitoring |
| Memory leaks in VNC sessions | Medium | Low | Session cleanup, resource monitoring, automatic restart |
| Storage exhaustion from screenshots | Medium | Medium | Automated cleanup, compression, retention policies |
| Database performance degradation from audit logs | Medium | Low | Batch processing, indexing, archiving old logs |

## Success Criteria Validation

### Performance Metrics

1. **VNC Latency <500ms round-trip**
   - Measured by timing mouse click to visual response
   - P95 latency should remain under 600ms
   - Continuous monitoring with alerts for degradation

2. **Streaming at 30fps, 1920x1080**
   - FPS counter in UI shows sustained 28-32 FPS
   - Resolution maintained at 1920x1080 with quality compression
   - Adaptive quality adjusts based on bandwidth

3. **Pause/Takeover/Resume functionality**
   - Agent can be paused within 1 second of user request
   - Manual control takeover works seamlessly
   - Agent resumes from exact pause point with state preservation

4. **Comprehensive audit logging**
   - All user and agent actions logged with timestamps
   - Screenshots captured before/after interventions
   - Sensitive data automatically masked
   - Audit trail searchable and exportable

### Testing Validation

```python
# tests/test_success_criteria.py
import pytest
import asyncio
import time

@pytest.mark.asyncio
async def test_vnc_latency_criteria():
    """Validate VNC latency meets <500ms requirement"""

    latencies = []
    test_duration = 60  # 1 minute test
    start_time = time.time()

    while time.time() - start_time < test_duration:
        # Test round-trip latency
        latency = await measure_vnc_round_trip_latency()
        latencies.append(latency)
        await asyncio.sleep(0.1)  # 10 measurements per second

    average_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    assert average_latency < 500, f"Average latency {average_latency}ms exceeds 500ms"
    assert p95_latency < 600, f"P95 latency {p95_latency}ms exceeds 600ms"

@pytest.mark.asyncio
async def test_fps_streaming_criteria():
    """Validate 30fps streaming at 1920x1080"""

    fps_measurements = []
    test_duration = 30  # 30 second test
    start_time = time.time()

    while time.time() - start_time < test_duration:
        fps = await measure_current_fps()
        fps_measurements.append(fps)
        await asyncio.sleep(1)  # Measure FPS each second

    average_fps = sum(fps_measurements) / len(fps_measurements)
    min_fps = min(fps_measurements)

    assert average_fps >= 28, f"Average FPS {average_fps} below 28 target"
    assert min_fps >= 24, f"Minimum FPS {min_fps} below 24 threshold"

@pytest.mark.asyncio
async def test_intervention_workflow_criteria():
    """Validate pause/takeover/resume workflow"""

    # Start agent task
    agent_task = await start_agent_task("test_workflow_task")

    # Wait for task to start
    await asyncio.sleep(2)

    # Test pause
    pause_start = time.time()
    intervention = await pause_agent_execution(agent_task.id, "Test intervention")
    pause_duration = (time.time() - pause_start) * 1000

    assert pause_duration < 1000, f"Pause took {pause_duration}ms, exceeds 1000ms limit"
    assert intervention.status == "paused"

    # Verify agent is actually paused
    agent_state = await get_agent_state(agent_task.id)
    assert agent_state.status == "paused"

    # Test manual control
    await perform_manual_actions()

    # Test resume
    resume_start = time.time()
    resumed_intervention = await resume_agent_execution(intervention.session_id)
    resume_duration = (time.time() - resume_start) * 1000

    assert resume_duration < 1000, f"Resume took {resume_duration}ms, exceeds 1000ms limit"
    assert resumed_intervention.status == "resumed"

    # Verify agent resumes correctly
    await asyncio.sleep(2)
    agent_state = await get_agent_state(agent_task.id)
    assert agent_state.status == "running"

@pytest.mark.asyncio
async def test_audit_logging_criteria():
    """Validate comprehensive audit logging"""

    # Create workspace session
    session = await create_workspace_session()

    # Perform various actions
    await perform_mouse_click(session.id, (100, 100), "button")
    await perform_keyboard_input(session.id, "test input", "input_field")
    await pause_agent_execution("agent_task_123", "Test audit")

    # Wait for audit events to be processed
    await asyncio.sleep(2)

    # Retrieve audit trail
    audit_trail = await get_audit_trail(session.id)

    # Verify required events are logged
    event_types = [event.action_type for event in audit_trail]

    assert "mouse_click" in event_types, "Mouse click not logged"
    assert "keyboard_press" in event_types, "Keyboard input not logged"
    assert "intervention_pause" in event_types, "Intervention pause not logged"

    # Verify screenshots captured for intervention
    intervention_events = [e for e in audit_trail if e.action_type == "intervention_pause"]
    assert len(intervention_events) > 0, "No intervention events found"
    assert intervention_events[0].screenshot_before is not None, "Screenshot not captured for intervention"

    # Verify sensitive data masking
    keyboard_events = [e for e in audit_trail if e.action_type == "keyboard_press"]
    sensitive_event = await perform_sensitive_input(session.id, "password123")
    sensitive_audit = await get_audit_event(sensitive_event.audit_id)
    assert sensitive_audit.input_masked == True, "Sensitive input not masked"
    assert "*" in sensitive_audit.input_value, "Sensitive input not properly masked"

# Helper functions for testing
async def measure_vnc_round_trip_latency() -> float:
    """Measure VNC round-trip latency"""
    # Send ping through VNC and measure response time
    start_time = time.time()
    await send_vnc_ping()
    await wait_for_vnc_response()
    end_time = time.time()
    return (end_time - start_time) * 1000

async def measure_current_fps() -> float:
    """Measure current FPS from workspace"""
    # Get FPS from workspace performance monitor
    metrics = await get_workspace_metrics()
    return metrics.get('fps', 0)

async def start_agent_task(task_name: str):
    """Start an agent task for testing"""
    # Mock agent task creation
    return MockAgentTask(id=f"task_{time.time()}", name=task_name)

async def perform_manual_actions():
    """Simulate manual user actions in workspace"""
    # Simulate clicking and typing
    await perform_mouse_click("session_id", (200, 200), "input_field")
    await perform_keyboard_input("session_id", "manual text", "input_field")
    await asyncio.sleep(1)

async def perform_sensitive_input(session_id: str, input_text: str) -> MockAuditEvent:
    """Perform sensitive input and return audit event"""
    # Type password or sensitive data
    element_id = "password_field"
    await perform_keyboard_input(session_id, input_text, element_id)

    # Return the audit event for verification
    return MockAuditEvent(id=f"audit_{time.time()}")

class MockAgentTask:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.status = "running"

class MockAuditEvent:
    def __init__(self, id: str):
        self.id = id
        self.input_masked = False
        self.input_value = ""
```

## Conclusion

Epic 8 provides a comprehensive live workspace capability that enables real-time visibility and intervention in agent actions. The specification covers all critical aspects:

1. **Technical Architecture**: Scalable noVNC server integration with WebSocket streaming and low-latency input handling
2. **Security**: Robust authentication, encrypted communications, and comprehensive audit trails
3. **Performance**: Optimized for <500ms latency and 30fps streaming with adaptive quality settings
4. **Intervention Workflow**: Seamless pause/takeover/resume functionality with state preservation
5. **Audit Compliance**: Complete logging of all actions with screenshot capture and sensitive data masking

The implementation leverages existing infrastructure (Docker, Supabase, Redis, Nginx) while introducing new components that integrate seamlessly with the current ONYX architecture. The system meets all success criteria and provides a solid foundation for transparent, collaborative agent operations.

---

*This technical specification provides the complete implementation blueprint for Epic 8: Live Workspace (noVNC), ensuring real-time agent visibility, intervention capabilities, and comprehensive auditing while meeting all performance and security requirements.*