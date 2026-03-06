import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { resetPassword } from 'aws-amplify/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();
  const t = (key) => getTranslation(key, language);

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      // Initiate password reset flow - Cognito sends code to email
      await resetPassword({ username: email });
      setSuccess(t('auth.reset_email_sent'));
      // Store email for confirmation step
      sessionStorage.setItem('resetPasswordEmail', email);
      sessionStorage.setItem('awaitingResetCode', 'true');
      setEmail('');
      setTimeout(() => {
        navigate('/confirm-reset-password');
      }, 2000);
    } catch (err) {
      if (err.code === 'UserNotFoundException') {
        setError('No account found with this email.');
      } else {
        setError(err.message || 'Failed to send reset email');
      }
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
        <Link to="/login" className="back-button">
          {t('auth.back_to_home')}
        </Link>

        <div className="auth-logo">
          <span className="logo-icon">🔐</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        <div className="auth-form">
          <h2>{t('auth.reset_password')}</h2>
          <p className="auth-subtitle">{t('auth.reset_desc')}</p>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <form onSubmit={handleResetPassword}>
            <div className="form-group">
              <label htmlFor="email">{t('auth.email')}</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                required
                disabled={loading}
                autoComplete="email"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !email}
            >
              {loading ? t('auth.sending_email') : t('auth.send_reset_email_btn')}
            </button>
          </form>

          <div className="auth-help" style={{ marginTop: '1.5rem' }}>
            <p>
              <strong>Note:</strong> If you don't have an account, you can use anonymous mode.
            </p>
          </div>
        </div>

        <p className="auth-switch">
          {t('auth.dont_have_account')}{' '}
          <Link to="/signup" className="auth-link">
            {t('auth.sign_up_here')}
          </Link>
        </p>
      </div>
    </div>
  );
}
