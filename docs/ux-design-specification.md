# Manus Internal - UX Design Specification

**Project:** ONYX - Manus Internal Strategic Intelligence System  
**Author:** Sally (UX Designer)  
**Date:** 2025-11-10  
**Version:** 1.0  
**Status:** Ready for Implementation

---

## Executive Summary

**Manus Internal** is M3rcury Ventures' private, self-hosted strategic intelligence advisor. This UX specification defines the user experience, visual design, interaction patterns, and component architecture needed to deliver a fast, trustworthy, and empowering strategic AI platform for three partners: Darius, Cameron, and Andres.

### Design Philosophy

Manus prioritizes:
1. **Speed First** — Responses feel instant; strategic insights delivered in <2 seconds
2. **Trust Through Sources** — Every claim is cited; users know exactly where information comes from
3. **Minimal Friction** — One click/tap to accomplish anything; no hidden complexity
4. **Clear Agency** — Users see plans before execution; control over agent actions
5. **Spacious Design** — Breathing room, scannable information, focused content
6. **Smooth Interactions** — Subtle animations, premium feel, Framer-like polish

### Emotional Goals

Partners should feel:
- **Confident & Empowered** — "I have the answer I need, backed by sources I trust"
- **Fast & Efficient** — "This saved me hours of manual research"
- **In Control & Safe** — "I see exactly what Manus is doing before it executes"

---

## 1. Design System Foundation

### 1.1 Technology Stack

**Design System:** shadcn/ui  
**Styling:** Tailwind CSS  
**Typography:** Inter font family  
**Component Library:** Radix UI (via shadcn)  
**Icons:** lucide-react or Heroicons

### 1.2 Why shadcn/ui?

✅ **Customizable** — You own the code, not locked into a brand  
✅ **Dark Mode First-Class** — Dark theme is trivial (Tailwind handles it)  
✅ **Framer-Like Aesthetic** — Minimal by default, you layer on polish  
✅ **YC SaaS DNA** — Used by modern companies (Stripe, Vercel, Linear patterns)  
✅ **Lightweight** — Only what you use, no bloat  
✅ **Accessible** — Radix components are WCAG AA/AAA compliant  

---

## 2. Visual Design System

### 2.1 Color Palette

#### Neutral Foundation (Backgrounds & Text)

```
Background Colors:
- bg-0 (#0A0E27):      True black-ish, rarely used
- bg-1 (#0F172A):      Primary background, main interface
- bg-2 (#1A202C):      Elevated surfaces (cards, panels)
- bg-3 (#242E42):      Hover states, interactive elevation

Text Colors:
- text-primary (#F8FAFC):    Main text, high contrast
- text-secondary (#CBD5E1):  Secondary content, slightly muted
- text-tertiary (#94A3B8):   Hints, labels, metadata
- text-muted (#64748B):      Disabled, very subtle

Borders:
- border-subtle (#1F2937):  Almost invisible, refined
- border-normal (#374151):  Visible but minimal
```

#### Accent Colors (Premium Blue)

```
Primary Accent (Strategic, Confident, Tech-Forward):
- accent-bright (#00D9FF):   Cyan, maximum pop, citations
- accent-medium (#0EA5E9):   Sky blue, primary buttons
- accent-dark (#0284C7):     Darker blue, hover states

Why This Blue?
- Modern, tech-forward (YC SaaS aesthetic)
- Signals trust & confidence (strategic decisions)
- High contrast on dark bg (WCAG AAA)
- Premium feel (not generic web blue)
```

#### Semantic Colors

```
Status Indicators:
- success (#10B981):   Emerald, approvals, completed
- warning (#F59E0B):   Amber, caution, needs attention
- error (#EF4444):     Red, errors, deletions
- info (#0EA5E9):      Blue, informational

Usage:
- Success: Agent task completion, approvals
- Warning: Approval gates, caution messages
- Error: Errors, deletions, validation failures
- Info: Informational messages, highlights
```

### 2.2 Typography System

**Font Family:** Inter (modern, clean, tech-forward)

#### Type Scale

```
Headlines:
- h1: 32px, weight 700, line-height 1.25  → Page titles, major sections
- h2: 24px, weight 600, line-height 1.33  → Section headers
- h3: 20px, weight 600, line-height 1.4   → Subsection headers

Body Text:
- body-lg:  16px, weight 400, line-height 1.5  → Main content, chat messages
- body:     14px, weight 400, line-height 1.5  → Default UI text
- body-sm:  13px, weight 400, line-height 1.5  → Smaller content, labels

Monospace (for technical content):
- mono: 13px, weight 400, font-family 'Monaco' or 'Menlo'
        → Citations, API responses, code blocks

Special:
- caption: 12px, weight 500, line-height 1.4  → Timestamps, metadata
- button:  14px, weight 500, line-height 1    → Call-to-action buttons
```

