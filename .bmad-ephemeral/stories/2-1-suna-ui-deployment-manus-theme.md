# Story 2.1: Suna UI Deployment with Manus Theme

**Status:** drafted
**Epic:** Epic 2 - Chat Interface & Core Intelligence
**Story ID:** 2-1-suna-ui-deployment-manus-theme
**Priority:** High (Blocker for Epic 2)
**Estimated Effort:** 2-3 days
**Dependencies:** Story 1.1 (Project Setup & Repository Initialization)

---

## 📋 OVERVIEW

Deploy a functional Next.js chat interface using Suna as the base, customized with the Manus dark theme. This story establishes the frontend foundation for the entire ONYX chat experience, providing a minimalist, high-performance interface optimized for strategic work.

**As a** frontend engineer
**I want** Suna deployed with Manus dark theme (Inter font, blue accents, minimalist)
**So that** the UI feels cohesive, branded, and optimized for strategic work

**User Experience Goal:** A founder navigates to http://localhost:3000 and sees a clean, dark-themed chat interface that loads in under 2 seconds, feels responsive, and works seamlessly across desktop, tablet, and mobile devices.

---

## 🎯 ACCEPTANCE CRITERIA

### AC1: Application Launch & Performance
- **Given:** Suna is running on :3000
- **When:** User navigates to http://localhost:3000
- **Then:** Chat interface loads in <2s
- **And:** No console errors or warnings
- **And:** All assets (fonts, styles) load successfully

### AC2: Manus Dark Theme Application
- **Given:** User has loaded the chat interface
- **Then:** Dark theme with blue accents (Manus color palette) is applied consistently
- **And:** Background color is #0F172A (Deep navy)
- **And:** Surface color is #1E293B (Elevated surface)
- **And:** Primary accent is #2563EB (Blue)
- **And:** Text color is #E2E8F0 (Light gray)

### AC3: Typography
- **Given:** User views the interface
- **Then:** Inter font family is loaded and applied to all text elements
- **And:** Font weights are properly configured (400, 500, 600, 700)
- **And:** Text rendering is crisp and readable

### AC4: Layout & Design
- **Given:** User interacts with the chat interface
- **Then:** Layout is single-column, minimalist (focus on conversation)
- **And:** Maximum content width is 900px, centered on desktop
- **And:** Proper spacing and padding throughout
- **And:** No visual glitches or layout shifts

### AC5: Mobile Responsiveness
- **Given:** User accesses the interface on various devices
- **Then:** Interface is responsive on desktop (>1024px)
- **And:** Interface is responsive on tablet (768px-1024px)
- **And:** Interface is responsive on mobile (<768px)
- **And:** Touch targets are appropriately sized (minimum 44x44px)
- **And:** No horizontal scrolling required

### AC6: Accessibility
- **Given:** User navigates the interface
- **Then:** WCAG AA contrast ratios are met (4.5:1 minimum for normal text)
- **And:** Keyboard navigation works for all interactive elements
- **And:** Focus indicators are visible on all focusable elements
- **And:** Lighthouse accessibility score is >90

### AC7: Browser Compatibility
- **Given:** User accesses the interface from different browsers
- **Then:** Interface works correctly on Chrome (latest 2 versions)
- **And:** Interface works correctly on Safari (latest 2 versions)
- **And:** Interface works correctly on Firefox (latest 2 versions)

---

## 🏗️ TECHNICAL IMPLEMENTATION

### Frontend Stack

**Technology Decisions:**
- **Framework:** Next.js 14 (App Router, Server Components)
- **Runtime:** React 18
- **Styling:** Tailwind CSS 3.4+ with custom Manus theme
- **Language:** TypeScript (strict mode)
- **Package Manager:** npm

### Manus Theme Specification

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'manus': {
          'bg': '#0F172A',        // Deep navy background
          'surface': '#1E293B',   // Elevated surface
          'accent': '#2563EB',    // Primary blue
          'text': '#E2E8F0',      // Light gray text
          'muted': '#64748B',     // Muted text
          'border': '#334155',    // Border color
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      }
    }
  }
}
```

### Key Components to Implement

#### 1. Main Chat Page (`src/app/page.tsx`)
```typescript
interface ChatPageProps {
  searchParams: { conversationId?: string };
}

