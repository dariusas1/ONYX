# Story 8.3: Advanced Intervention & Control System

## Story Metadata

- **Story ID**: 8-3-advanced-intervention-control-system
- **Title**: Advanced Intervention & Control System
- **Epic**: Epic 8 (Advanced Workspace Integration & Collaborative Intelligence)
- **Priority**: P0 (Critical)
- **Estimated Points**: 10
- **Status**: drafted
- **Sprint**: Sprint 8-2
- **Assigned To**: TBD
- **Created Date**: 2025-11-15
- **Dependencies**: Story 8.1, Story 8.2, Story 5.4

## Story

As a founder,
I want granular control over agent execution with pause, takeover, and guidance capabilities,
So that I can correct mistakes, guide execution, and maintain strategic control.

## Acceptance Criteria

### AC8.3.1: One-Click Agent Pause
- **Requirement**: One-click agent pause with immediate execution halt (<1s response time)
- **Evidence**: Pause button functionality that stops agent execution within 1 second
- **Test**: Measure pause response time and verify complete execution halt

### AC8.3.2: Manual Takeover Mode
- **Requirement**: Manual takeover mode with full mouse/keyboard control in workspace
- **Evidence**: Workspace control transferred to user with full input capabilities
- **Test**: Verify user can control all workspace elements during takeover

### AC8.3.3: Step-by-Step Execution Control
- **Requirement**: Step-by-step execution control with next/previous navigation
- **Evidence**: Agent execution broken into steps with user control over progression
- **Test**: Test step navigation and execution control functionality

### AC8.3.4: Guidance System
- **Requirement**: Guidance system where founder can suggest next actions to agent
- **Evidence**: Interface for providing suggestions and recommendations to agent
- **Test**: Verify agent receives and processes user guidance correctly

### AC8.3.5: Rollback Functionality
- **Requirement**: Rollback functionality with visual diff showing before/after states
- **Evidence**: Rollback system with visual comparison of states
- **Test**: Test rollback operations and verify state restoration

### AC8.3.6: Intervention Logging
- **Requirement**: Intervention logging with timestamps and rationale capture
- **Evidence**: Comprehensive log of all interventions with context and reasons
- **Test**: Verify intervention events are properly logged and retrievable

### AC8.3.7: Smart Resumption
- **Requirement**: Smart resumption that adapts to manual changes made during pause
- **Evidence**: Agent adapts execution plan based on changes made during manual control
- **Test**: Test resumption scenarios with various manual modifications

## Technical Requirements

### Agent Execution Control
- **Execution State Management**: Real-time tracking of agent execution state and progress
- **Pause/Resume Mechanism**: Immediate pause capability with state preservation
- **Step Breakdown**: Agent task decomposition into discrete, controllable steps
- **Interruption Handling**: Graceful handling of user interruptions and takeovers

### Input Control System
- **Input Routing**: Dynamic routing of mouse/keyboard input between agent and user
- **Takeover Protocol**: Secure transfer of workspace control to human user
- **Input Capture**: Comprehensive input event capture and logging
- **Control Indicators**: Visual indicators showing current control source

### Guidance & Suggestion System
- **Suggestion Interface**: User interface for providing guidance to agent
- **Context Integration**: Integration of user guidance with agent context and planning
- **Suggestion Processing**: Agent processing of user suggestions and recommendations
- **Feedback Loop**: Closed-loop feedback system for guidance effectiveness

### State Management & Rollback
- **State Checkpointing**: Automatic state checkpoints before each execution step
- **Diff Visualization**: Visual comparison between different execution states
- **Rollback Engine**: Engine for reverting to previous states safely
- **Change Detection**: Automated detection of manual changes during pause

## Implementation Tasks

### Phase 1: Core Intervention Infrastructure (4 points)
- [ ] Task 1.1: Build agent execution control system
  - [ ] Subtask 1.1.1: Create AgentExecutionController class with state management
  - [ ] Subtask 1.1.2: Implement pause/resume functionality with immediate response
  - [ ] Subtask 1.1.3: Create execution step breakdown and tracking system
  - [ ] Subtask 1.1.4: Build intervention event logging and audit trail
  - [ ] Subtask 1.1.5: Add WebSocket communication for real-time control