**Why This Scale?**
- 14-16px body text is readable without strain
- Clear visual jumps guide scanning and hierarchy
- Generous line-height (1.5) feels spacious and premium
- Meets WCAG AA minimum size + contrast requirements

### 2.3 Spacing & Layout System

**Base Unit:** 8px (standard, scales cleanly to any breakpoint)

#### Spacing Scale

```
xs:   4px   → Very tight, button padding edges
sm:   8px   → Standard padding (buttons, tight spacing)
md:   16px  → Standard section padding
lg:   24px  → Large gaps between sections
xl:   32px  → Extra large, major divisions
2xl:  48px  → Page-level spacing

Component Padding (Common):
- Buttons:     10px (vertical) × 16px (horizontal)
- Inputs:      10px (vertical) × 12px (horizontal), min 44px height
- Cards:       16px (all sides)
- Modals:      24px (inside padding)
- Chat area:   24px (horizontal), 16px (message gap)
```

#### Layout Grid

```
Desktop (1440px):
- 12-column grid, 16px gutters
- Max-width container: 1280px (leaves margin on ultra-wide)

Tablet (768px):
- 8-column grid, 16px gutters

Mobile (375px):
- 4-column grid, 12px gutters
- Single-column stacking for most UI

Chat-Specific:
- Message max-width: 80% (prevents too-wide text lines)
- Sidebar width: 280px (desktop) → 100% mobile
- Right panel width: 350px (desktop) → hidden mobile
```

### 2.4 Interactive States & Micro-Interactions

#### Button States

```
Primary Button (#0EA5E9):
  Default:  bg: #0EA5E9, no shadow
  Hover:    bg: #0284C7, shadow: 0 4px 12px rgba(0,217,255,0.15)
  Active:   bg: #0284C7, shadow: 0 2px 4px (pressed feel)
  Focus:    outline: 2px #00D9FF, outline-offset: 2px
  Disabled: bg: #1F2937, text: #64748B, cursor: not-allowed

Secondary Button (#242E42 + border):
  Default:  bg: #242E42, border: 1px #374151
  Hover:    bg: #2D3A51, border: 1px #0EA5E9
  Focus:    outline: 2px #00D9FF

Ghost Button (transparent):
  Default:  bg: transparent, text: #0EA5E9, border: 1px #374151
  Hover:    bg: #242E42
```

#### Input Focus States

```
Input Field:
  Default:    border: 1px #374151, bg: #242E42
  Focus:      border: 1px #0EA5E9
              box-shadow: 0 0 0 3px rgba(14,165,233,0.1)
              (Glowing ring effect, premium)
  Error:      border: 1px #EF4444
              box-shadow: 0 0 0 3px rgba(239,68,68,0.1)
```

#### Transitions

```
Global Transition Timing:
- All:              150ms cubic-bezier(0.4, 0, 0.2, 1)
- Hover effects:    150ms (smooth, snappy)
- Focus:            150ms (clear feedback)
- Modals/panels:    200ms (slightly slower for larger UI changes)

Why cubic-bezier(0.4, 0, 0.2, 1)?
- Standard in modern design (Material Design inspired)
- Feels snappy but not jarring
- Premium, Framer-like quality
```

---

## 3. Core User Experience

### 3.1 Defining Experience

**The Strategic Query Flow** (Primary)

> A partner asks Manus a strategic question at any time. Within 2 seconds, they see a response backed by internal company knowledge (Drive, Slack, local context) + web data, with clear citations. They can see where every fact comes from, drill into sources, and trust the answer completely.

**The Agent Task Flow** (Secondary)

> When a multi-step task is needed, a partner can toggle Agent Mode, see the execution plan, approve sensitive actions, and watch execution live in the workspace panel. They feel in control the entire time.

### 3.2 Core Experience Principles

