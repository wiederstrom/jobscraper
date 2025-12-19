# Lovable Frontend Prompts for Job Scraper

This document contains structured prompts for building the React frontend using Lovable.dev.

## Project Overview

A modern job search dashboard for Norwegian tech jobs scraped from FINN.no and NAV.no. The backend API is already built with FastAPI and deployed. The frontend needs to provide filtering, search, favorites management, application tracking, and statistics.

---

## Prompt 1: Initial Project Setup & API Integration

```
Create a modern React job board application with the following requirements:

**Tech Stack:**
- React with TypeScript
- Tailwind CSS for styling
- shadcn/ui components
- TanStack Query (React Query) for API calls
- Axios for HTTP requests

**API Configuration:**
Base URL: Will be provided via environment variable
API Prefix: /api/v1

**API Endpoints to integrate:**
1. GET /api/v1/jobs - List jobs with filters
2. GET /api/v1/jobs/{id} - Get single job
3. PATCH /api/v1/jobs/{id} - Update job metadata
4. DELETE /api/v1/jobs/{id} - Hide job
5. GET /api/v1/stats - Get statistics

**Types to create (TypeScript):**
```typescript
interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  summary: string;
  source: 'FINN' | 'NAV';
  scraped_date: string;
  is_favorite: boolean;
  is_hidden: boolean;
  applied: boolean;
  applied_date: string | null;
  notes: string;
  status: 'ACTIVE' | 'INACTIVE' | 'EXPIRED';
}

interface JobStatistics {
  total_jobs: number;
  favorites: number;
  applied: number;
  sources: {
    FINN: number;
    NAV: number;
  };
  status: {
    ACTIVE: number;
    INACTIVE: number;
    EXPIRED: number;
  };
  new_last_7_days: number;
}
```

**Initial UI:**
Create a clean, modern layout with:
- Header with app title "Tech Jobs Norway"
- Sidebar for filters and statistics
- Main content area for job listings
- Responsive design (mobile-first)

Use a professional color scheme suitable for a job board (blues/grays).
```

---

## Prompt 2: Job List Component & Cards

```
Create the main job listing view with the following features:

**Job Card Component:**
Display each job as a card with:
- Job title (large, bold)
- Company name with location
- Source badge (FINN or NAV) with different colors
- Scraped date (relative time: "2 days ago")
- Summary text (truncated to 3 lines with "Read more")
- Action buttons:
  - Favorite (heart icon, filled if favorited)
  - Applied (checkmark icon, green if applied)
  - Hide (eye-slash icon)
  - View details (arrow icon)

**Visual States:**
- Applied jobs: Green border on left side
- Favorite jobs: Yellow star in top-right corner
- Hover state: Subtle shadow and scale
- Applied date shown if applied: "Applied on {date}"

**List View:**
- Grid layout: 1 column mobile, 2 columns tablet, 3 columns desktop
- Infinite scroll or pagination (100 items per page)
- Loading skeleton cards while fetching
- Empty state: "No jobs found" with illustration

**Interactions:**
- Click card to open job details modal
- Click favorite to toggle (optimistic update)
- Click applied to toggle with confirmation
- Click hide with "Are you sure?" dialog
- Click external link icon to open job URL in new tab

Use shadcn/ui Card, Badge, Button components.
```

---

## Prompt 3: Filters & Search Sidebar

```
Create a collapsible sidebar with filtering and search:

**Search Bar:**
- Text input with search icon
- Placeholder: "Search jobs by title, company, or description..."
- Debounced search (500ms delay)
- Clear button (X) when text entered

**Filters Section:**
Organized in collapsible accordions:

1. **Source Filter:**
   - Checkboxes: FINN, NAV
   - Show count next to each: "FINN (45)"

2. **Status Filter:**
   - Radio buttons: All, Active, Applied, Favorites
   - Default: Active

3. **Applied Status:**
   - Toggle: "Show only unapplied jobs"

4. **Date Range:**
   - Dropdown: Last 7 days, Last 30 days, Last 3 months, All time
   - Default: All time

**Active Filters Display:**
- Show active filters as chips above job list
- Each chip has X to remove filter
- "Clear all" button if multiple filters active

**Mobile Behavior:**
- Sidebar hidden by default
- Filter button in header opens drawer
- Filters displayed in bottom sheet

Use shadcn/ui Accordion, Checkbox, RadioGroup, Select components.
```

