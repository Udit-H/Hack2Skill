import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../utils/firebase';
import './AuthPages.css';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const validateForm = () => {
    if (!email || !password || !confirmPassword) {
      setError('All fields are required');
      return false;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return false;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;

    setLoading(true);

    try {
      await createUserWithEmailAndPassword(auth, email, password);
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to create account');
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
          <span className="logo-icon">🏛️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Signup Form */}
        <form onSubmit={handleSignup} className="auth-form">
          <h2>Create Account</h2>
          <p className="auth-subtitle">Join Sahayak to get support today</p>

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
            <small>At least 6 characters</small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          <div className="terms-checkbox">
            <input type="checkbox" id="terms" required disabled={loading} />
            <label htmlFor="terms">
              I agree to the <a href="/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a> and{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
            </label>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        {/* Login Link */}
        <p className="auth-switch">
          Already have an account?{' '}
          <Link to="/login" className="auth-link">
            Sign in here
          </Link>
        </p>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            Your information is secure and will never be shared without your consent.
          </p>
        </div>
      </div>

      {/* Sidebar Info */}
      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Why Join Sahayak?</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">⚡</span>
              <div>
                <strong>Instant Access</strong>
                <p>Get help immediately upon signup</p>
              </div>
            </li>
            <li>
              <span className="help-icon">🔒</span>
              <div>
                <strong>Completely Private</strong>
                <p>Your crisis stays between you and us</p>
              </div>
            </li>
            <li>
              <span className="help-icon">🌍</span>
              <div>
                <strong>24/7 Available</strong>
                <p>Support whenever you need it most</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