| Principle | Means | Interaction |
|-----------|-------|-----------|
| **Speed First** | Responses stream instantly, no artificial delays | Chat streams in real-time; citations load without pause |
| **Trust Through Sources** | Every claim is traceable | Citations are obvious, sources one click away, snippets show context |
| **Minimal Friction** | One click/tap to do anything | Send message → see response → drill source (3 clicks max) |
| **Clear Agency** | User knows what Manus will do before it acts | Agent tasks show plan first; sensitive actions require approval |
| **Spacious Design** | Breathing room between elements; scannable info | Generous padding, clear hierarchy, focused content area |
| **Smooth Interactions** | Subtle animations guide attention | Fade in/out, smooth slide panels, no jarring transitions |

### 3.3 Novel Pattern: Interactive Citation System

**Problem:** How do users explore sources without losing context in the chat?

**Solution:** Integrated citation system with source sidebar

```
User reads response in chat
    ↓
Hovers over [1] citation
    ↓
Popover shows: source name, timestamp, snippet
    ↓
Clicks citation
    ↓
Source opens in right sidebar (Drive doc, Slack thread, uploaded file)
    ↓
User can continue reading chat while browsing source
    ↓
Click source to close, return focus to chat
```

**Implementation Details:**
- Citation numbers: Superscript [1] (clean, academic style)
- Hover trigger: Popover appears on hover (Framer-like, instant feedback)
- Source panel: Slide in from right on desktop (preserve chat context)
- Mobile: Full-screen modal or overlay (adapt to small screens)

---

## 4. Layout & Navigation Architecture

### 4.1 Recommended Direction: Sidebar + Right Panel (Direction 4)

**Why This Layout?**
- ✅ Classic chat interface partners know
- ✅ Left sidebar for persistent navigation (easy access to search, settings, workspace)
- ✅ Right panel for source citations (integrates research into conversation flow)
- ✅ Main chat area focused, spacious
- ✅ Scales well to desktop (primary use case)
- ✅ Adapts cleanly to tablet/mobile (sidebar collapses, panel hides)

**Layout Structure:**
```
┌─────────────┬──────────────────────┬─────────────┐
│  Sidebar    │   Main Chat Area     │Right Panel  │
│  Navigation │                      │ (Sources)   │
│  280px      │   Full Width         │ 350px       │
│             │   (Responsive)       │             │
├─────────────┼──────────────────────┼─────────────┤
│  Logo       │   Top Bar (Title)    │ Citations   │
│  New Chat   │   ────────────────   │ & Sources   │
│  Search     │   Chat Messages      │             │
│  Workspace  │   (Main Area)        │ Memory      │
│  Settings   │   ────────────────   │ Context     │
│             │   Input Area         │             │
└─────────────┴──────────────────────┴─────────────┘

Responsive Behavior:
- Desktop (>1200px): 3-column visible
- Tablet (768px-1200px): Sidebar collapses, panel hidden (slide-out on demand)
- Mobile (<768px): Sidebar & panel hidden, hamburger menu for nav
```

### 4.2 Navigation Hierarchy

**Primary Navigation (Sidebar):**
- New Chat / Chats (list of conversations)
- Search (search across all chats & memory)
- Workspace (live VNC overlay, agent tasks)
- Settings (standing instructions, memory management, profile)

**Secondary Navigation (In-Chat):**
- Chat title / metadata (top bar)
- Mode toggle (Chat ↔ Agent Mode)
- Options menu (export, archive, delete)

**Tertiary Navigation (Right Panel):**
- Sources / Citations (for current response)
- Memory Recall (relevant facts injected)
- Related Queries (similar past questions)

---

## 5. Component Library & Custom Components

### 5.1 shadcn/ui Components Used

**From Base Library:**
- Button (primary, secondary, ghost, destructive)
- Input (text, textarea, with icon support)
- Card (for message bubbles, source cards)
- Dialog / Modal (for approvals, settings)
- Sheet / Drawer (for sidebar on mobile, right panel)
- Tabs (for toggling modes, multiple sections)
- Badge (for tags, status, source type)
- Alert (for warnings, errors, info)
- Popover / Hover Card (for citation previews)
- Scroll Area (for chat history, scrollable panels)
- Dropdown Menu (for options, actions)
- Form (Form, FormField, FormControl - for complex forms)

### 5.2 Custom Components Needed

#### Chat Message Bubble

```
Component: ChatMessage
Props:
  - role: "user" | "manus"
  - content: string (Markdown support)
  - citations: [{number, source, snippet, link}]
  - timestamp: ISO string (optional)
  - isStreaming: boolean (shows typing indicator)

States:
  - default: Complete message rendered
  - streaming: Message still arriving, character-by-character
  - error: Failed to load, retry button

Design:
  - User messages: Aligned right, #0EA5E9 background, white text
  - Manus messages: Aligned left, #242E42 background, #F8FAFC text
  - Citations: Superscript [1] in text, interactive (hover → popover)
  - Hover: Subtle glow effect, appears copy & action buttons
```