---

## Prompt 4: Statistics Dashboard Card

```
Create a statistics summary card in the sidebar:

**Card Layout:**
Title: "Statistics"

**Metrics to display:**
1. Total Jobs - Large number with label
2. Favorites - Star icon + count
3. Applied - Checkmark icon + count
4. New (Last 7 days) - Badge with "New" + count

**Source Breakdown:**
- Mini bar chart or progress bars showing FINN vs NAV split
- Show percentage: "FINN: 45 (73%)"

**Status Breakdown:**
- Color-coded dots:
  - Active (green)
  - Inactive (gray)
  - Expired (red)
- Show counts next to each

**Visual Design:**
- Use icons from lucide-react
- Subtle background colors for each metric
- Responsive grid: 2x2 on mobile, 4x1 on desktop
- Auto-refresh every 30 seconds

**Loading State:**
- Skeleton loaders for numbers
- Smooth transition when data loads

Use shadcn/ui Card, Skeleton components.
```

---

## Prompt 5: Job Details Modal

```
Create a modal/drawer for displaying full job details:

**Modal Header:**
- Job title (H2)
- Company name with location icon
- Source badge (FINN/NAV)
- Close button (X)

**Action Bar:**
Three toggle buttons:
1. Favorite (heart icon) - Yellow when active
2. Applied (checkmark icon) - Green when active
3. Hide (eye-slash icon) - Confirm before hiding

**Content Sections:**
Tabs for organization:

**Tab 1: Details**
- Full description (formatted HTML/markdown)
- Scraped date
- Last checked date
- Status badge (Active/Inactive/Expired)
- External link button: "View on {source}" (opens in new tab)

**Tab 2: Summary**
- AI-generated Norwegian summary
- Icon indicating AI-generated content
- "Show original description" link

**Tab 3: Notes**
- Textarea for personal notes
- Autosave after 2 seconds of no typing
- Character count
- Last updated timestamp
- Placeholder: "Add your notes about this job..."

**Footer:**
- Applied date if applied: "Applied on {date}"
- Link to original job posting
- Share button (copy link to clipboard)

**Mobile Behavior:**
- Full-screen drawer on mobile
- Modal on desktop (max-width: 900px)
- Swipe down to close on mobile

Use shadcn/ui Dialog, Tabs, Textarea, Toggle components.
```

---

## Prompt 6: State Management & Optimistic Updates

```
Implement robust state management with React Query:

**Query Keys Structure:**
```typescript
const queryKeys = {
  jobs: {
    all: ['jobs'] as const,
    lists: () => [...queryKeys.jobs.all, 'list'] as const,
    list: (filters: JobFilters) => [...queryKeys.jobs.lists(), filters] as const,
    details: () => [...queryKeys.jobs.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.jobs.details(), id] as const,
  },
  stats: ['stats'] as const,
}
```

**Mutations with Optimistic Updates:**

1. **Toggle Favorite:**
   - Optimistically update job card
   - Show loading spinner on heart icon
   - Rollback on error with toast notification
   - Invalidate stats query

2. **Toggle Applied:**
   - Show confirmation dialog if marking as applied
   - Optimistically update with applied_date = now
   - Show success toast: "Marked as applied"
   - Green border animation on card
   - Invalidate stats query

3. **Add/Update Notes:**
   - Debounced autosave (2 seconds)
   - Show "Saving..." indicator
   - Show "Saved" checkmark when complete
   - Error toast if save fails

4. **Hide Job:**
   - Show confirmation dialog
   - Fade out animation
   - Remove from list after animation
   - Show undo toast (5 seconds)
   - Invalidate stats and list queries

**Error Handling:**
- Show toast notifications for all errors
- Retry failed mutations (max 2 retries)
- Network error: "Connection lost. Changes will sync when online."
- Server error: Show error message from API

**Polling:**
- Poll stats every 30 seconds (when tab is active)
- Pause polling when tab is hidden
- Use React Query's refetchInterval

Use TanStack Query mutations with onMutate, onError, onSettled.
```