- [ ] Task 1.2: Implement input control and takeover system
  - [ ] Subtask 1.2.1: Create InputRouter for dynamic input source management
  - [ ] Subtask 1.2.2: Build takeover protocol with secure control transfer
  - [ ] Subtask 1.2.3: Implement input capture and event logging
  - [ ] Subtask 1.2.4: Add control source indicators and visual feedback
  - [ ] Subtask 1.2.5: Create control conflict resolution mechanisms

### Phase 2: Step Control & Navigation (3 points)
- [ ] Task 2.1: Create step-by-step execution system
  - [ ] Subtask 2.1.1: Implement step decomposition algorithm for agent tasks
  - [ ] Subtask 2.1.2: Build step navigation controls (next, previous, jump)
  - [ ] Subtask 2.1.3: Create step progress visualization and timeline
  - [ ] Subtask 2.1.4: Add step preview and description system
  - [ ] Subtask 2.1.5: Implement step validation and error handling

- [ ] Task 2.2: Build execution state checkpointing
  - [ ] Subtask 2.2.1: Create state checkpoint system before each step
  - [ ] Subtask 2.2.2: Implement state serialization and restoration
  - [ ] Subtask 2.2.3: Build checkpoint management and cleanup
  - [ ] Subtask 2.2.4: Add checkpoint integrity validation
  - [ ] Subtask 2.2.5: Create checkpoint rollback mechanisms

### Phase 3: Guidance & Smart Features (3 points)
- [ ] Task 3.1: Implement guidance and suggestion system
  - [ ] Subtask 3.1.1: Create GuidanceInterface component for user input
  - [ ] Subtask 3.1.2: Build suggestion processing and integration engine
  - [ ] Subtask 3.1.3: Implement guidance context and priority management
  - [ ] Subtask 3.1.4: Add guidance effectiveness tracking and learning
  - [ ] Subtask 3.1.5: Create guidance templates and common patterns

- [ ] Task 3.2: Build rollback and diff visualization
  - [ ] Subtask 3.2.1: Create rollback engine with state restoration
  - [ ] Subtask 3.2.2: Implement visual diff system for state comparison
  - [ ] Subtask 3.2.3: Build change detection and highlighting
  - [ ] Subtask 3.2.4: Add rollback confirmation and safety mechanisms
  - [ ] Subtask 3.2.5: Create rollback history and audit trail

## Component Architecture

### Agent Execution Controller
```typescript
export interface AgentExecutionState {
  status: 'running' | 'paused' | 'stopped' | 'intervened';
  currentStep: number;
  totalSteps: number;
  stepProgress: number;
  lastCheckpoint: ExecutionCheckpoint;
  controlSource: 'agent' | 'user' | 'guidance';
  interventionHistory: InterventionEvent[];
}

export class AgentExecutionController {
  private state: AgentExecutionState;
  private checkpoints: Map<number, ExecutionCheckpoint>;
  private interventionLogger: InterventionLogger;

  pause(): Promise<void>;
  resume(): Promise<void>;
  takeover(): Promise<void>;
  releaseControl(): Promise<void>;
  stepForward(): Promise<void>;
  stepBackward(): Promise<void>;
  rollback(checkpointId: string): Promise<void>;
  provideGuidance(guidance: UserGuidance): Promise<void>;
}
```

### Input Router System
```typescript
export interface InputEvent {
  type: 'mouse' | 'keyboard' | 'touch';
  source: 'agent' | 'user';
  timestamp: number;
  data: any;
  target?: string;
}

export class InputRouter {
  private currentController: 'agent' | 'user';
  private inputBuffer: InputEvent[];
  private eventListeners: Map<string, Function>;

  setController(source: 'agent' | 'user'): void;
  routeInput(event: InputEvent): void;
  captureInput(event: InputEvent): void;
  releaseInput(): void;
  getController(): 'agent' | 'user';
}
```