#### Citation Popover

```
Component: CitationPreview
Props:
  - citation: {source_type, source_name, timestamp, snippet, link}
  - onView: callback to open source in panel

Design:
  - Trigger: Hover over [N] citation
  - Content:
    - Source icon (📄 Doc, 💬 Slack, 🌐 Web)
    - Source name (clickable link)
    - Timestamp (e.g., "Updated 2 hours ago")
    - Snippet (100 chars of context)
  - Size: Small, 300px wide popover
  - Animation: Fade in 150ms on hover
```

#### Agent Approval Gate Modal

```
Component: ApprovalGate
Props:
  - action: string (what the agent wants to do)
  - reason: string (why it's doing this)
  - preview: ReactNode (preview of result if possible)
  - onApprove, onReject: callbacks
  - timeout: number (auto-reject after N seconds)

Design:
  - Modal overlay (#000 with opacity, centered)
  - Clear heading: "Approval Required"
  - Section 1: "Action" (what is Manus doing?)
  - Section 2: "Reason" (why is it doing this?)
  - Section 3: "Preview" (if available, show what will be created)
  - Buttons: [Approve (green)] [Reject (gray)] [Modify (blue)]
  - Timeout warning: "Auto-rejecting in 30 seconds..." (if needed)
```

#### Live Workspace Panel

```
Component: WorkspacePanel
Props:
  - vncUrl: string (noVNC WebSocket URL)
  - isOpen: boolean
  - onClose: callback
  - agentState: "idle" | "running" | "paused"
  - onPause, onResume, onTakeover: callbacks

Design:
  - Right-side slide-out panel (350px wide)
  - Top bar: "Live Workspace" + status indicator + controls
  - Main area: noVNC iframe (embedded VNC viewer)
  - Bottom bar: Buttons [Pause] [Resume] [Fullscreen]
  - Handles agent pause/resume + founder takeover
  - Logs all actions to audit trail
```

#### Source / Citation Sidebar

```
Component: SourceSidebar
Props:
  - citations: Citation[]
  - selectedId: string | null
  - onSelectSource: callback

Design:
  - Right panel (350px)
  - Title: "Sources & Context"
  - Section 1: "Citations" (list of sources from response)
    - Expandable items: source name, type icon, timestamp
    - Click to view content (in preview or external)
  - Section 2: "Memory" (relevant facts injected for this query)
    - List of memory facts, click to view in full
  - Search within panel (optional: search sources)
  - Copy buttons for each source
```

---

## 6. User Journey Flows

### 6.1 Strategic Query Journey

```
User Flow: "What's the competitive landscape for AI agents?"

Step 1: User enters chat
  - Sees familiar chat interface
  - Left sidebar for navigation
  - Right panel empty (no sources yet)
  - Input field ready with cursor

Step 2: User types question
  - Input field highlights on focus (#0EA5E9 glow)
  - Character count visible (optional)
  - Submit: Cmd+Enter or click Send button

Step 3: Manus begins responding
  - "Manus is thinking..." (typing indicator)
  - First token appears within 500ms
  - Response streams character-by-character
  - Citations [1], [2], [3] appear inline

Step 4: User reads response
  - Can hover over [1] → see citation popover
  - Popover shows: source name, timestamp, snippet
  - Click [1] → source opens in right sidebar
  - User reads source while chat still visible

Step 5: User has follow-up
  - Types: "How does this affect our strategy?"
  - Response incorporates previous context
  - New citations shown
  - Sources added to right panel

Step 6: User explores deeper
  - Clicks on a source doc
  - Drive doc opens in sidebar or new tab
  - Returns to chat, continues conversation

Success:
  - Response arrived <2s
  - All claims cited
  - Sources easy to access
  - Conversation felt fast, trustworthy
```

### 6.2 Agent Task Journey

