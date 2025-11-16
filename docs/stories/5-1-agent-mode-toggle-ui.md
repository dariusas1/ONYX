# Story 5.1: Agent Mode Toggle & UI

Status: drafted

## Story

As a user,
I want to switch between Chat Mode (advisory) and Agent Mode (execution),
so that I can choose when to give Manus autonomy.

## Acceptance Criteria

1. **AC5.1.1**: Toggle switch for Agent Mode is prominently displayed in Suna UI header (top-right)
2. **AC5.1.2**: Toggle changes state seamlessly between Chat Mode and Agent Mode with visual feedback
3. **AC5.1.3**: Agent Mode displays warning message: "Agent will execute actions. Review approval gates."
4. **AC5.1.4**: "Execute Task" button replaces "Send" button in Agent Mode
5. **AC5.1.5**: "Send" button only shown in Chat Mode (no Agent Mode functionality)
6. **AC5.1.6**: User's mode preference is saved to localStorage for immediate persistence
7. **AC5.1.7**: Mode preference is synced to Supabase user_settings table for cross-device consistency
8. **AC5.1.8**: Help text or tooltip explains Agent Mode functionality when user hovers over toggle
9. **AC5.1.9**: Mode state is properly maintained across page refreshes and browser sessions
10. **AC5.1.10**: UI clearly indicates current mode through visual styling (color, labels, icons)

## Tasks / Subtasks

- [ ] **Task 1**: Implement Agent Mode Toggle Component (AC: 1, 2, 8, 10)
  - [ ] Subtask 1.1: Create ToggleSwitch React component with smooth animations
  - [ ] Subtask 1.2: Integrate toggle into Suna header layout (top-right positioning)
  - [ ] Subtask 1.3: Add visual mode indicators (icons, colors, labels)
  - [ ] Subtask 1.4: Implement hover tooltip with Agent Mode explanation
  - [ ] Subtask 1.5: Add responsive design for mobile/tablet views

- [ ] **Task 2**: Implement Mode State Management (AC: 6, 7, 9)
  - [ ] Subtask 2.1: Create mode context/provider for global state management
  - [ ] Subtask 2.2: Implement localStorage persistence for immediate mode storage
  - [ ] Subtask 2.3: Add Supabase user_settings table integration for cloud sync
  - [ ] Subtask 2.4: Handle mode restoration on app initialization
  - [ ] Subtask 2.5: Implement conflict resolution between local and cloud preferences

- [ ] **Task 3**: Update Chat Interface Based on Mode (AC: 3, 4, 5)
  - [ ] Subtask 3.1: Show/hide Agent Mode warning banner based on current mode
  - [ ] Subtask 3.2: Replace "Send" button with "Execute Task" button in Agent Mode
  - [ ] Subtask 3.3: Update chat input placeholder text based on mode
  - [ ] Subtask 3.4: Modify chat functionality to handle mode-specific behavior
  - [ ] Subtask 3.5: Add mode transitions with smooth animations

- [ ] **Task 4**: Backend Integration and User Settings (AC: 7)
  - [ ] Subtask 4.1: Update Supabase schema for user_settings table (if not exists)
  - [ ] Subtask 4.2: Create API endpoints for mode preference CRUD operations
  - [ ] Subtask 4.3: Implement authentication checks for user settings access
  - [ ] Subtask 4.4: Add error handling for settings sync failures
  - [ ] Subtask 4.5: Implement optimistic updates with rollback on sync failure

- [ ] **Task 5**: Testing and Quality Assurance (All AC)
  - [ ] Subtask 5.1: Unit tests for toggle component and state management
  - [ ] Subtask 5.2: Integration tests for localStorage and Supabase sync
  - [ ] Subtask 5.3: E2E tests for mode switching and persistence
  - [ ] Subtask 5.4: Accessibility testing (keyboard navigation, screen readers)
  - [ ] Subtask 5.5: Cross-browser compatibility testing
  - [ ] Subtask 5.6: Performance testing for mode transitions

## Dev Notes

### Architecture Patterns and Constraints
- **State Management**: Use React Context API with useReducer for predictable state updates
- **Persistence Strategy**: Dual persistence with localStorage (immediate) + Supabase (cloud sync)
- **Component Architecture**: Atomic design with reusable ToggleSwitch component
- **API Integration**: RESTful endpoints following existing Supabase patterns
- **Error Boundaries**: Implement error boundaries for settings sync failures
- **Performance**: Debounce Supabase sync to prevent excessive API calls