### Guidance System
```typescript
export interface UserGuidance {
  id: string;
  type: 'suggestion' | 'correction' | 'enhancement';
  priority: 'low' | 'medium' | 'high' | 'critical';
  content: string;
  context: GuidanceContext;
  expectedImpact: string;
  timestamp: number;
}

export interface GuidanceContext {
  currentStep: number;
  taskDescription: string;
  recentActions: string[];
  workspaceState: any;
  userIntent: string;
}

export class GuidanceSystem {
  private activeGuidance: UserGuidance[];
  private guidanceHistory: UserGuidance[];
  private effectivenessTracker: GuidanceEffectivenessTracker;

  receiveGuidance(guidance: UserGuidance): Promise<void>;
  processGuidance(guidance: UserGuidance): Promise<GuidanceResult>;
  prioritizeGuidance(guidance: UserGuidance[]): UserGuidance[];
  trackEffectiveness(guidance: UserGuidance, result: GuidanceResult): void;
}
```

### Rollback Engine
```typescript
export interface ExecutionCheckpoint {
  id: string;
  stepNumber: number;
  timestamp: number;
  workspaceState: any;
  agentState: any;
  filesystemSnapshot: FilesystemSnapshot;
  metadata: CheckpointMetadata;
}

export class RollbackEngine {
  private checkpoints: Map<string, ExecutionCheckpoint>;
  private changeDetector: ChangeDetector;
  private visualizer: DiffVisualizer;

  createCheckpoint(stepNumber: number): Promise<ExecutionCheckpoint>;
  rollback(checkpointId: string): Promise<RollbackResult>;
  visualizeDiff(before: ExecutionCheckpoint, after: ExecutionCheckpoint): Promise<DiffResult>;
  detectChanges(fromCheckpoint: ExecutionCheckpoint, toState: any): Promise<Change[]>;
  validateRollback(checkpointId: string): Promise<boolean>;
}
```

## Database Schema

### agent_executions Table
```sql
CREATE TABLE agent_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  task_id UUID REFERENCES agent_tasks(id),
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  current_step INTEGER DEFAULT 0,
  total_steps INTEGER,
  control_source VARCHAR(20) DEFAULT 'agent',
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_agent_executions_user_id (user_id),
  INDEX idx_agent_executions_task_id (task_id),
  INDEX idx_agent_executions_status (status),
  INDEX idx_agent_executions_started_at (started_at)
);
```

### execution_checkpoints Table
```sql
CREATE TABLE execution_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID REFERENCES agent_executions(id),
  step_number INTEGER NOT NULL,
  workspace_state JSONB,
  agent_state JSONB,
  filesystem_snapshot JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_rollback_safe BOOLEAN DEFAULT true,

  INDEX idx_execution_checkpoints_execution_id (execution_id),
  INDEX idx_execution_checkpoints_step_number (step_number),
  INDEX idx_execution_checkpoints_created_at (created_at)
);
```

### intervention_events Table
```sql
CREATE TABLE intervention_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID REFERENCES agent_executions(id),
  intervention_type VARCHAR(50) NOT NULL, -- pause, takeover, guidance, rollback
  user_id UUID NOT NULL REFERENCES users(id),
  intervention_data JSONB,
  rationale TEXT,
  outcome VARCHAR(50),
  response_time_ms INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_intervention_events_execution_id (execution_id),
  INDEX idx_intervention_events_user_id (user_id),
  INDEX idx_intervention_events_type (intervention_type),
  INDEX idx_intervention_events_created_at (created_at)
);
```

### user_guidance Table
```sql
CREATE TABLE user_guidance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID REFERENCES agent_executions(id),
  user_id UUID NOT NULL REFERENCES users(id),
  guidance_type VARCHAR(50) NOT NULL,
  priority VARCHAR(20) NOT NULL DEFAULT 'medium',
  content TEXT NOT NULL,
  context JSONB,
  expected_impact TEXT,
  accepted BOOLEAN,
  implemented BOOLEAN,
  effectiveness_score FLOAT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_user_guidance_execution_id (execution_id),
  INDEX idx_user_guidance_user_id (user_id),
  INDEX idx_user_guidance_priority (priority),
  INDEX idx_user_guidance_created_at (created_at)
);
```

## API Endpoints

### Execution Control
- `POST /api/agent/executions/{id}/pause` - Pause agent execution
- `POST /api/agent/executions/{id}/resume` - Resume agent execution
- `POST /api/agent/executions/{id}/takeover` - Take manual control
- `POST /api/agent/executions/{id}/release` - Release control back to agent
- `GET /api/agent/executions/{id}/status` - Get current execution status