---

## Prompt 7: Responsive Design & Animations

```
Polish the UI with responsive design and smooth animations:

**Responsive Breakpoints:**
- Mobile: < 640px (1 column)
- Tablet: 640px - 1024px (2 columns)
- Desktop: > 1024px (3 columns + sidebar)

**Layout Adjustments:**
- Mobile: Bottom navigation, filters in drawer
- Tablet: Side navigation, collapsible filters
- Desktop: Persistent sidebar, filters always visible

**Animations:**
1. **Card Entrance:**
   - Stagger animation (100ms delay between cards)
   - Fade in + slide up
   - Use Framer Motion or CSS animations

2. **Filter Changes:**
   - Smooth height transition when opening accordions
   - Cards fade out/in when filters change

3. **Status Updates:**
   - Favorite: Scale + color pulse
   - Applied: Green border slide-in from left
   - Hide: Fade out + scale down

4. **Modal:**
   - Backdrop fade in
   - Modal slide up from bottom (mobile) or scale in (desktop)
   - Spring animation for smooth feel

5. **Loading States:**
   - Skeleton cards with shimmer effect
   - Spinner for actions (favorite, applied)
   - Progress bar at top for background updates

**Accessibility:**
- Focus states on all interactive elements
- Keyboard navigation (Tab, Enter, Esc)
- ARIA labels for icon buttons
- Screen reader announcements for status changes

**Dark Mode Support:**
- Toggle in header
- Use CSS variables for theme colors
- Respect system preference by default
- Persist preference in localStorage

Use Framer Motion for animations, shadcn/ui theme system for dark mode.
```

---

## Prompt 8: Performance Optimizations

```
Optimize the application for performance:

**Code Splitting:**
- Lazy load job details modal
- Lazy load statistics charts
- Split by route if multiple pages

**Memoization:**
```typescript
// Memoize expensive computations
const filteredJobs = useMemo(() => {
  return applyFilters(jobs, filters);
}, [jobs, filters]);

// Memoize card components
const JobCard = memo(({ job }: { job: Job }) => {
  // Component code
});
```

**Virtual Scrolling:**
- Use @tanstack/react-virtual for job list
- Render only visible items + buffer
- Improves performance with 100+ jobs

**Image Optimization:**
- Lazy load company logos if added later
- Use blur placeholder for images
- Responsive images with srcset

**API Optimization:**
- Cache jobs list for 5 minutes (staleTime)
- Prefetch next page on scroll
- Debounce search input (500ms)
- Cancel pending requests on filter change

**Bundle Optimization:**
- Tree-shake unused dependencies
- Use import aliases for cleaner imports
- Minimize bundle with Vite/Webpack config

**Query Configuration:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 2,
    },
  },
});
```

Measure performance with Lighthouse and React DevTools Profiler.
```

---

## Prompt 9: Environment Setup & Deployment

```
Set up environment configuration and deployment:

**Environment Variables:**
Create `.env` file:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_VERSION=v1
```

Create `.env.production`:
```
VITE_API_BASE_URL=https://your-railway-app.railway.app
VITE_API_VERSION=v1
```

**API Client Setup:**
```typescript
// src/lib/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL}/api/${import.meta.env.VITE_API_VERSION}`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response?.status === 404) {
      toast.error('Resource not found');
    } else if (error.response?.status === 500) {
      toast.error('Server error. Please try again.');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**Build Configuration:**
- Vite for fast builds
- TypeScript strict mode
- ESLint + Prettier
- Path aliases (@/components, @/lib, etc.)

**Deployment:**
Platform recommendation: Vercel or Netlify

Deploy steps:
1. Connect GitHub repository
2. Set environment variables in dashboard
3. Build command: `npm run build`
4. Output directory: `dist`
5. Enable automatic deployments on push

**CORS Configuration:**
Note: Backend must allow frontend origin in CORS settings.
```

---

## Prompt 10: Testing & Error Boundaries

```
Add testing and error handling:

**Error Boundary Component:**
```typescript
// Wrap app in error boundary
<ErrorBoundary fallback={<ErrorFallback />}>
  <App />
</ErrorBoundary>
```

**Error Fallback:**
- Friendly error message
- "Reload page" button
- "Report issue" button (optional)
- Error details in dev mode only

**Loading States:**
1. **Initial Load:**
   - Full-page skeleton with app layout
   - Shimmer effect on cards

2. **Filter Changes:**
   - Keep existing cards visible
   - Overlay with opacity + spinner

3. **Action Feedback:**
   - Inline spinners for buttons
   - Toast notifications for success/error

**Empty States:**
1. **No Jobs:**
   - Illustration or icon
   - "No jobs found"
   - Suggestion: "Try adjusting your filters"

2. **No Favorites:**
   - Heart icon
   - "No favorites yet"
   - "Click ♥ on jobs to save them"

3. **No Applied:**
   - Checkmark icon
   - "You haven't applied to any jobs yet"

**Offline Support:**
- Show banner when offline: "You're offline. Some features may not work."
- Queue mutations when offline
- Sync when back online
- Use service worker for offline caching (optional)

**Toast Notifications:**
Use sonner or react-hot-toast for:
- Success: "Job marked as favorite"
- Error: "Failed to update job"
- Info: "Changes saved automatically"
- Warning: "You're viewing cached data"

Add accessibility attributes and keyboard shortcuts for power users.
```

---

## API Reference for Frontend Developers

### GET /api/v1/jobs

**Query Parameters:**
- `source`: "FINN" | "NAV" (optional)
- `keyword`: string (optional, searches in title/company/description)
- `search`: string (optional, full-text search)
- `is_favorite`: boolean (optional)
- `is_hidden`: boolean (optional, default: false)
- `applied`: boolean (optional)
- `status`: "ACTIVE" | "INACTIVE" | "EXPIRED" (optional)
- `skip`: number (optional, default: 0)
- `limit`: number (optional, default: 100, max: 1000)

**Response:**
```json
{
  "jobs": [...],
  "total": 156,
  "skip": 0,
  "limit": 100
}
```

### PATCH /api/v1/jobs/{id}

**Request Body:**
```json
{
  "is_favorite": true,
  "applied": true,
  "notes": "Great company culture"
}
```

**Response:** Updated job object

### DELETE /api/v1/jobs/{id}

**Response:**
```json
{
  "success": true,
  "message": "Job hidden successfully"
}
```

---

## Design Guidelines

**Color Palette:**
- Primary: Blue (#3B82F6)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- FINN Badge: Orange (#F97316)
- NAV Badge: Blue (#3B82F6)

**Typography:**
- Headings: Inter or similar sans-serif
- Body: System font stack for performance

**Spacing:**
- Consistent 4px grid system
- Card padding: 16px (mobile), 24px (desktop)
- Section gaps: 24px (mobile), 32px (desktop)

**Icons:**
- Use lucide-react throughout
- 20px for inline icons
- 24px for button icons

---

## Notes for Lovable

- All Norwegian text from the API (summary, description) should be displayed as-is
- The API is read-only for job data (title, company, etc.) - only metadata (favorite, applied, notes) can be updated
- Jobs are soft-deleted (is_hidden=true), not permanently removed
- The backend handles AI filtering and scraping - frontend just displays and manages
- Applied date is automatically set by backend when applied=true
- Statistics update in real-time when jobs are favorited/applied/hidden
