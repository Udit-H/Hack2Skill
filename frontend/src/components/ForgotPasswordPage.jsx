import { Link } from 'react-router-dom';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function ForgotPasswordPage() {
  const { language } = useLanguage();
  const t = (key) => getTranslation(key, language);

  return (
    <div className="auth-container">
      <div className="auth-box">
        <Link to="/login" className="back-button">
          ← Back to Login
        </Link>

        <div className="auth-logo">
          <span className="logo-icon">🔐</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        <div className="auth-form">
          <h2>No Password Needed</h2>
          <p className="auth-subtitle">
            Sahayak uses anonymous sessions — no account or password required.
            Just go to the login page and click "Continue Without Login."
          </p>

          <Link to="/login" className="btn btn-primary btn-block" style={{ textAlign: 'center', textDecoration: 'none' }}>
            Go to Login
          </Link>
        </div>

        <div className="auth-help">
          <p>
            Your privacy is our priority. No email or password is collected.
          </p>
        </div>
      </div>
    </div>
  );
}
