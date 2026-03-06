import { useState, useEffect, useContext, createContext } from 'react';
import { signOut, getCurrentUser } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check initial auth state
    const checkAuthState = async () => {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        // Not authenticated - set anonymous user for now
        setUser({ anonymous: true });
      } finally {
        setLoading(false);
      }
    };

    checkAuthState();

    // Subscribe to auth state changes via Amplify Hub
    const hubListener = Hub.listen('auth', ({ payload }) => {
      switch (payload.event) {
        case 'signedIn':
          getCurrentUser().then(user => setUser(user)).catch(() => setUser({ anonymous: true }));
          break;
        case 'signedOut':
          setUser({ anonymous: true });
          break;
        case 'tokenRefresh':
          // Token refreshed, user object remains valid
          break;
        default:
          break;
      }
    });

    return () => hubListener();
  }, []);

  const loginAnonymous = () => {
    // For anonymous access, just set a mock user
    setUser({ anonymous: true, id: 'anonymous-' + Date.now() });
  };

  const logout = async () => {
    try {
      await signOut();
      setUser({ anonymous: true });
    } catch (err) {
      console.error('Logout error:', err);
      // Even if signOut fails, treat as anonymous
      setUser({ anonymous: true });
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout, loginAnonymous }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
