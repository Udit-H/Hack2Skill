import { useState, useContext, createContext } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  // Simple anonymous auth — no Firebase
  const [user, setUser] = useState({ anonymous: true });
  const loading = false;

  const logout = () => {
    setUser(null);
    window.location.href = '/';
  };

  const loginAnonymous = () => {
    setUser({ anonymous: true });
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
