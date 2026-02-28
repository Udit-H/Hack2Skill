import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signInWithEmailAndPassword, signInAnonymously } from 'firebase/auth';
import { auth } from '../utils/firebase';
import './AuthPages.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to login');
    } finally {
      setLoading(false);
    }
  };

  const handleAnonymousLogin = async () => {
    setError('');
    setLoading(true);

    try {
      await signInAnonymously(auth);
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to login anonymously');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        {/* Back Button */}
        <Link to="/" className="back-button">
          ← Back to Home
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">⚖️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="auth-form">
          <h2>Welcome Back</h2>
          <p className="auth-subtitle">Sign in to access your crisis support</p>

          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="auth-divider">
          <span>or</span>
        </div>

        {/* Anonymous Login */}
        <button
          onClick={handleAnonymousLogin}
          className="btn btn-secondary btn-block"
          disabled={loading}
        >
          {loading ? 'Connecting...' : 'Continue without Login'}
        </button>

        {/* Sign Up Link */}
        <p className="auth-switch">
          Don't have an account?{' '}
          <Link to="/signup" className="auth-link">
            Sign up here
          </Link>
        </p>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            In a crisis? Call <strong>emergency services</strong> or reach out to a
            local support hotline immediately.
          </p>
        </div>

        {/* Terms & Privacy */}
        <div className="auth-terms">
          <p>
            By continuing, you agree to our{' '}
            <a href="/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a>
            {' '}and{' '}
            <a href="/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
          </p>
        </div>
      </div>

      {/* Sidebar Info */}
      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Need Help Right Now?</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">🏠</span>
              <div>
                <strong>Emergency Shelter</strong>
                <p>Find safe places to stay immediately</p>
              </div>
            </li>
            <li>
              <span className="help-icon">⚖️</span>
              <div>
                <strong>Legal Guidance</strong>
                <p>Get help with property and eviction issues</p>
              </div>
            </li>
            <li>
              <span className="help-icon">💬</span>
              <div>
                <strong>24/7 Support</strong>
                <p>AI assistant available anytime</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
