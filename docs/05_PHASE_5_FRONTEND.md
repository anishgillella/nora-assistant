# Phase 5: Frontend Development

## 🎯 Objectives

1. Build Chat Interface with streaming support
2. Create Product Cards for recommendations
3. Implement History Timeline view
4. Build Stats Dashboard
5. Connect to Backend API

---

## 🧩 Components

### 1. Chat Interface (`ChatInterface.tsx`)
- **State:** `messages`, `isLoading`, `input`
- **Features:**
  - Auto-scroll to bottom
  - Markdown rendering for bot responses
  - Source citations display
  - Streaming text effect

### 2. Product Card (`ProductCard.tsx`)
- **Props:** `Product` object
- **Display:** Image, Title, Price, Store, "Why Recommended" badge
- **Action:** Click to view original URL

### 3. History Timeline (`HistoryTimeline.tsx`)
- **Display:** List of browsing history items grouped by date
- **Features:** Filter by category, search

### 4. Stats Dashboard (`StatsPanel.tsx`)
- **Display:**
  - Total items tracked
  - Top categories (Pie chart or list)
  - Favorite brands

---

## 🎨 UI/UX Design

- **Theme:** Clean, modern, "Nora-like" aesthetic
- **Colors:** Neutral grays, accent blue/purple for AI actions
- **Typography:** Inter or system sans-serif
- **Layout:**
  - Sidebar: History/Stats
  - Main: Chat Interface
  - Right Panel (Optional): Product Details

---

## 🔌 Integration

### API Client (`api.ts`)

```typescript
export const sendMessage = async (message: string, onToken: (token: string) => void) => {
    const response = await fetch(`${API_URL}/api/chat/message`, {
        method: 'POST',
        body: JSON.stringify({ message }),
        // ... headers
    });
    
    // Handle SSE stream
    const reader = response.body.getReader();
    // ... decode and callback onToken
};
```

---

## 🧪 Testing

1. **Component Tests:** Render Chat, ProductCard
2. **Integration Tests:** Verify API calls
3. **User Flow:**
   - Send message -> See stream -> See sources
   - Click "Ingest" -> See stats update