```
User Flow: "Create a competitive analysis document for Monday's meeting"

Step 1: Toggle Agent Mode
  - Chat mode: blue [Chat Mode] button
  - Click to toggle → "Agent Mode" enabled
  - Warning shown: "Agent will execute actions. Review approvals."
  - Button changes to [Execute Task]

Step 2: User requests task
  - Types: "Create competitive analysis doc with market trends"
  - System prompts: "Should I include pricing analysis?"
  - User confirms

Step 3: Agent creates plan
  - "Planning task... [⏳ 2/3 steps ready]"
  - Shows plan before executing:
    - Step 1: Search web for AI market trends [search_web]
    - Step 2: Analyze our internal positioning [search_internal]
    - Step 3: Create Google Doc with findings [create_doc]
    - Step 4: Save to M3rcury shared folder [permissions check]
  - User can: [Approve] [Edit plan] [Run different approach]

Step 4: User approves plan
  - Clicks [Approve & Execute]
  - Agent begins execution
  - Step 1: Web search running... ✓ Complete (5 sources found)
  - Step 2: Internal search running... ✓ Complete (4 docs analyzed)
  - Step 3: Creating document... ⏳ In progress

Step 5: Approval Gate (Sensitive Action)
  - Modal appears: "Create Google Doc?"
  - Details: "Creating 'Competitive Analysis - Nov 2025' in /M3rcury Shared/"
  - Preview: [Shows first 3 paragraphs]
  - Buttons: [Approve] [Reject] [Edit & Create]
  - User clicks [Approve]

Step 6: Task completes
  - ✅ Document created successfully
  - "Generated: Competitive Analysis Nov 2025.gdoc"
  - Link: [Open in Google Drive]
  - Task time: 1m 23s
  - [View Logs] for detailed execution

Step 7: User reviews document
  - Opens link in new tab
  - Reviews Manus-generated content
  - Makes edits as needed
  - Done!

Success:
  - User felt in control throughout
  - All sensitive actions required approval
  - Document was exactly what was requested
  - Process took 2 minutes total
```

---

## 7. UX Pattern Decisions (Consistency Rules)

### 7.1 Button Hierarchy

```
Primary Action (Most Important):
  - Background: #0EA5E9 (accent-medium)
  - Text: white
  - Usage: Main CTAs (Send message, Approve task, Create doc)
  - Size: Default (44px min height for touch)

Secondary Action (Important but not primary):
  - Background: #242E42
  - Border: 1px #374151
  - Text: #CBD5E1
  - Usage: Cancel, settings, back, secondary options
  - Size: Default

Ghost Action (Subtle, exploratory):
  - Background: transparent
  - Border: 1px #374151
  - Text: #0EA5E9
  - Usage: Learn more, view source, expand, optional actions
  - Size: Default

Destructive Action (Warning, rarely used):
  - Background: #EF4444
  - Text: white
  - Usage: Delete, dangerous operations (rare in Manus)
  - Requires confirmation modal
  - Size: Default

Context Menu Actions:
  - Rendered in dropdown, same styling as ghost/secondary
  - Hover highlight background: #2D3A51
```

### 7.2 Feedback Patterns

```
Success Message:
  - Alert box: bg: rgba(16,185,129,0.1), border: 1px #10B981
  - Icon: ✓ in green (#10B981)
  - Text: "Agent task completed successfully"
  - Duration: Auto-dismiss after 6 seconds
  - Position: Top-right (not blocking content)

Error Message:
  - Alert box: bg: rgba(239,68,68,0.1), border: 1px #EF4444
  - Icon: ✗ in red (#EF4444)
  - Text: "Failed to retrieve document. Retry?"
  - Duration: Persistent (user must dismiss)
  - Position: Top-right with prominent visibility

Warning Message:
  - Alert box: bg: rgba(245,158,11,0.1), border: 1px #F59E0B
  - Icon: ⚠ in amber (#F59E0B)
  - Text: "This action requires approval"
  - Duration: Persistent
  - Position: Top-right or inline with affected element

Loading State:
  - Spinner: 24px circular, #0EA5E9
  - Text: "Searching internal documents..." or "Creating document..."
  - Position: Inline (in message, not blocking)
  - Animation: Smooth rotation, 1s per rotation

Toast/Notification Stack:
  - Multiple notifications stack top-right
  - Spacing: 12px between toasts
  - Max-width: 400px
  - Auto-dismiss after 6 seconds (unless error)
```

### 7.3 Form Patterns

```
Label Position:
  - Above input (top-aligned, not floating)
  - Label: "Standing Instruction"
  - Sub-label: "What should Manus remember?" (help text)

Required Field Indicator:
  - Red asterisk *
  - Appears after label: "Standing Instruction *"

Validation Timing:
  - On blur (when user leaves field)
  - Not on every keystroke (reduces noise)
  - Real-time for email validation (optional)

Error Display:
  - Inline below input: "error message in red"
  - Input border turns red (#EF4444)
  - Icon appears (alert triangle)

Help Text:
  - Below input in gray (#94A3B8)
  - "e.g., 'Prioritize defense contracts in analysis'"
  - Shows before error, replaced by error when present
```