### Step Navigation
- `POST /api/agent/executions/{id}/step/next` - Execute next step
- `POST /api/agent/executions/{id}/step/previous` - Go back to previous step
- `POST /api/agent/executions/{id}/step/jump` - Jump to specific step
- `GET /api/agent/executions/{id}/steps` - Get execution step list

### Checkpoint & Rollback
- `POST /api/agent/executions/{id}/checkpoints` - Create new checkpoint
- `GET /api/agent/executions/{id}/checkpoints` - List available checkpoints
- `POST /api/agent/executions/{id}/rollback` - Rollback to checkpoint
- `GET /api/agent/executions/{id}/diff` - Get state diff visualization

### Guidance System
- `POST /api/agent/executions/{id}/guidance` - Provide user guidance
- `GET /api/agent/executions/{id}/guidance` - Get guidance history
- `PUT /api/agent/guidance/{id}/effectiveness` - Rate guidance effectiveness
- `GET /api/agent/guidance/templates` - Get guidance templates

## Configuration

### Intervention Settings
```typescript
export const INTERVENTION_CONFIG = {
  pause: {
    maxResponseTime: 1000, // 1 second max
    autoResumeTimeout: 300000, // 5 minutes auto-resume
    requireConfirmation: false
  },
  takeover: {
    maxDuration: 1800000, // 30 minutes max takeover
    requireConfirmation: true,
    autoReleaseTimeout: 600000 // 10 minutes idle timeout
  },
  guidance: {
    maxActiveGuidance: 5,
    priorityLevels: ['critical', 'high', 'medium', 'low'],
    autoPrioritization: true,
    effectivenessTracking: true
  },
  rollback: {
    maxRollbackDepth: 10,
    requireConfirmation: true,
    autoBackupInterval: 300000, // 5 minutes
    maxStorageSize: 1073741824 // 1GB
  }
};
```

### Performance Optimization
```typescript
export const PERFORMANCE_CONFIG = {
  checkpointing: {
    interval: 5000, // 5 seconds between checkpoints
    compressionEnabled: true,
    maxMemoryUsage: 52428800, // 50MB
    cleanupThreshold: 86400000 // 24 hours retention
  },
  inputRouting: {
    bufferSize: 1000,
    processingInterval: 16, // ~60fps
    maxLatency: 50 // 50ms max input latency
  },
  guidance: {
    maxProcessingTime: 2000, // 2 seconds max
    batchSize: 10,
    timeoutMs: 5000
  }
};
```

## Testing Strategy

### Unit Tests
- **Execution Controller**: Pause, resume, takeover functionality
- **Input Router**: Input routing and control transfer logic
- **Guidance System**: Guidance processing and prioritization
- **Rollback Engine**: Checkpoint creation and state restoration

### Integration Tests
- **End-to-End Intervention**: Complete intervention workflows
- **Multi-Step Execution**: Step navigation and control scenarios
- **State Consistency**: Verify state preservation across interventions
- **Performance Testing**: Response time and memory usage validation

### User Experience Tests
- **Control Transfer**: Smooth transition between agent and user control
- **Guidance Effectiveness**: User guidance acceptance and implementation rates
- **Rollback Safety**: Safe rollback operations without data loss
- **Intuitive Interface**: User understanding and ease of use

### Performance Tests
- **Response Time**: <1s pause response time validation
- **Memory Usage**: Checkpoint storage and memory management
- **Concurrent Operations**: Multiple interventions simultaneously
- **Large-Scale Rollback**: Performance with complex state changes

## Success Metrics

### Control Metrics
- **Pause Response Time**: 95% of pauses under 1 second
- **Control Transfer Success**: 99% successful control transfers
- **Step Navigation Accuracy**: 100% accurate step forward/backward
- **Rollback Success Rate**: 98% successful rollback operations

### User Experience Metrics
- **Intervention Frequency**: Average 2-3 interventions per session
- **Guidance Acceptance Rate**: 75% of user guidance accepted by agent
- **Takeover Duration**: Average 5-10 minutes per takeover session
- **User Satisfaction**: NPS score above 80 for intervention system

### Performance Metrics
- **System Responsiveness**: <100ms average response for controls
- **Memory Efficiency**: <100MB additional memory usage for intervention system
- **Checkpoint Performance**: <500ms checkpoint creation time
- **Rollback Speed**: <2 seconds for typical rollback operations