### Source Tree Components to Touch
- `/suna/src/components/ToggleSwitch/ToggleSwitch.jsx` - New toggle component
- `/suna/src/components/Header/Header.jsx` - Integrate toggle into header
- `/suna/src/contexts/ModeContext.jsx` - Global mode state management
- `/suna/src/hooks/useMode.js` - Custom hook for mode operations
- `/suna/src/components/ChatInterface/ChatInterface.jsx` - Mode-specific UI changes
- `/suna/src/services/settingsService.js` - Supabase settings API integration
- `/suna/src/utils/storage.js` - localStorage utilities
- `/suna/src/styles/modes.css` - Mode-specific styling

### Testing Standards Summary
- **Unit Tests**: 90% coverage for toggle logic and state management
- **Integration Tests**: Cover localStorage + Supabase sync workflows
- **E2E Tests**: Full user journey from mode toggle to persistence
- **Accessibility Tests**: WCAG AA compliance for keyboard and screen reader users
- **Performance Tests**: Mode transitions <100ms, no layout thrashing

### Project Structure Notes

- **Alignment with unified project structure**: Follow existing Suna component patterns in `/suna/src/components/`
- **Detected conflicts or variances**: None identified - follows existing Supabase + localStorage patterns used elsewhere in the application
- **Naming conventions**: Follow camelCase for components, kebab-case for CSS classes
- **File organization**: Group mode-related files in dedicated `/mode/` subdirectories for maintainability

### References

- [Source: docs/epics.md#Story-5.1] - Complete story definition and acceptance criteria
- [Source: docs/PRD.md] - Product requirements for Agent Mode functionality
- [Source: /suna/src/components/] - Existing component patterns and architecture
- [Source: /suna/src/contexts/] - Existing context management patterns
- [Source: docs/sprint-status.yaml] - Current sprint tracking and epic status

## Dev Agent Record

### Context Reference

- Story Context: `/docs/stories/context/5-1-agent-mode-toggle-ui.xml` (generated by story-context workflow)
- Context Generated: 2025-11-15T15:30:00Z
- Context Coverage: Complete project context including codebase structure, technical specifications, and implementation details

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

- N/A - Initial story creation, no development logs yet

### Completion Notes List

- Story created from BMAD create-story workflow template
- All acceptance criteria extracted from docs/epics.md
- Technical approach aligned with existing Suna architecture
- Task breakdown follows dependency order (UI → State → Backend → Testing)
- Performance and accessibility considerations included

### File List

- `/docs/stories/5-1-agent-mode-toggle-ui.md` - This story file
- `/suna/src/components/ToggleSwitch/ToggleSwitch.jsx` - Planned toggle component
- `/suna/src/contexts/ModeContext.jsx` - Planned mode context
- `/suna/src/hooks/useMode.js` - Planned mode hook
- `/suna/src/components/Header/Header.jsx` - Modified header component
- `/suna/src/components/ChatInterface/ChatInterface.jsx` - Modified chat interface
- `/suna/src/services/settingsService.js` - Planned settings service
- `/suna/src/utils/storage.js` - Storage utilities
- `/suna/src/styles/modes.css` - Mode-specific styles

### Dependencies

- **Prerequisites**: Story 2.1 (Suna UI Deployment) - Must have Suna UI running
- **Blocks**: Stories 5.2-5.8 (Agent Mode features) - Toggle is foundation for all Agent Mode functionality
- **Related Stories**:
  - Story 5.2: Tool Selection & Routing Logic
  - Story 5.3: Approval Gates for Sensitive Actions
  - Story 4.3: Memory Injection & Agent Integration

### Risk Assessment

- **Low Risk**: Component follows established patterns in Suna codebase
- **Medium Risk**: Supabase sync complexity and conflict resolution
- **Mitigation**: Implement optimistic updates with rollback, extensive testing of sync scenarios

### Success Metrics

- User can toggle between modes within <100ms
- Mode preference persists across sessions (99.9% reliability)
- Zero UI layout shifts during mode transitions
- Settings sync success rate >95%
- Accessibility compliance (WCAG AA) for keyboard and screen reader users