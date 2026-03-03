import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function SignupPage() {
  const { language } = useLanguage();
  const { loginAnonymous } = useAuth();
  const navigate = useNavigate();
  const t = (key) => getTranslation(key, language);

  const handleStart = () => {
    loginAnonymous();
    navigate('/chat');
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <Link to="/" className="back-button">
          {t('auth.back_to_home')}
        </Link>

        <div className="auth-logo">
          <span className="logo-icon">🏛️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        <div className="auth-form">
          <h2>Get Started</h2>
          <p className="auth-subtitle">No account needed — start your session anonymously.</p>

          <button onClick={handleStart} className="btn btn-primary btn-block">
            Start Private Session
          </button>
        </div>

        <p className="auth-switch">
          Already visited?{' '}
          <Link to="/login" className="auth-link">
            Continue here
          </Link>
        </p>

        <div className="auth-help">
          <p>Your information is secure and will never be shared without your consent.</p>
        </div>
      </div>

      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Why Join Sahayak?</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">⚡</span>
              <div>
                <strong>Instant Access</strong>
                <p>Get help immediately</p>
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