### 7.4 Modal & Dialog Patterns

```
Approval Gate Modal:
  - Overlay: #000 at 50% opacity, covers full screen
  - Modal: Centered, 500px wide (600px on desktop)
  - Border: 1px #374151
  - Backdrop blur: Optional (modern, subtle)
  - Close: [X] button top-right, [Reject] button bottom-left
  - Action buttons: [Approve (green)] [Reject (gray)]

Settings Modal:
  - Similar to approval gate
  - Title: "Settings" or specific setting name
  - Content: Form fields for editing
  - Footer: [Cancel] [Save]

Confirmation Dialog:
  - Smaller modal (400px wide)
  - Title: "Are you sure?"
  - Message: Specific action being confirmed
  - Buttons: [Cancel (secondary)] [Confirm (primary or error)]
  - Dismissible: Click overlay to cancel

Dismiss Behavior:
  - Can click outside modal to cancel (non-destructive)
  - Press Escape to cancel
  - Destructive actions require explicit button click (can't close via overlay)
```

### 7.5 Empty State Patterns

```
First Use (No Chats):
  - Large icon: 💬
  - Heading: "Welcome to Manus"
  - Text: "Ask a strategic question to get started"
  - Example: "What's the competitive landscape for AI agents?"
  - Button: [Try this query]

No Results (Search):
  - Icon: 🔍
  - Heading: "No results found"
  - Text: "Try different keywords or ask a new question"
  - Suggestions: [Refine search] [Try web search]

Cleared/Archived Content:
  - Icon: 🗑️
  - Heading: "Chat archived"
  - Text: "This conversation has been archived"
  - Actions: [Unarchive] [Delete permanently]

No Memory Facts:
  - Icon: 🧠
  - Heading: "No memories yet"
  - Text: "Manus will remember key facts from your conversations"
  - Button: [Learn more about memory]
```

### 7.6 Citation & Source Patterns

```
Citation Format (In Response Text):
  - Superscript number: [1], [2], [3]
  - Color: #0EA5E9 (accent-medium)
  - Weight: Normal text weight
  - Underline: On hover, shows as clickable

Citation Key (Below Message):
  - Format: "[1] 2025-11-10 | Google Drive | Q3 Board Deck"
  - Link: Clickable to open source
  - Spacing: 8px above previous content, in light gray

Citation Preview (Popover):
  - Trigger: Hover on [N]
  - Content:
    - Icon: Based on source type (📄, 💬, 🌐)
    - Title: Source name
    - Timestamp: "Updated 2 hours ago"
    - Snippet: 100-150 chars of context
    - Footer: "[View source]" link
  - Size: 300px wide, 150px tall

Citation in Sidebar:
  - List of all citations for response
  - Each item shows: icon, name, timestamp
  - Expandable to show snippet
  - Click to open/expand in main view or new tab
```

---

## 8. Responsive Design & Accessibility

### 8.1 Responsive Strategy

#### Desktop (>1200px)

```
Layout: Full 3-column
- Sidebar: 280px (visible, collapsible via hamburger)
- Chat area: Flexible width
- Right panel: 350px (visible, shows sources)

Navigation: Sidebar navigation visible
Workspace: Right side panel integrated
Chat: Full width available
Input: Bottom of chat area
```

#### Tablet (768px - 1200px)

```
Layout: Sidebar collapsed, 2-column
- Sidebar: Hidden, hamburger menu
- Chat area: Full width
- Right panel: Hidden initially, slide-out on demand

Navigation: Hamburger menu (top-left)
Workspace: Full-screen modal or overlay
Chat: Full width
Input: Bottom of chat area, spans full width
```

#### Mobile (<768px)

```
Layout: Single column, stack everything
- Sidebar: Hidden, drawer menu (hamburger)
- Chat area: Full width, 100% height
- Right panel: Hidden, modal only

Navigation: Hamburger menu, drawer navigation
Workspace: Full-screen modal
Chat: Full width, limited height (input at bottom)
Input: Fixed at bottom, full width (44px height)
Message max-width: 100% (not 80%)
```

### 8.2 Accessibility Strategy

**Target:** WCAG 2.1 Level AA compliance

#### Color Contrast

