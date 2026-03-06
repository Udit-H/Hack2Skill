import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signIn } from 'aws-amplify/auth';
import { useAuth } from '../hooks/useAuth.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const { loginAnonymous } = useAuth();
  const navigate = useNavigate();

  const t = (key) => getTranslation(key, language);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn({ username: email, password });
      navigate('/chat');
    } catch (err) {
      // Map Cognito errors to user-friendly messages
      const errorMessage = err.message || 'Failed to login';
      if (err.code === 'UserNotConfirmedException') {
        setError('Please verify your email before logging in.');
      } else if (err.code === 'NotAuthorizedException' || err.code === 'InvalidPasswordException') {
        setError('Invalid email or password.');
      } else if (err.code === 'UserNotFoundException') {
        setError('No account found with this email.');
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAnonymousLogin = async () => {
    setError('');
    setLoading(true);

    try {
      loginAnonymous();
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to login anonymously');
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
        <Link to="/" className="back-button">
          {t('auth.back_to_home')}
        </Link>

        <div className="auth-logo">
          <span className="logo-icon">⚖️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        <div className="auth-form">
          <h2>{t('auth.welcome_back')}</h2>
          <p className="auth-subtitle">Sign in to access your secure session</p>

          {error && <div className="error-message">{error}</div>}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label htmlFor="email">{t('auth.email')}</label>
              <input
                id="email"
                type="email"
                placeholder="your.email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">{t('auth.password')}</label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            <div className="form-footer">
              <Link to="/forgot-password" className="forgot-password-link">
                {t('auth.forgot_password')}
              </Link>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !email || !password}
            >
              {loading ? 'Signing in...' : t('auth.login')}
            </button>
          </form>

          <div className="divider">
            <span>OR</span>
          </div>

          <button
            onClick={handleAnonymousLogin}
            className="btn btn-secondary btn-block"
            disabled={loading}
          >
            {t('auth.continue_without_login')}
          </button>
        </div>

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

        <div className="auth-terms">
          <p>
            {t('auth.by_continuing')}{' '}
            <a href="/terms" target="_blank" rel="noopener noreferrer">{t('auth.terms_of_service')}</a>
            {' '}{t('auth.and')}{' '}
            <a href="/privacy" target="_blank" rel="noopener noreferrer">{t('auth.privacy_policy')}</a>
          </p>
        </div>
      </div>

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
