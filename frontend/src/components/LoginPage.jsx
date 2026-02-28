import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signInWithEmailAndPassword, signInAnonymously } from 'firebase/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import { auth } from '../utils/firebase';
import './AuthPages.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const t = (key) => getTranslation(key, language);

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
      <div className="language-selector">
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="en">English</option>
          <option value="hi">हिन्दी (Hindi)</option>
          <option value="ta">தமிழ் (Tamil)</option>
          <option value="bn">বাংলা (Bengali)</option>
        </select>
      </div>

      <div className="auth-box">
        {/* Back Button */}
        <Link to="/" className="back-button">
          {t('auth.back_to_home')}
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">⚖️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="auth-form">
          <h2>{t('auth.welcome_back')}</h2>
          <p className="auth-subtitle">{t('auth.sign_in_desc')}</p>

          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">{t('auth.email')}</label>
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
            <label htmlFor="password">{t('auth.password')}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
            <Link to="/forgot-password" className="forgot-password-link">
              {t('auth.forgot_password')}
            </Link>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? t('auth.sending_email') : t('auth.sign_in_btn')}
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
          {loading ? 'Connecting...' : t('auth.continue_without_login')}
        </button>

        {/* Sign Up Link */}
        <p className="auth-switch">
          {t('auth.dont_have_account')}{' '}
          <Link to="/signup" className="auth-link">
            {t('auth.sign_up_here')}
          </Link>
        </p>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            {t('auth.emergency_help')}
          </p>
        </div>

        {/* Terms & Privacy */}
        <div className="auth-terms">
          <p>
            {t('auth.by_continuing')}{' '}
            <a href="/terms" target="_blank" rel="noopener noreferrer">{t('auth.terms_of_service')}</a>
            {' '}{t('auth.and')}{' '}
            <a href="/privacy" target="_blank" rel="noopener noreferrer">{t('auth.privacy_policy')}</a>
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
