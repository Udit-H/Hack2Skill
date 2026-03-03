import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function LoginPage() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const { loginAnonymous } = useAuth();
  const navigate = useNavigate();

  const t = (key) => getTranslation(key, language);

  const handleAnonymousLogin = () => {
    setError('');
    setLoading(true);
    try {
      loginAnonymous();
      navigate('/chat');
    } catch (err) {
      setError('Failed to start session');
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
          <p className="auth-subtitle">Click below to start your session privately and anonymously.</p>

          {error && <div className="error-message">{error}</div>}

          <button
            onClick={handleAnonymousLogin}
            className="btn btn-primary btn-block"
            disabled={loading}
          >
            {loading ? 'Connecting...' : t('auth.continue_without_login')}
          </button>
        </div>

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