export default function ChatPage({ searchParams }: ChatPageProps) {
  return (
    <main className="h-screen flex flex-col bg-manus-bg">
      <Header />
      <ChatInterface conversationId={searchParams.conversationId} />
    </main>
  );
}
```

#### 2. Chat Interface Component (`src/components/ChatInterface.tsx`)
```typescript
interface ChatInterfaceProps {
  conversationId?: string;
}

export function ChatInterface({ conversationId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // Implementation in Story 2.4 (Streaming)
  const handleSubmit = useCallback(async (message: string) => {
    // Stream message handling
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <MessageList messages={messages} />
      <InputBox
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={isStreaming}
      />
    </div>
  );
}
```

#### 3. Header Component (`src/components/Header.tsx`)
- Logo/branding
- Navigation (if needed)
- User menu (placeholder for auth)

#### 4. Message List Component (`src/components/MessageList.tsx`)
- Display conversation history
- Auto-scroll to latest message
- Virtual scrolling for performance (react-window)

#### 5. Input Box Component (`src/components/InputBox.tsx`)
- Text input with auto-resize
- Send button
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)

### Responsive Design Breakpoints

- **Desktop (>1024px):** Full-width single column, max 900px centered
- **Tablet (768px-1024px):** Full-width with adjusted padding
- **Mobile (<768px):** Full viewport, optimized touch targets

### Accessibility Requirements

1. **Contrast Ratios:**
   - Normal text (16px): 4.5:1 minimum
   - Large text (24px+): 3:1 minimum
   - All Manus color combinations must meet WCAG AA

2. **Keyboard Navigation:**
   - Tab through all interactive elements
   - Enter/Space to activate buttons
   - Escape to close modals/dropdowns
   - Arrow keys for navigation where appropriate

3. **Screen Reader Support:**
   - Semantic HTML (main, nav, article, section)
   - ARIA labels for icon buttons
   - Proper heading hierarchy (h1, h2, h3)

4. **Focus Indicators:**
   - Visible focus ring on all focusable elements
   - Custom styling to match Manus theme

---

## 📁 FILES TO CREATE/MODIFY

### Core Files to Create

1. **`suna/src/app/page.tsx`** - Main chat page
2. **`suna/src/app/layout.tsx`** - Root layout with Manus theme
3. **`suna/src/components/ChatInterface.tsx`** - Core chat component
4. **`suna/src/components/Header.tsx`** - Header/navigation
5. **`suna/src/components/MessageList.tsx`** - Message display
6. **`suna/src/components/InputBox.tsx`** - Input component
7. **`suna/src/styles/globals.css`** - Global styles + Manus theme
8. **`suna/tailwind.config.js`** - Tailwind configuration with Manus colors
9. **`suna/next.config.js`** - Next.js configuration

### Configuration Files to Modify

1. **`suna/package.json`** - Add dependencies:
   ```json
   {
     "dependencies": {
       "next": "^14.0.0",
       "react": "^18.0.0",
       "react-dom": "^18.0.0",
       "tailwindcss": "^3.4.0",
       "@tailwindcss/typography": "^0.5.10",
       "react-window": "^1.8.10"
     },
     "devDependencies": {
       "typescript": "^5.3.0",
       "@types/react": "^18.0.0",
       "@types/react-dom": "^18.0.0",
       "eslint": "^8.0.0",
       "eslint-config-next": "^14.0.0"
     }
   }
   ```

2. **`suna/tsconfig.json`** - TypeScript strict mode configuration

3. **`docker/Dockerfile.suna`** - Docker image for production build

4. **`docker-compose.yaml`** - Add Suna service:
   ```yaml
   services:
     suna:
       build:
         context: ./suna
         dockerfile: ../docker/Dockerfile.suna
       ports:
         - "3000:3000"
       environment:
         NEXT_PUBLIC_API_BASE: "/"
       depends_on:
         - postgres
         - redis
   ```

---

## 🧪 TESTING REQUIREMENTS

### Unit Tests

Create tests for each component:

```typescript
// __tests__/components/ChatInterface.test.tsx
describe('ChatInterface', () => {
  it('renders without crashing', () => {
    render(<ChatInterface />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('displays empty state when no messages', () => {
    render(<ChatInterface />);
    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });

  it('handles user input correctly', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'Test message');
    expect(input).toHaveValue('Test message');
  });
});
```

### Integration Tests

```typescript
// __tests__/integration/chat-page.test.tsx
describe('Chat Page', () => {
  it('loads and renders complete chat interface', () => {
    render(<ChatPage searchParams={{}} />);

    expect(screen.getByRole('banner')).toBeInTheDocument(); // Header
    expect(screen.getByRole('main')).toBeInTheDocument(); // Chat interface
    expect(screen.getByRole('textbox')).toBeInTheDocument(); // Input box
  });

  it('applies Manus theme correctly', () => {
    render(<ChatPage searchParams={{}} />);

    const main = screen.getByRole('main');
    expect(main).toHaveClass('bg-manus-bg');
  });
});
```

### E2E Tests (Playwright)

```typescript
// __tests__/e2e/chat-ui.e2e.ts
import { test, expect } from '@playwright/test';

test('chat interface loads successfully', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Check page loads
  await expect(page).toHaveTitle(/ONYX/i);

  // Check theme applied
  const main = page.locator('main');
  await expect(main).toHaveCSS('background-color', 'rgb(15, 23, 42)'); // #0F172A

  // Check Inter font loaded
  await expect(page.locator('body')).toHaveCSS('font-family', /Inter/);
});

test('chat interface is responsive', async ({ page }) => {
  // Desktop
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('http://localhost:3000');
  await expect(page.locator('main')).toBeVisible();

  // Tablet
  await page.setViewportSize({ width: 768, height: 1024 });
  await expect(page.locator('main')).toBeVisible();

  // Mobile
  await page.setViewportSize({ width: 375, height: 667 });
  await expect(page.locator('main')).toBeVisible();
});

test('accessibility checks pass', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Run Lighthouse accessibility audit
  // (Requires @playwright/test with lighthouse plugin)
  // Score should be >90
});
```

### Manual Testing Checklist

- [ ] Page loads in <2s on localhost
- [ ] All Manus colors render correctly
- [ ] Inter font is applied everywhere
- [ ] Layout is centered and responsive
- [ ] Works on Chrome (latest)
- [ ] Works on Safari (latest)
- [ ] Works on Firefox (latest)
- [ ] Mobile view looks good on iPhone
- [ ] Mobile view looks good on Android
- [ ] Tablet view looks good on iPad
- [ ] Keyboard navigation works
- [ ] Focus indicators are visible
- [ ] No console errors
- [ ] No accessibility warnings
- [ ] Lighthouse score >90 for accessibility

---

## 🔍 VERIFICATION CHECKLIST

Before marking this story as complete, verify:

### Development Environment
- [ ] `npm install` runs without errors
- [ ] `npm run dev` starts development server successfully
- [ ] No TypeScript compilation errors
- [ ] No ESLint warnings or errors
- [ ] Hot module replacement works correctly

### Build & Production
- [ ] `npm run build` completes successfully
- [ ] `npm run start` serves production build
- [ ] Docker image builds successfully
- [ ] Docker container runs without errors
- [ ] Environment variables are properly configured

### Visual & UX
- [ ] All Manus colors match specification
- [ ] Inter font loads and displays correctly
- [ ] Layout matches design requirements
- [ ] No layout shifts or visual glitches
- [ ] Responsive design works on all breakpoints
- [ ] Touch targets meet minimum size on mobile

### Accessibility
- [ ] Lighthouse accessibility score >90
- [ ] WCAG AA contrast ratios verified
- [ ] Keyboard navigation functional
- [ ] Focus indicators visible
- [ ] Screen reader compatible

### Performance
- [ ] Initial page load <2s
- [ ] Time to Interactive <3s
- [ ] Largest Contentful Paint <2.5s
- [ ] Cumulative Layout Shift <0.1
- [ ] First Input Delay <100ms

### Browser Testing
- [ ] Chrome: All features work
- [ ] Safari: All features work
- [ ] Firefox: All features work
- [ ] Mobile Chrome: All features work
- [ ] Mobile Safari: All features work

---

## 📝 IMPLEMENTATION NOTES

### Development Approach

1. **Start with Next.js setup:**
   - Use `create-next-app` with TypeScript and Tailwind
   - Configure App Router (not Pages Router)
   - Set up strict TypeScript configuration

2. **Configure Manus theme:**
   - Create custom Tailwind theme with Manus colors
   - Add Inter font from Google Fonts
   - Configure global styles

3. **Build component structure:**
   - Start with layout and page structure
   - Build components from outside-in (layout → interface → components)
   - Use TypeScript interfaces for all props

4. **Implement responsive design:**
   - Mobile-first approach
   - Test at multiple breakpoints
   - Use Tailwind responsive utilities

5. **Ensure accessibility:**
   - Use semantic HTML
   - Add ARIA labels where needed
   - Test keyboard navigation
   - Run Lighthouse audits

### Potential Challenges

1. **Font loading performance:**
   - Solution: Use Next.js Font Optimization
   - Preload Inter font in layout
   - Consider using font-display: swap

2. **Tailwind configuration complexity:**
   - Solution: Use Tailwind's extend feature
   - Keep custom theme organized
   - Document color usage

3. **Responsive design edge cases:**
   - Solution: Test on real devices
   - Use browser dev tools for various screen sizes
   - Consider tablet landscape orientation

4. **Accessibility compliance:**
   - Solution: Use automated tools (axe, Lighthouse)
   - Manual keyboard testing
   - Consider screen reader testing

---

## 🔗 RELATED STORIES

### Blockers (Must Complete Before)
- ✅ Story 1.1: Project Setup & Repository Initialization

### Blocked By This Story
- Story 2.2: LiteLLM Proxy Setup & Model Routing
- Story 2.3: Message History & Persistence
- Story 2.4: Message Streaming & Real-Time Response Display

### Related Documentation
- [Epic 2 Tech Spec](../docs/epics/epic-2-tech-spec.md)
- [Architecture Document](../docs/architecture.md)
- [PRD](../docs/PRD.md)

---

## 📚 REFERENCE MATERIALS

### Manus Theme Colors
```css
:root {
  --manus-bg: #0F172A;        /* Deep navy background */
  --manus-surface: #1E293B;   /* Elevated surface */
  --manus-accent: #2563EB;    /* Primary blue */
  --manus-text: #E2E8F0;      /* Light gray text */
  --manus-muted: #64748B;     /* Muted text */
  --manus-border: #334155;    /* Border color */
}
```

### Inter Font Configuration
```typescript
// next.config.js or layout.tsx
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});
```

### Accessibility Resources
- [WCAG 2.1 AA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Next.js Accessibility Best Practices](https://nextjs.org/docs/accessibility)

---

## ✅ DEFINITION OF DONE

This story is considered complete when:

1. **Code Complete:**
   - [ ] All components implemented
   - [ ] All tests passing
   - [ ] No TypeScript errors
   - [ ] No ESLint warnings

2. **Quality Standards:**
   - [ ] Code reviewed and approved
   - [ ] Test coverage >80%
   - [ ] Lighthouse performance score >90
   - [ ] Lighthouse accessibility score >90

3. **Documentation:**
   - [ ] Component documentation written
   - [ ] README updated with setup instructions
   - [ ] CHANGELOG updated

4. **Deployment:**
   - [ ] Docker image builds successfully
   - [ ] Deployed to development environment
   - [ ] Smoke tests pass

5. **Acceptance:**
   - [ ] All acceptance criteria met
   - [ ] Manual testing completed
   - [ ] Product owner approval

---

**Created:** 2025-11-13
**Last Updated:** 2025-11-13
**Assigned To:** Frontend Developer
**Reviewed By:** Technical Architect