```
Requirements:
- Body text on backgrounds: 7:1 ratio (AAA)
- Large text (18pt+) on backgrounds: 4.5:1 ratio (AA)
- Interactive elements (buttons): 4.5:1 (AA)

Specific Pairs:
- #F8FAFC text on #0F172A: 16:1 (excellent)
- #CBD5E1 text on #1A202C: 8:1 (excellent)
- #0EA5E9 button on #0F172A: 4.9:1 (AA)
- #10B981 (success) on dark: 4.5:1 (AA)

Avoid Color-Only Communication:
- Don't use color alone for status (always add icon/text)
- Error messages use text + red color
- Success uses text + green icon
```

#### Keyboard Navigation

```
Tab Order:
- Sidebar navigation
- Main chat messages (read-only, Skip with Tab)
- Chat input field
- Send button
- Right panel sources (if open)

Focus Indicators:
- All interactive elements: 2px solid #0EA5E9 outline
- Outline-offset: 2px (visible space around element)
- No outline: none (always override with custom)

Keyboard Shortcuts (Optional, but helpful):
- Cmd/Ctrl+K: Focus search / command palette
- Cmd/Ctrl+N: New chat
- Cmd/Ctrl+Enter: Send message
- Escape: Close modal or panel
- Tab: Navigate to next element
- Shift+Tab: Navigate to previous element
```

#### Screen Reader Support

```
Aria Labels:
- Buttons: <button aria-label="Send message">→</button>
- Icons: Icon + aria-label (not aria-hidden unless decorative)
- Chat messages: <div role="article" aria-label="Manus response">

Headings:
- Use proper heading hierarchy (h1, h2, h3)
- Don't skip levels (no h1 → h3, skip h2)
- Use semantic HTML (<header>, <nav>, <main>, <section>)

Live Regions:
- Chat messages: aria-live="polite" (announce as they appear)
- Loading states: aria-busy="true"
- Alerts: role="alert" (high priority announce)
```

#### Touch Targets

```
Minimum Touch Target: 44px × 44px (accessible on mobile)

Component Sizing:
- Buttons: Min 44px height
- Input fields: Min 44px height
- Icons: 24px inside 44px container
- Links: 44px clickable area (padding if small text)

Spacing:
- Min 8px between touch targets
- Group related targets (avoid accidental clicks)
```

---

## 9. Implementation Guidance

### 9.1 Component Setup (Manus-Specific Variants)

**shadcn/ui Components + Customization:**

```typescript
// Example: Custom Chat Message Component
import { Card } from "@/components/ui/card"

export interface ChatMessageProps {
  role: "user" | "manus"
  content: string  // Markdown support
  citations?: Citation[]
  isStreaming?: boolean
  timestamp?: string
}

export function ChatMessage({
  role,
  content,
  citations,
  isStreaming,
}: ChatMessageProps) {
  return (
    <Card className={cn(
      "max-w-[80%] px-4 py-3 rounded-lg",
      role === "user" 
        ? "ml-auto bg-blue-500 text-white" 
        : "bg-slate-800 text-slate-50 border border-slate-700"
    )}>
      <div className="prose prose-invert text-sm max-w-none">
        {/* Render markdown content with citation highlights */}
        {renderContentWithCitations(content, citations)}
      </div>
      {isStreaming && <div className="mt-2 text-xs opacity-75">...</div>}
    </Card>
  )
}
```

### 9.2 Color Token System (Tailwind)

```javascript
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        // Manus dark theme
        bg: {
          0: "#0A0E27",
          1: "#0F172A",  // primary
          2: "#1A202C",  // elevated
          3: "#242E42",  // hover
        },
        text: {
          primary: "#F8FAFC",
          secondary: "#CBD5E1",
          tertiary: "#94A3B8",
          muted: "#64748B",
        },
        border: {
          subtle: "#1F2937",
          normal: "#374151",
        },
        accent: {
          bright: "#00D9FF",
          medium: "#0EA5E9",
          dark: "#0284C7",
        },
      },
    },
  },
}

// Usage: <button className="bg-accent-medium text-white">Send</button>
```

### 9.3 Animation & Transition System

```css
/* Global transitions */
:root {
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Example: Chat message fade-in */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message {
  animation: fadeInUp var(--transition-normal);
}

/* Example: Button hover */
.btn {
  transition: background var(--transition-fast), 
              box-shadow var(--transition-fast);
}
```

### 9.4 Dark Mode Implementation

