# Frontend Authentication System — Visual Guide

## 🗺️ User Journey Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANDING PAGE (/)                              │
│                                                                   │
│  🏛️ Sahayak — Last Mile Justice Navigator                       │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Hero Section                                             │   │
│  │ "Justice for All - Last Mile"                           │   │
│  │ [Sign Up Button]  [Login Button]                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Features:                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   🏠     │  │    ⚖️     │  │    ⏰     │  │   🔒     │       │
│  │ Shelter  │  │  Legal   │  │  24/7    │  │  Privacy │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                   │
│  About + Stats + Footer                                         │
└─────────────────────────────────────────────────────────────────┘
         ↓                                          ↓
    [Sign Up]                                  [Login]
         ↓                                          ↓
┌────────────────────────┐            ┌────────────────────────┐
│   SIGN UP PAGE (/signup)           │   LOGIN PAGE (/login)   │
│                        │            │                        │
│ Email Address: [_____] │            │ Email: [__________]    │
│ Password:      [_____] │            │ Password: [______]     │
│ Confirm:       [_____] │            │ [Sign In Button]       │
│ ☑️ Terms & Privacy     │            │                        │
│ [Create Account]       │            │ ─── or ───             │
│                        │            │ [Login Anonymously]    │
│ Already have account?  │            │                        │
│ [Sign in here]         │            │ No account?            │
│                        │            │ [Sign up here]         │
│                        │            │                        │
│ Sidebar: Help Info     │            │ Sidebar: Help Info     │
└────────────────────────┘            └────────────────────────┘
         ↓                                          ↓
    Firebase Auth                           Firebase Auth
         ↓                                          ↓
    ✓ User Created                         ✓ User Authenticated
         ↓                                          ↓
    Redirect to /chat                    Redirect to /chat
         ↓                                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CHAT PAGE (/chat) - PROTECTED                  │
│                                                                   │
│  ┌─────────────┐  ┌──────────────────────────────────────────┐ │
│  │   Sidebar   │  │          CHAT INTERFACE                  │ │
│  │             │  │                                          │ │
│  │  • Session  │  │  Header:                                 │ │
│  │  • Agent    │  │  ⚖️ Sahayak Legal Assistant              │ │
│  │    Info     │  │  Ready to help                           │ │
│  │  • Chat     │  │  [Lang ▼] [Panic] [Logout 🚪]          │ │
│  │    History  │  │                                          │ │
│  │             │  │  Messages:                               │ │
│  │  [New Chat] │  │  ┌─────────────────────────────────┐   │ │
│  │  [Clear]    │  │  │ How can I help you today?       │   │ │
│  │             │  │  └─────────────────────────────────┘   │ │
│  │             │  │                                          │ │
│  │             │  │  Input Bar:                              │ │
│  │             │  │  [Type message...] [Send] [Upload]      │ │
│  │             │  │                                          │ │
│  └─────────────┘  └──────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         ↓
    [Logout 🚪]
         ↓
    Firebase Sign Out
         ↓
    Redirect to /login
         ↓
    Return to Login Page
```

## 🔀 Router Architecture

```
App (BrowserRouter)
├── AuthProvider (Context)
│   └── Routes
│       ├── Route "/" → LandingPage
│       ├── Route "/login" → LoginPage
│       ├── Route "/signup" → SignupPage
│       ├── Route "/chat" → ProtectedRoute
│       │   └── ChatApp
│       │       ├── Sidebar
│       │       ├── ChatWindow
│       │       ├── InputBar
│       │       └── PanicButton
│       └── Route "*" → Navigate to "/"
```

## 🔐 Authentication State Flow

```
Initial State: Not Authenticated
        ↓
User visits app
        ↓
useAuth Hook checks Firebase
        ↓
   ┌─ Loading
   │  Shows: "Loading..."
   │  ↓
   ├─ User: null → Redirect to /login
   │  
   └─ User: {obj} → Allow access to /chat
        ↓
    User can now:
    • View chat
    • Send messages
    • Use all features
    • Click logout
        ↓
    Logout → Firebase signOut()
        ↓
    Session cleared
        ↓
    User: null
        ↓
    Redirect to /login
        ↓
    Back to initial state
```

## 🎨 Component Hierarchy

```
App.jsx
│
├── App Wrapper
│   ├── BrowserRouter
│   └── AuthProvider (Context Provider)
│
├── Routes Level
│   ├── Landing (Public)
│   │   └── Hero + Features + About + Footer
│   │
│   ├── SignUp (Public)
│   │   ├── Form Inputs
│   │   ├── Validation
│   │   └── Sidebar Helper
│   │
│   ├── Login (Public)
│   │   ├── Form Inputs
│   │   ├── Anonymous Option
│   │   └── Sidebar Helper
│   │
│   └── Chat (Protected)
│       └── ChatApp (requires auth)
│           ├── Sidebar
│           │   ├── Session Info
│           │   └── Chat History
│           │
│           └── Main Area
│               ├── Header
│               │   ├── Agent Info
│               │   └── Actions (Lang, Panic, Logout)
│               │
│               ├── ChatWindow
│               │   └── Messages
│               │
│               └── InputBar
│                   └── Send Message
```

## 🎯 State Management

```
useAuth Hook
├── user: Firebase User Object | null
├── loading: boolean
├── logout(): Promise<void>
└── Context Provider
    └── Available to all child components

