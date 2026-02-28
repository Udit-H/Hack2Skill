# Frontend Authentication Setup

This frontend uses Firebase Authentication for user management with React Router for navigation.

## Project Structure

```
src/
├── components/
│   ├── ChatApp.jsx           # Main chat interface (protected)
│   ├── LandingPage.jsx       # Public landing page
│   ├── LoginPage.jsx         # Firebase login
│   ├── SignupPage.jsx        # Firebase signup
│   ├── ProtectedRoute.jsx    # Route guard for authenticated pages
│   ├── AuthPages.css         # Auth page styling
│   └── LandingPage.css       # Landing page styling
├── hooks/
│   ├── useAuth.js            # Auth context hook
│   └── useChat.js            # Chat functionality hook
├── utils/
│   └── firebase.js           # Firebase configuration
├── App.jsx                   # Router setup
└── main.jsx                  # Entry point
```

## Routes

- **`/`** - Landing page (public)
- **`/login`** - Login page (public)
- **`/signup`** - Sign up page (public)
- **`/chat`** - Chat interface (protected - requires authentication)

## Firebase Configuration

The app requires a Firebase project. Update `src/utils/firebase.js` with your credentials:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### Getting Firebase Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to Project Settings > General
4. Scroll down to "Your apps" and copy the config
5. Paste into `src/utils/firebase.js`

## Authentication Features

### Sign Up
- Email/password registration
- Password validation (min 6 characters)
- Password confirmation
- Terms of Service agreement
- Automatic login after signup

### Login
- Email/password login
- Anonymous login option
- Error handling and feedback
- Redirect to chat on success

### Protection
- `ProtectedRoute` component prevents unauthorized access
- Automatic redirect to login for unauthenticated users
- Auth state persists across page reloads

### Logout
- Logout button in chat header
- Clears Firebase session
- Redirects to login page

## Design System

The app uses a trauma-informed design with:
- **Primary**: Teal palette (`#14b8a6` to `#0f766e`)
- **Accent**: Warm amber (`#f59e0b`)
- **Background**: Dark mode (`#0f1a1f`)
- **Text**: Light colors for accessibility

## Development

### Start Dev Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

### Important Notes

1. **Firebase Config**: Update `firebase.js` before running
2. **Auth Persistence**: Firebase automatically persists user sessions
3. **Anonymous Login**: Users can login without email
4. **Protected Routes**: Chat requires authentication
5. **Error Messages**: User-friendly error messages for all auth errors

## Component Details

### useAuth Hook
Provides authentication context:
- `user` - Current authenticated user (or null)
- `loading` - Auth state loading status
- `logout()` - Sign out function

### ChatApp Component
- Checks authentication status
- Renders chat interface if authenticated
- Includes logout button
- Redirects to login if not authenticated

### ProtectedRoute Component
- Wraps protected routes (e.g., `/chat`)
- Shows loading state while checking auth
- Redirects to `/login` if not authenticated

## Styling

All authentication pages use consistent styling:
- Responsive grid layout (single column on mobile)
- Animated form elements
- Accessible form validation
- Smooth transitions and hover effects
- Dark mode by default

## Security Considerations

1. **No sensitive data in client code** - Config contains public API key
2. **Firebase security rules** - Configure in Firebase Console
3. **Anonymous browsing** - Available for quick access
4. **Password requirements** - Min 6 characters enforced
5. **Session persistence** - Handled by Firebase SDK
