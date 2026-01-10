# Frontend Guide for Beginners

This guide explains the **React frontend** from scratch - perfect if you've never worked with React, Vite, TypeScript, or Tailwind before.

---

## 📚 Table of Contents

1. [Technology Overview](#technology-overview)
2. [What is React?](#what-is-react)
3. [What is Vite?](#what-is-vite)
4. [What is TypeScript?](#what-is-typescript)
5. [What is Tailwind CSS?](#what-is-tailwind-css)
6. [Project Structure](#project-structure)
7. [Understanding Components](#understanding-components)
8. [State Management](#state-management)
9. [API Communication](#api-communication)
10. [Building and Deployment](#building-and-deployment)

---

## Technology Overview

Our frontend uses these technologies:

| Technology | Purpose | Why We Use It |
|------------|---------|---------------|
| **React** | UI Framework | Component-based, efficient updates |
| **Vite** | Build Tool | Super fast development server |
| **TypeScript** | Language | Type safety, better IDE support |
| **Tailwind CSS** | Styling | Utility-first, fast styling |
| **Zustand** | State Management | Simple, lightweight |
| **Axios** | HTTP Client | API requests |

---

## What is React?

### The Problem React Solves

**Without React** (plain JavaScript):
```javascript
// When data changes, manually update DOM
function updateUser(name) {
    document.getElementById('user-name').innerText = name;
    document.getElementById('user-greeting').innerText = 'Hello, ' + name;
    document.getElementById('user-badge').setAttribute('title', name);
    // ... update every place that shows the name
}
```

**With React**:
```jsx
// Just update state, React handles the DOM
function UserCard({ name }) {
    return (
        <div>
            <span id="user-name">{name}</span>
            <span id="user-greeting">Hello, {name}</span>
            <div id="user-badge" title={name}>...</div>
        </div>
    );
}
// Change `name` → React updates all places automatically!
```

### Key React Concepts

#### 1. Components

Components are **reusable pieces of UI**. Think of them as custom HTML tags.

```tsx
// A simple component
function Greeting() {
    return <h1>Hello, World!</h1>;
}

// Using it
<Greeting />

// Component with data (props)
function Greeting({ name }) {
    return <h1>Hello, {name}!</h1>;
}

// Using it
<Greeting name="Alice" />
```

#### 2. Props (Properties)

Props are how you pass data TO a component (like function arguments).

```tsx
// Parent passes data via props
<UserCard name="Alice" age={25} isAdmin={true} />

// Child receives props
function UserCard({ name, age, isAdmin }) {
    return (
        <div>
            <h2>{name}</h2>
            <p>Age: {age}</p>
            {isAdmin && <span>Admin</span>}
        </div>
    );
}
```

#### 3. State

State is data that can **change** and trigger re-renders.

```tsx
import { useState } from 'react';

function Counter() {
    // useState returns [currentValue, setterFunction]
    const [count, setCount] = useState(0);
    
    return (
        <div>
            <p>Count: {count}</p>
            <button onClick={() => setCount(count + 1)}>
                Increment
            </button>
        </div>
    );
}
```

#### 4. JSX

JSX is HTML-like syntax in JavaScript. It gets converted to regular JavaScript.

```tsx
// JSX
const element = <h1 className="title">Hello</h1>;

// Gets converted to:
const element = React.createElement('h1', {className: 'title'}, 'Hello');
```

**JSX Rules:**
- Use `className` instead of `class`
- Use `{}` for JavaScript expressions
- All tags must be closed (`<br />` not `<br>`)
- Return single root element (or use `<>...</>` fragment)

---

## What is Vite?

### The Problem Vite Solves

**Old tools** (Webpack):
- Bundle everything before serving
- Slow startup (minutes for large apps)
- Slow updates (seconds)

**Vite**:
- Serves source files directly (ES modules)
- Instant startup
- Instant updates (HMR - Hot Module Replacement)

### How Vite Works

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT                              │
│                                                             │
│  Your Browser ◀──── Vite Dev Server ◀──── Source Files     │
│                    (transforms on demand)                   │
│                                                             │
│  Change a file → Only that file is updated → Instant!       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION                               │
│                                                             │
│  Source Files ──▶ Vite Build ──▶ Optimized Bundle          │
│                  (Rollup)        (minified, split)          │
└─────────────────────────────────────────────────────────────┘
```

### Vite Configuration (`vite.config.ts`)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],      // Enable React support
  server: {
    port: 5173,            // Dev server port
    proxy: {
      '/api': {            // Proxy API requests to backend
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

### Common Vite Commands

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
```

---

## What is TypeScript?

### The Problem TypeScript Solves

**JavaScript** (no types):
```javascript
function greet(name) {
    return "Hello, " + name.toUpperCase();
}

greet("Alice");  // Works
greet(42);       // Runtime Error! 42.toUpperCase is not a function
```

**TypeScript** (with types):
```typescript
function greet(name: string): string {
    return "Hello, " + name.toUpperCase();
}

greet("Alice");  // Works
greet(42);       // Compile Error! Caught before running
```

### Basic TypeScript Syntax

```typescript
// Basic types
let name: string = "Alice";
let age: number = 25;
let isAdmin: boolean = true;
let items: string[] = ["a", "b", "c"];

// Object types
interface User {
    name: string;
    age: number;
    email?: string;  // Optional (?)
}

const user: User = {
    name: "Alice",
    age: 25
};

// Function types
function add(a: number, b: number): number {
    return a + b;
}

// React component with types
interface Props {
    title: string;
    count: number;
}

function Counter({ title, count }: Props) {
    return <div>{title}: {count}</div>;
}
```

### TypeScript Configuration (`tsconfig.json`)

```json
{
  "compilerOptions": {
    "target": "ES2020",           // JavaScript version to output
    "jsx": "react-jsx",           // Enable JSX for React
    "strict": true,               // Enable all strict checks
    "moduleResolution": "bundler" // How to find modules
  },
  "include": ["src"]              // Files to compile
}
```

---

## What is Tailwind CSS?

### The Problem Tailwind Solves

**Traditional CSS** (separate files, custom classes):
```css
/* styles.css */
.card {
    background-color: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.card-title {
    font-size: 18px;
    font-weight: bold;
    color: #333;
}
```
```html
<div class="card">
    <h2 class="card-title">Hello</h2>
</div>
```

**Tailwind CSS** (utility classes directly in HTML):
```html
<div class="bg-white rounded-lg p-4 shadow-md">
    <h2 class="text-lg font-bold text-gray-800">Hello</h2>
</div>
```

### How Tailwind Works

Tailwind provides **utility classes** for every CSS property:

| Utility Class | CSS Property |
|--------------|--------------|
| `bg-white` | `background-color: white` |
| `text-lg` | `font-size: 1.125rem` |
| `p-4` | `padding: 1rem` |
| `rounded-lg` | `border-radius: 0.5rem` |
| `flex` | `display: flex` |
| `mt-2` | `margin-top: 0.5rem` |

### Common Tailwind Patterns

```tsx
// Flexbox layout
<div className="flex items-center justify-between">

// Grid
<div className="grid grid-cols-3 gap-4">

// Responsive (mobile-first)
<div className="text-sm md:text-base lg:text-lg">
    {/* text-sm on mobile, text-base on medium+, text-lg on large+ */}
</div>

// Hover states
<button className="bg-blue-500 hover:bg-blue-600">

// Dark mode
<div className="bg-white dark:bg-gray-900">

// Conditional classes
<div className={`p-4 ${isActive ? 'bg-green-500' : 'bg-gray-500'}`}>
```

### Tailwind Configuration (`tailwind.config.js`)

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",  // Scan these files for classes
  ],
  theme: {
    extend: {
      colors: {
        midnight: {
          900: '#102a43',  // Custom color
        },
        electric: {
          400: '#38b2ac',  // Custom color
        },
      },
    },
  },
}
```

---

## Project Structure

```
frontend/
│
├── index.html                # HTML entry point
│   │                         # Vite injects scripts here
│   │
├── src/
│   │
│   ├── main.tsx              # React entry point
│   │   │                     # Renders <App /> into DOM
│   │   │
│   │   └── ReactDOM.createRoot(document.getElementById('root')).render(<App />)
│   │
│   ├── App.tsx               # Main application component
│   │   │                     # Contains layout, navigation, routing
│   │   │
│   │   └── function App() {
│   │         return (
│   │           <div>
│   │             <Sidebar />
│   │             <MainContent />
│   │           </div>
│   │         );
│   │       }
│   │
│   ├── index.css             # Global styles + Tailwind imports
│   │   │
│   │   └── @tailwind base;
│   │       @tailwind components;
│   │       @tailwind utilities;
│   │
│   ├── components/           # Reusable UI components
│   │   ├── QueryChat.tsx     # Chat interface
│   │   ├── DocumentUpload.tsx# File upload
│   │   ├── GraphViz...tsx    # Graph visualization
│   │   ├── ExtractionPanel.tsx # Extraction status
│   │   └── HealthStatus.tsx  # System health display
│   │
│   ├── services/
│   │   └── api.ts            # API client
│   │       │                 # Axios instance + API functions
│   │       │
│   │       └── export const queryAPI = {
│   │             ask: (question) => axios.post('/query/ask', { question }),
│   │           };
│   │
│   └── store/
│       └── index.ts          # Global state (Zustand)
│           │
│           └── export const useAppStore = create((set) => ({
│                 messages: [],
│                 addMessage: (msg) => set((state) => ({
│                   messages: [...state.messages, msg]
│                 })),
│               }));
│
├── package.json              # Dependencies + scripts
├── vite.config.ts            # Vite configuration
├── tailwind.config.js        # Tailwind configuration
└── tsconfig.json             # TypeScript configuration
```

---

## Understanding Components

### Anatomy of a Component

```tsx
// 1. IMPORTS
import { useState, useEffect } from 'react';  // React hooks
import { motion } from 'framer-motion';        // Animation library
import { useAppStore } from '../store';        // Global state
import { queryAPI } from '../services/api';    // API functions

// 2. TYPES/INTERFACES
interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant';
}

// 3. COMPONENT FUNCTION
export default function QueryChat() {
    // 3a. STATE
    const [input, setInput] = useState('');           // Local state
    const { messages, addMessage } = useAppStore();   // Global state
    
    // 3b. EFFECTS (run on mount/update)
    useEffect(() => {
        // Runs when component mounts
        console.log('Component mounted');
        
        return () => {
            // Cleanup when component unmounts
            console.log('Component unmounted');
        };
    }, []);  // Empty array = run once on mount
    
    // 3c. EVENT HANDLERS
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const response = await queryAPI.ask(input);
        addMessage({ content: response.answer, role: 'assistant' });
    };
    
    // 3d. RENDER
    return (
        <div className="flex flex-col h-full">
            {/* Message list */}
            <div className="flex-1 overflow-y-auto">
                {messages.map((msg) => (
                    <div key={msg.id} className="p-4">
                        {msg.content}
                    </div>
                ))}
            </div>
            
            {/* Input form */}
            <form onSubmit={handleSubmit}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a question..."
                />
                <button type="submit">Send</button>
            </form>
        </div>
    );
}
```

### Component Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     COMPONENT LIFECYCLE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. MOUNT                                                   │
│     │                                                       │
│     ├─▶ Component function runs                             │
│     ├─▶ Initial state created (useState)                    │
│     ├─▶ JSX returned and rendered to DOM                    │
│     └─▶ useEffect runs (after render)                       │
│                                                             │
│  2. UPDATE (state or props change)                          │
│     │                                                       │
│     ├─▶ Component function runs again                       │
│     ├─▶ New JSX compared to old (diffing)                  │
│     ├─▶ Only changed parts update in DOM                    │
│     └─▶ useEffect runs if dependencies changed              │
│                                                             │
│  3. UNMOUNT                                                 │
│     │                                                       │
│     └─▶ useEffect cleanup function runs                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

### Local State (useState)

For state used only within one component:

```tsx
function Counter() {
    const [count, setCount] = useState(0);
    
    return (
        <button onClick={() => setCount(count + 1)}>
            Clicked {count} times
        </button>
    );
}
```

### Global State (Zustand)

For state shared across multiple components:

```tsx
// store/index.ts
import { create } from 'zustand';

interface AppState {
    messages: Message[];
    isLoading: boolean;
    addMessage: (msg: Message) => void;
    setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
    // Initial state
    messages: [],
    isLoading: false,
    
    // Actions (functions that update state)
    addMessage: (msg) => set((state) => ({
        messages: [...state.messages, msg]
    })),
    
    setLoading: (loading) => set({ isLoading: loading }),
}));

// Using in component:
function QueryChat() {
    const { messages, addMessage, isLoading } = useAppStore();
    // ...
}
```

### When to Use Which

| Scenario | Solution |
|----------|----------|
| Form input value | Local state (`useState`) |
| Toggle/modal open | Local state |
| User authentication | Global state (Zustand) |
| Chat messages | Global state |
| Theme preference | Global state |

---

## API Communication

### API Client (`services/api.ts`)

```typescript
import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
    baseURL: 'http://localhost:8000',
});

// Define API functions
export const queryAPI = {
    ask: async (question: string) => {
        const response = await api.post('/query/ask', {
            question,
            include_follow_ups: true,
        });
        return response.data;
    },
};

export const uploadAPI = {
    uploadDocument: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await api.post('/upload/document', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },
};
```

### Using API in Components

```tsx
import { queryAPI } from '../services/api';

function QueryChat() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const handleSubmit = async (question: string) => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await queryAPI.ask(question);
            // Handle success
            addMessage(response);
        } catch (err) {
            // Handle error
            setError('Failed to get response');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            {loading && <p>Loading...</p>}
            {error && <p className="text-red-500">{error}</p>}
            {/* rest of component */}
        </div>
    );
}
```

---

## Building and Deployment

### Development

```bash
cd frontend
npm install       # Install dependencies
npm run dev       # Start dev server at http://localhost:5173
```

### Production Build

```bash
npm run build     # Creates optimized files in dist/
```

Output:
```
dist/
├── index.html        # Entry point
├── assets/
│   ├── index-abc123.js   # Bundled JavaScript
│   └── index-xyz789.css  # Bundled CSS
```

### Docker Deployment

The `Dockerfile` creates a production container:

```dockerfile
# Build stage
FROM node:20-alpine as build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Nginx Configuration

