# Frontend Quick Start

## Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up Amazon Cognito**
   - Follow the [Cognito Setup Guide](./COGNITO_SETUP.md)
   - Copy your Cognito credentials to `.env.local`:
     ```bash
     cp .env.example .env.local
     # Then fill in VITE_COGNITO_* variables
     ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   - Default: `http://localhost:5173`

## Features Implemented

### ✅ Authentication Pages
- **Landing Page** (`/`) - Public homepage with features overview
- **Sign Up** (`/signup`) - Create account with Cognito
- **Confirm Signup** (`/confirm-signup`) - Verify email with code
- **Login** (`/login`) - Sign in with email/password
- **Forgot Password** (`/forgot-password`) - Initiate password reset
- **Confirm Reset Password** (`/confirm-reset-password`) - Complete password reset
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
3. **On signup**: 
   - Creates Cognito account
   - Sends verification email
   - User confirms with code
   - Auto sign-in or redirects to login
4. **On login**: 
   - Authenticates with Cognito
   - Redirects to chat
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
- Links to signup and password reset
- Sidebar with help information
- Error messages for different error types

### Sign Up Page
Features:
- Email field
- Password field with requirements
- Confirm password field
- Terms checkbox
- Auto-validation before submission
- Links to login

### Confirm Signup Page
Features:
- Email confirmation input
- 6-digit code entry
- Auto sign-in after confirmation
- Help text for code delivery

### Chat Page (Protected)
Shows:
- Sidebar with session info
- Chat messages area
- Input bar for messages
- Language selector
- Logout button in header

### Password Reset Flow
- Email-based code verification
- 2-step process: verify code, then set new password
- Auto-redirect to login after reset

## Environment Variables

Required for Cognito:
```
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_COGNITO_CLIENT_ID=your_client_id_here
VITE_COGNITO_REGION=us-east-1
```

Copy ``.env.example`` to ``.env.local`` and fill in your Cognito details.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Next Steps

1. **Complete Cognito Setup**
   - Follow [COGNITO_SETUP.md](./COGNITO_SETUP.md) for detailed instructions
   - Test signup, login, and password reset flows

2. **Connect to Backend**
   - Update `src/hooks/useChat.js` API endpoints
   - Point to your FastAPI backend

3. **Customize Content**
   - Update landing page features
   - Modify sidebar help text
   - Adjust colors in `src/index.css`

4. **Deployment**
   - Update callback URLs in Cognito App Client settings
   - Update environment variables for production
   - Configure your domain

## Troubleshooting

### Cognito Config Not Working
- Verify all VITE_COGNITO_* variables are filled in `.env.local`
- Check User Pool ID format: `region_randomstring`
- Ensure Client ID is correct (not Client Secret)
- Restart dev server after changing `.env.local`

### Routes Not Loading
- React Router is set up in `App.jsx`
- All routes should work from root path
- Check browser console for errors

### Auth Not Persisting
- Amplify handles session persistence automatically
- Check browser localStorage/sessionStorage isn't disabled
- Verify Cognito User Pool settings

### Email Codes Not Arriving
- Check spam folder
- Verify email address is correct
- Wait 1-2 minutes for delivery (especially first time)
- Check email quota (Cognito: 50/day without SES)

### "Callback URL mismatch"
- Add `http://localhost:5173/` to Cognito App Client settings
- Include protocol and trailing slash
- Add production domains before deploying

## Authentication Stack

Sahayak uses Amazon Cognito with AWS Amplify. Key details:

**Authentication Provider**
- `aws-amplify/auth` library

**Auth Context**
- Amplify Hub for state changes + `getCurrentUser()`

**Environment Variables**
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_CLIENT_ID`
- `VITE_COGNITO_REGION`

**Dependencies**
- `aws-amplify` package

## File Changes Made

✅ **Modified:**
- `package.json` - Includes `aws-amplify`
- `src/utils/cognito.js` - Cognito configuration
- `src/hooks/useAuth.jsx` - Amplify Hub + getCurrentUser
- `src/hooks/useAuth.js` - Amplify Hub + getCurrentUser
- `src/components/LoginPage.jsx` - Uses `signIn` from `aws-amplify/auth`
- `src/components/SignupPage.jsx` - Uses `signUp` + `confirmSignUp`
- `src/components/ForgotPasswordPage.jsx` - Uses `resetPassword`
- `src/App.jsx` - Includes confirmation routes
- `.env.example` - Cognito variables
- `QUICK_START.md` - Updated this file

✅ **Created:**
- `src/components/ConfirmSignupPage.jsx` - Email verification page
- `src/components/ConfirmResetPasswordPage.jsx` - Password reset completion
- `COGNITO_SETUP.md` - Detailed Cognito setup guide

## Support

For issues with:
- **Cognito**: Check [COGNITO_SETUP.md](./COGNITO_SETUP.md) or [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- **React Router**: Check [Router Documentation](https://reactrouter.com)
- **Styling**: All CSS is in component `.css` files
- **Amplify**: Check [AWS Amplify Documentation](https://docs.amplify.aws/react/)