useChat Hook (Existing)
├── messages: Array
├── sessionId: string
├── isLoading: boolean
├── error: string | null
├── agentInfo: object
├── send(): void
├── upload(): void
└── clearMessages(): void
```

## 📱 Responsive Breakpoints

```
Desktop (≥1024px)
├── 2-column layout (Auth sidebar visible)
├── Full width hero
└── Multi-column features grid

Tablet (768px - 1023px)
├── 1-column layout
├── Sidebar hidden on mobile
└── 2-column features grid

Mobile (<768px)
├── Single column
├── Optimized form inputs (16px to prevent zoom)
├── Simplified header
└── Full-width buttons
```

## 🎨 Color Usage Map

```
Primary Actions
└─ Background: linear-gradient(var(--primary-500) → var(--primary-600))
   Color: white
   Text: "Sign In", "Create Account"

Secondary Actions
└─ Background: transparent
   Border: var(--primary-500)
   Color: var(--primary-400)
   Text: "Continue Anonymously", "Sign Up"

Hover States
└─ Background: rgba(20, 184, 166, 0.1)
   Border: var(--primary-400)
   Color: var(--primary-300)
   Transform: translateY(-2px)
   Box-shadow: 0 8px 16px rgba(20, 184, 166, 0.3)

Error States
└─ Background: rgba(239, 68, 68, 0.1)
   Border: var(--danger-600)
   Color: var(--danger-500)
   Text: Error message

Sidebar/Accent
└─ Background: linear-gradient(135deg, var(--primary-900) → var(--primary-800))
   Color: var(--primary-200)
   Glow: radial-gradient circle (20% opacity)
```

## 📊 Feature Matrix

```
┌─────────────────────┬──────────┬────────┬─────────┐
│ Feature             │ Landing  │ Auth   │ Chat    │
├─────────────────────┼──────────┼────────┼─────────┤
│ Hero Section        │ ✅       │        │         │
│ Feature Cards       │ ✅       │        │         │
│ About Section       │ ✅       │        │         │
│ CTA Buttons         │ ✅       │        │         │
│ Footer              │ ✅       │        │         │
│                     │          │        │         │
│ Email/Password Form │          │ ✅     │         │
│ Anonymous Login     │          │ ✅     │         │
│ Form Validation     │          │ ✅     │         │
│ Error Messages      │          │ ✅     │         │
│ Sidebar Helper      │          │ ✅     │         │
│                     │          │        │         │
│ Message Display     │          │        │ ✅      │
│ Input Bar           │          │        │ ✅      │
│ Language Selector   │          │        │ ✅      │
│ Panic Button        │          │        │ ✅      │
│ Logout Button       │          │        │ ✅      │
│ Session Info        │          │        │ ✅      │
└─────────────────────┴──────────┴────────┴─────────┘
```

## 🔄 Request/Response Flow

```
User Signup
1. User enters email/password → SignupPage
2. Form validation → Frontend
3. createUserWithEmailAndPassword() → Firebase
4. Firebase creates user → Returns user object
5. App detects user → useAuth hook
6. Redirect → /chat → ProtectedRoute
7. ChatApp renders → User sees chat

User Login
1. User enters credentials → LoginPage
2. signInWithEmailAndPassword() → Firebase
3. Firebase authenticates → Returns user object
4. App detects user → useAuth hook
5. Redirect → /chat
6. ChatApp loads → Ready to chat

Anonymous Login
1. User clicks "Continue Anonymously" → LoginPage
2. signInAnonymously() → Firebase
3. Firebase creates anonymous session
4. App detects user → useAuth hook
5. Redirect → /chat
6. ChatApp loads → Full functionality

Logout
1. User clicks "Logout" → ChatApp header
2. handleLogout() → Calls logout()
3. signOut() → Firebase clears session
4. useAuth detects logout
5. Redirect → /login
6. Session cleared → Can login again
```

## 💾 Data Structures

```
Firebase User Object
{
  uid: string,                 // Unique user ID
  email: string | null,        // User email (null for anonymous)
  displayName: string | null,  // User display name
  isAnonymous: boolean,        // Is anonymous user?
  metadata: {...},             // Creation/last login times
  providerData: [...],         // Auth provider info
}

Auth Context
{
  user: User | null,           // Current user
  loading: boolean,            // Auth loading state
  logout: () => Promise,       // Logout function
}

Chat Message (Existing)
{
  id: string,
  sender: 'user' | 'bot',
  content: string,
  timestamp: number,
  sessionId: string,
}
```

---

This visual guide shows the complete architecture, user flow, and technical implementation of the authentication system.