## Dependencies

### Internal Dependencies
- **Story 8.1**: Workspace foundation for takeover control
- **Story 8.2**: Multi-mode system for intervention interface integration
- **Story 5.4**: Multi-step task planning for step control functionality
- **Epic 5**: Agent mode and task execution infrastructure

### External Dependencies
- **WebSocket**: Real-time communication for control commands
- **Redis**: State management and caching for execution control
- **PostgreSQL**: Storage for checkpoints and intervention events
- **React**: Frontend components for intervention controls

## Risk Assessment

### Technical Risks
- **State Complexity**: Managing complex execution states and checkpoints
  - **Mitigation**: Clear state architecture with comprehensive testing
- **Race Conditions**: Simultaneous interventions causing conflicts
  - **Mitigation**: Proper locking mechanisms and conflict resolution
- **Performance Impact**: Intervention system affecting agent performance
  - **Mitigation**: Efficient algorithms and asynchronous processing

### User Experience Risks
- **Control Confusion**: Users may not understand control transfer mechanics
  - **Mitigation**: Clear visual indicators and comprehensive onboarding
- **Over-Intervention**: Excessive user intervention disrupting agent workflow
  - **Mitigation**: Guidance on appropriate intervention timing and usage

## Definition of Done

### Code Requirements
- [ ] All acceptance criteria met and tested
- [ ] Code review completed and approved
- [ ] Performance benchmarks achieved
- [ ] Security review passed for control transfer mechanisms

### Testing Requirements
- [ ] Unit test coverage >95%
- [ ] Integration tests covering all intervention scenarios
- [ ] Performance tests meeting response time requirements
- [ ] Security tests for control transfer and rollback safety
- [ ] User acceptance testing with positive feedback

### Operational Requirements
- [ ] Monitoring and alerting for intervention system health
- [ ] Documentation for troubleshooting and support
- [ ] Training materials for users and support staff
- [ ] Backup and recovery procedures for critical data

### User Experience Requirements
- [ ] Intuitive and responsive intervention controls
- [ ] Clear visual indicators for control states
- [ ] Comprehensive guidance and help system
- [ ] Smooth transitions between control sources

## Notes

### Important Considerations
- **Safety First**: Rollback and intervention safety mechanisms are critical
- **User Control**: Always maintain user's ability to intervene and control
- **Performance**: Intervention system must not impact agent performance
- **Transparency**: Clear indication of control source and execution state

### Future Enhancements
- **Predictive Intervention**: AI-predicted intervention opportunities
- **Voice Control**: Voice commands for intervention and control
- **Collaborative Intervention**: Multiple users collaborating on interventions
- **Learning System**: Agent learning from user interventions and guidance

---

This story establishes a comprehensive intervention and control system that gives users granular control over agent execution while maintaining safety and performance. The implementation provides the foundation for true human-AI collaboration with intelligent guidance, rollback capabilities, and seamless control transfer mechanisms.

## Dev Agent Record

### Context Reference
<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes List
- Advanced intervention control system architecture designed with comprehensive state management
- Input routing and takeover system specified for seamless control transfer
- Step-by-step execution control with navigation and checkpointing implemented
- Guidance and suggestion system created for user-agent collaboration
- Rollback engine with visual diff capabilities designed
- Database schema for execution tracking and intervention logging completed
- Performance targets and safety mechanisms established with comprehensive testing strategy

### File List
**Files to Create:**
- onyx-core/src/agent/AgentExecutionController.ts
- onyx-core/src/agent/InputRouter.ts
- onyx-core/src/agent/GuidanceSystem.ts
- onyx-core/src/agent/RollbackEngine.ts
- suna/src/components/intervention/InterventionPanel.tsx
- suna/src/components/intervention/GuidanceInterface.tsx
- suna/src/components/intervention/StepNavigator.tsx
- suna/src/hooks/useAgentControl.ts

**Files to Modify:**
- onyx-core/src/agent/AgentService.ts
- suna/src/components/workspace/WorkspaceViewer.tsx
- suna/src/types/agent.ts

## Change Log
**Created:** 2025-11-15
**Status:** drafted
**Last Updated:** 2025-11-15
**Workflow:** BMAD create-story workflow execution