Nginx serves the built files and proxies API requests:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    
    # Serve React app
    location / {
        try_files $uri $uri/ /index.html;  # SPA routing
    }
    
    # Proxy API to backend
    location /api/ {
        proxy_pass http://backend:8000/;
    }
}
```

---

## Quick Reference

### React Hooks

| Hook | Purpose |
|------|---------|
| `useState` | Local component state |
| `useEffect` | Side effects (API calls, subscriptions) |
| `useRef` | DOM references, mutable values |
| `useMemo` | Expensive calculations caching |
| `useCallback` | Function memoization |

### Common Tailwind Classes

| Class | Effect |
|-------|--------|
| `flex` | Display flex |
| `flex-col` | Flex direction column |
| `items-center` | Align items center |
| `justify-between` | Space between |
| `p-4` | Padding 1rem |
| `m-2` | Margin 0.5rem |
| `text-lg` | Large text |
| `font-bold` | Bold text |
| `rounded-lg` | Border radius |
| `shadow-md` | Medium shadow |

### File Naming Conventions

| File | Convention |
|------|------------|
| Components | `PascalCase.tsx` (e.g., `QueryChat.tsx`) |
| Utilities | `camelCase.ts` (e.g., `formatDate.ts`) |
| Constants | `SCREAMING_SNAKE_CASE` |
| CSS | `kebab-case.css` |

---

## Next Steps

1. **Try modifying a component** - Change text or styling in `QueryChat.tsx`
2. **Add console logs** - Understand when renders happen
3. **Explore React DevTools** - Install browser extension
4. **Read Tailwind docs** - https://tailwindcss.com/docs
5. **Read React docs** - https://react.dev/learn
