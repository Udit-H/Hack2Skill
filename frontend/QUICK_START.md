# Frontend Quick Start

## Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up Firebase**
   - Copy your Firebase config to `src/utils/firebase.js`
   - Replace all placeholder values with your actual credentials

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   - Default: `http://localhost:5173`

## Features Implemented

### ✅ Authentication Pages
- **Landing Page** (`/`) - Public homepage with features overview
- **Sign Up** (`/signup`) - Create account with Firebase
- **Login** (`/login`) - Sign in with email/password or anonymously
- **Protected Chat** (`/chat`) - Requires authentication

### ✅ Design System
- Teal/Navy/Amber color scheme
- Dark mode by default
- Trauma-informed typography and spacing
- Responsive layout (mobile to desktop)
- Smooth transitions and hover effects

### ✅ Authentication Flow
1. User lands on landing page
2. User clicks "Sign Up" or "Login"
3. On signup: Creates Firebase account → Redirects to chat
4. On login: Authenticates with Firebase → Redirects to chat
5. Chat page checks auth status
6. Logout button clears session and redirects to login

## Pages Overview

### Landing Page
Shows:
- Hero section with call-to-action
- 4 feature cards (Shelter, Legal, 24/7, Privacy)
- About section with stats
- Footer with links

### Login Page
Features:
- Email/password form
- Anonymous login option
- Links to signup
- Sidebar with help information
- Error messages and validation

### Sign Up Page
Features:
- Email field
- Password field with min 6 chars
- Confirm password field
- Terms checkbox
- Links to login
- Sidebar with benefits

### Chat Page (Protected)
Shows:
- Sidebar with session info
- Chat messages area
- Input bar for messages
- Language selector
- **NEW:** Logout button in header

## Environment Variables

No `.env` file needed! Firebase credentials go directly in:
```
src/utils/firebase.js
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Next Steps

1. **Configure Firebase Project**
   - Enable Email/Password auth
   - Enable Anonymous auth
   - Add users for testing

2. **Connect to Backend**
   - Update `src/hooks/useChat.js` API endpoints
   - Point to your FastAPI backend

3. **Customize Content**
   - Update landing page features
   - Modify sidebar help text
   - Adjust colors in `src/index.css`

## Troubleshooting

### Firebase Config Not Working
- Verify all fields are filled in `src/utils/firebase.js`
- Check Firebase project ID matches
- Ensure authentication methods are enabled in Firebase Console

### Routes Not Loading
- React Router is set up in `App.jsx`
- All routes should work from root path
- Check browser console for errors

### Auth Not Persisting
- Firebase SDK handles persistence automatically
- Check browser localStorage isn't disabled
- Verify Firebase project security rules aren't blocking

## File Changes Made

✅ **Created:**
- `src/components/ChatApp.jsx` - Separated chat logic with auth
- `src/components/ProtectedRoute.jsx` - Route protection
- `src/components/LandingPage.jsx` - Landing page
- `src/components/LoginPage.jsx` - Login form
- `src/components/SignupPage.jsx` - Signup form
- `src/components/AuthPages.css` - Auth styling
- `src/components/LandingPage.css` - Landing styling
- `src/hooks/useAuth.js` - Auth context
- `src/utils/firebase.js` - Firebase config

✅ **Updated:**
- `src/App.jsx` - Router setup with protected routes
- `src/index.css` - Added logout button styles
- `package.json` - Added react-router-dom

## Support

For issues with:
- **Firebase**: Check [Firebase Documentation](https://firebase.google.com/docs)
- **React Router**: Check [Router Documentation](https://reactrouter.com)
- **Styling**: All CSS is in component `.css` files