```jsx
// Dark mode is default and always on (no toggle)
// shadcn/ui + Tailwind handle dark mode via CSS variables

// In _app.tsx or layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <style>{`
          :root {
            --background: #0F172A;
            --foreground: #F8FAFC;
          }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  )
}
```

---

## 10. Completion Summary

### Deliverables Created

✅ **Color Theme Explorer**  
- Interactive HTML showcasing all colors, components, text scales
- Located: `docs/ux-color-themes.html`
- Shows: Neutral palette, accents, semantic colors, button/input/alert examples

✅ **Design Direction Mockups**  
- 8 different layout approaches (Sidebar, Top Nav, Floating, Panel, Minimal, Dense, Cards, Command)
- Located: `docs/ux-design-directions.html`
- Interactive navigation between directions
- Includes: Layout characteristics, best-use cases, recommendations

✅ **UX Design Specification Document**  
- Complete design system definition
- User journey flows (strategic query, agent task)
- Component library & custom components
- Accessibility & responsive strategy
- Located: `docs/ux-design-specification.md` (this document)

### Design Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Design System | shadcn/ui | Modern, customizable, YC SaaS aesthetic |
| Dark Mode | Dark-first, always on | Reduces eye strain, matches M3rcury brand, premium feel |
| Primary Accent | #0EA5E9 (sky blue) | Modern, tech-forward, high contrast, signals trust |
| Navigation | Sidebar + Right Panel | Classic chat UX, source exploration integrated, scales responsively |
| Typography | Inter, 14-16px body | Readable, modern, accessible, Framer-like |
| Spacing | 8px base unit | Responsive, predictable, spacious feel |
| Citation UX | Hover popover + sidebar | Integrated research, doesn't break chat flow |
| Accessibility | WCAG AA target | Inclusive, professional, legally defensible |

### Next Steps for Development

1. **Setup shadcn/ui** in Next.js project
   - Install shadcn components
   - Configure Tailwind with Manus color tokens
   - Create custom components (ChatMessage, CitationPopover, etc.)

2. **Build Core Chat Interface** (Step 6 prep)
   - Implement sidebar navigation
   - Build chat message component with streaming
   - Add citation system with hover previews
   - Integrate right panel for sources

3. **User Journey Implementation**
   - Strategic query flow (chat + RAG)
   - Agent mode flow (planning + approval gates)
   - Live workspace panel (noVNC integration)

4. **Test & Refine**
   - Accessibility testing (keyboard nav, screen readers)
   - Responsiveness testing (desktop, tablet, mobile)
   - User testing with partners (Darius, Cameron, Andres)
   - Iterate on design based on feedback

5. **Polish & Launch**
   - Micro-animations and transitions
   - Performance optimization
   - Browser compatibility
   - Production deployment

---

## Design Principles (Repeated for Reference)

Every interaction in Manus should embody these principles:

1. **Speed First** ⚡ — Make users feel like they're interacting with something instant
2. **Trust Through Sources** 🔐 — Every claim is traceable, no surprises
3. **Minimal Friction** 🎯 — One click/tap to do anything important
4. **Clear Agency** 👁️ — Users see the plan before Manus acts
5. **Spacious Design** 🌬️ — Breathing room, never cramped
6. **Smooth Interactions** ✨ — Subtle animations that guide, not distract

---

## Appendix: References

**Input Documents:**
- Product Brief: `docs/product-brief-ONYX-2025-11-10.md`
- PRD: `docs/PRD.md`
- Epics: `docs/epics.md`

**Interactive Deliverables:**
- Color Theme Explorer: `docs/ux-color-themes.html`
- Design Direction Mockups: `docs/ux-design-directions.html`

**Design Tokens:**
- Colors: 20+ defined (neutrals, accents, semantics)
- Typography: 8 scales (h1, h2, h3, body-lg, body, body-sm, mono, caption)
- Spacing: 6 units (4px, 8px, 16px, 24px, 32px, 48px)
- Transitions: 3 speeds (150ms, 200ms, 300ms)

**Component Library:**
- shadcn/ui base components: 15+
- Custom components: ChatMessage, CitationPopover, ApprovalGate, WorkspacePanel, SourceSidebar

**Accessibility:**
- WCAG 2.1 Level AA target
- Color contrast: AAA levels maintained
- Keyboard navigation: Full support
- Screen reader: Semantic HTML + ARIA labels

---

**Design Specification Complete.**  
**Ready for Implementation by Development Team.**

_Created: 2025-11-10_  
_Next: Architecture Design & Development Sprints_

